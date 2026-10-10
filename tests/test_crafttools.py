import json
import stat

from typer.testing import CliRunner

from moneyhub import crafttools
from moneyhub.cli import app
from moneyhub.cli import app as app_cli


def _fake(base, name, body):
    d = base / name / "current" / f"{name}-cli-1.0-macos-universal"
    d.mkdir(parents=True, exist_ok=True)
    exe = d / f"{name}-cli"
    exe.write_text("#!/bin/bash\n" + body)
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    (base / name / "VERSION").write_text("v1.0\n")
    return exe


def test_missing_tool_and_failures_never_raise(tmp_path, monkeypatch):
    monkeypatch.setenv("MONEYHUB_CRAFT_DIR", str(tmp_path))
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    r = crafttools.run("pdfcraft", ["info", "x.pdf"])
    assert not r.ok and "not installed" in r.err
    _fake(tmp_path, "pdfcraft", "echo boom >&2\nexit 3\n")
    r = crafttools.run("pdfcraft", ["info", "x.pdf"])
    assert not r.ok and r.code == 3 and "boom" in r.err
    _fake(tmp_path, "vectorcraft", "sleep 5\n")
    assert "timed out" in crafttools.run("vectorcraft", ["info", "x"], timeout=0.3).err


def test_verify_product_uses_each_tool_on_the_right_files(tmp_path, monkeypatch):
    tools = tmp_path / "tools"
    monkeypatch.setenv("MONEYHUB_CRAFT_DIR", str(tools))
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    _fake(tools, "pdfcraft", 'if [ "$1" = render ]; then head -c 500 /dev/zero > "${@: -1}"; fi\necho \'{"pages": 3}\'\n')
    _fake(tools, "gridcraft", 'echo \'{"sheets": []}\'\n')
    _fake(tools, "vectorcraft", "echo bad file >&2\nexit 1\n")
    prod = tmp_path / "p"
    (prod / "product").mkdir(parents=True)
    (prod / "editable").mkdir()
    (prod / "product" / "a.pdf").write_bytes(b"%PDF")
    (prod / "product" / "t.xlsx").write_bytes(b"x")
    (prod / "editable" / "a.svg").write_text("<svg/>")
    res = crafttools.verify_product(prod)
    by = {(f["tool"], f["check"]): f["ok"] for f in res}
    assert by[("pdfcraft", "opens and summarises")] and by[("pdfcraft", "page 1 renders")]
    assert by[("gridcraft", "opens and lists sheets")] and not by[("vectorcraft", "opens as a vector document")]
    report = json.loads(crafttools.write_report(prod, res).read_text())
    assert len(report["findings"]) == 4 and any(t["tool"] == "pdfcraft" and t["path"] for t in report["tools"])


def test_images_and_documents_go_to_photocraft_and_wordcraft_and_passthrough_runs_any_tool(tmp_path, monkeypatch):
    tools = tmp_path / "tools"
    monkeypatch.setenv("MONEYHUB_CRAFT_DIR", str(tools))
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    _fake(tools, "photocraft", 'echo "photo $@"\n')
    _fake(tools, "wordcraft", 'echo "word $@"\n')
    prod = tmp_path / "p"
    (prod / "product").mkdir(parents=True)
    (prod / "images" / "etsy").mkdir(parents=True)
    (prod / "product" / "g.docx").write_bytes(b"x")
    (prod / "images" / "etsy" / "01-hero.jpg").write_bytes(b"x")
    res = {(f["tool"], f["file"]): f for f in crafttools.verify_product(prod)}
    assert res[("photocraft", "01-hero.jpg")]["ok"] and "--compact" in res[("photocraft", "01-hero.jpg")]["detail"]
    assert res[("wordcraft", "g.docx")]["ok"]
    r = crafttools.passthrough("wordcraft", ["--version"])
    assert r.ok and "word --version" in r.out
    assert not crafttools.passthrough("nonsense", []).ok
    out = CliRunner().invoke(app, ["craft", "wordcraft", "info", "x.docx"])
    assert out.exit_code == 0 and "word info x.docx" in out.output


def test_dxf_in_zips_audio_and_decks_are_checked(tmp_path, monkeypatch):
    import zipfile
    tools = tmp_path / "tools"
    monkeypatch.setenv("MONEYHUB_CRAFT_DIR", str(tools))
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    _fake(tools, "cadcraft", 'echo "cad $@"\n')
    _fake(tools, "soundcraft", 'echo "sound $@"\n')
    _fake(tools, "deckcraft", 'echo "deck $@"\n')
    prod = tmp_path / "p"
    (prod / "product").mkdir(parents=True)
    with zipfile.ZipFile(prod / "product" / "cut-DXF.zip", "w") as z:
        z.writestr("01-star.dxf", "0\nEOF\n")
        z.writestr("readme.txt", "x")
    (prod / "product" / "bad.zip").write_bytes(b"not a zip")
    (prod / "product" / "s.pptx").write_bytes(b"x")
    (prod / "music.wav").write_bytes(b"x")
    res = crafttools.verify_product(prod)
    names = {(f["tool"], f["file"]): f["ok"] for f in res}
    assert names[("cadcraft", "cut-DXF.zip:01-star.dxf")] and names[("deckcraft", "s.pptx")] and names[("soundcraft", "music.wav")]
    assert names[("cadcraft", "bad.zip")] is False


def _settings(monkeypatch, **craft):
    base = {"enabled": False, "verify_after_make": False, "timeout": 20, "tools": {}}
    base.update(craft)
    monkeypatch.setattr(crafttools, "_cfg", lambda key, default=None: base.get(key, default))


def _generate():
    from moneyhub.pipeline import Request, generate
    return generate(Request("x", "card_deck", providers=["builtin"], seed=3, sizes=["letter"], with_images=False, with_video=False,
                            options={"no_research": True}))


def test_everything_is_off_by_default_and_nothing_is_started(tmp_path, monkeypatch):
    tools = tmp_path / "tools"
    marker = tmp_path / "ran"
    monkeypatch.setenv("MONEYHUB_CRAFT_DIR", str(tools))
    _fake(tools, "pdfcraft", f"touch {marker}\necho '{{}}'\n")
    _settings(monkeypatch)   # the shipped defaults: all off
    assert crafttools.second_opinion(tmp_path) is None and not crafttools.is_enabled("pdfcraft")
    res = _generate()
    assert not any("Second opinion" in c.name for c in res.checks) and not marker.exists()
    _settings(monkeypatch, enabled=True, verify_after_make=True)   # master on, but no tool switched on
    assert crafttools.second_opinion(tmp_path) is None


def test_switched_on_tools_add_a_warn_only_check_and_others_never_run(tmp_path, monkeypatch):
    tools = tmp_path / "tools"
    other = tmp_path / "other-ran"
    monkeypatch.setenv("MONEYHUB_CRAFT_DIR", str(tools))
    _fake(tools, "pdfcraft", 'if [ "$1" = render ]; then head -c 500 /dev/zero > "${@: -1}"; fi\necho \'{"pages": 2}\'\n')
    _fake(tools, "photocraft", f"touch {other}\necho '{{}}'\n")
    _settings(monkeypatch, enabled=True, verify_after_make=True, tools={"pdfcraft": True, "photocraft": False})
    res = _generate()
    op = [c for c in res.checks if c.name == "Second opinion (craft tools)"]
    assert op and op[0].status == "pass" and "pdfcraft" in op[0].detail and not other.exists()
    assert (res.folder / "craft-verify.json").exists()
    # a tool that cannot open the file only warns; it never fails the product
    _fake(tools, "pdfcraft", "echo broken >&2\nexit 1\n")
    res2 = _generate()
    op2 = [c for c in res2.checks if c.name == "Second opinion (craft tools)"]
    assert op2 and op2[0].status == "warn" and res2.qa_status != "fail"


def test_a_crashing_or_missing_tool_never_breaks_generation(tmp_path, monkeypatch):
    monkeypatch.setenv("MONEYHUB_CRAFT_DIR", str(tmp_path / "none"))
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    _settings(monkeypatch, enabled=True, verify_after_make=True, tools={"pdfcraft": True, "gridcraft": True})
    res = _generate()   # tools enabled but not installed
    assert not any("Second opinion" in c.name for c in res.checks) and res.qa_status != "fail"

    def boom(*a, **k):
        raise RuntimeError("tool exploded")
    monkeypatch.setattr(crafttools, "verify_product", boom)
    assert crafttools.second_opinion(tmp_path) is None


def test_settings_roundtrip_cli_and_web(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from moneyhub import config
    from moneyhub.web.app import app
    monkeypatch.setenv("MONEYHUB_HOME", str(tmp_path))
    config.reload_config()
    try:
        assert crafttools.settings_view()["enabled"] is False
        crafttools.save_settings(True, True, {"pdfcraft": True})
        v = crafttools.settings_view()
        assert v["enabled"] and v["verify_after_make"] and {t["tool"]: t["enabled"] for t in v["tools"]}["pdfcraft"]
        assert (tmp_path / "moneyhub.local.yaml").exists()
        try:
            crafttools.save_settings(None, None, {"nonsense": True})
            raise AssertionError("expected ValueError")
        except ValueError:
            pass
        r = CliRunner().invoke(app_cli, ["tools", "--disable", "all", "--no-master"])
        assert r.exit_code == 0 and "off" in r.output
        assert crafttools.settings_view()["enabled"] is False
        assert CliRunner().invoke(app_cli, ["tools", "--enable", "bogus"]).exit_code != 0
        c = TestClient(app, base_url="http://127.0.0.1:8000")
        j = c.post("/api/settings/craft", data={"enabled": "1", "tools": ["gridcraft"]}, headers={"origin": "http://127.0.0.1:8000"}).json()
        assert j["enabled"] and {t["tool"]: t["enabled"] for t in j["tools"]}["gridcraft"]
    finally:
        monkeypatch.delenv("MONEYHUB_HOME")
        config.reload_config()


def test_settings_page_shows_the_craft_panel_switched_off_by_default():
    from fastapi.testclient import TestClient
    from moneyhub.web.app import app
    page = TestClient(app).get("/settings")
    assert page.status_code == 200 and "Second-opinion tools" in page.text and "Off by default" in page.text


def test_tools_command_lists_every_tool(tmp_path, monkeypatch):
    monkeypatch.setenv("MONEYHUB_CRAFT_DIR", str(tmp_path))
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    _fake(tmp_path, "gridcraft", "echo ok\n")
    out = CliRunner().invoke(app, ["tools"]).output
    assert "gridcraft" in out and "v1.0" in out and "pdfcraft" in out and "not installed" in out
