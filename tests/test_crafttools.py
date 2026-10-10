import json
import stat

from typer.testing import CliRunner

from moneyhub import crafttools
from moneyhub.cli import app


def _fake(base, name, body):
    d = base / name / "current" / f"{name}-cli-1.0-macos-universal"
    d.mkdir(parents=True)
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


def test_tools_command_lists_every_tool(tmp_path, monkeypatch):
    monkeypatch.setenv("MONEYHUB_CRAFT_DIR", str(tmp_path))
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    _fake(tmp_path, "gridcraft", "echo ok\n")
    out = CliRunner().invoke(app, ["tools"]).output
    assert "gridcraft" in out and "v1.0" in out and "pdfcraft" in out and "not installed" in out
