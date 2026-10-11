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
    names = {(f["tool"], f["file"]): f["ok"] for f in res if f["check"] != "size and units match the design"}
    assert names[("cadcraft", "cut-DXF.zip:01-star.dxf")] and names[("deckcraft", "s.pptx")] and names[("soundcraft", "music.wav")]
    assert names[("cadcraft", "bad.zip")] is False


def _cut_zips(prod, size_in=6.0, dxf_units=True):
    import zipfile
    from moneyhub import cutfiles
    d = cutfiles.heart()
    (prod / "product").mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(prod / "product" / "cut-SVG.zip", "w") as z:
        z.writestr("01-heart.svg", cutfiles.to_svg(d, size_in))
    dxf = cutfiles.to_dxf(d, size_in)
    with zipfile.ZipFile(prod / "product" / "cut-DXF.zip", "w") as z:
        z.writestr("01-heart.dxf", dxf if dxf_units else dxf.replace("$INSUNITS\n70\n1", "$INSUNITS\n70\n4"))
    return d


def _extents_json(d, scale):
    k = 6.0 / 1000.0 * scale
    xs = [x for r in d.rings for x, _ in r]
    ys = [1000 - y for r in d.rings for _, y in r]
    return json.dumps({"extents": [[min(xs) * k, min(ys) * k], [max(xs) * k, max(ys) * k]]})


def test_cad_size_and_unit_check(tmp_path, monkeypatch):
    tools = tmp_path / "tools"
    monkeypatch.setenv("MONEYHUB_CRAFT_DIR", str(tools))
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    _fake(tools, "cadcraft", 'cat "$CAD_JSON"\n')
    prod = tmp_path / "p"
    d = _cut_zips(prod)

    def size_row(scale, **kw):
        (tmp_path / "e.json").write_text(_extents_json(d, scale))
        monkeypatch.setenv("CAD_JSON", str(tmp_path / "e.json"))
        return [f for f in crafttools.verify_product(prod, only=["cadcraft"]) if f["check"] == "size and units match the design"][0]

    good = size_row(1.0)
    assert good["ok"] and "matches the SVG" in good["detail"]
    mm = size_row(25.4)                                     # a program that read inches as millimetres
    assert not mm["ok"] and "mat" in mm["detail"]
    small = size_row(0.5)
    assert not small["ok"] and "SVG of the same design" in small["detail"]
    prod2 = tmp_path / "p2"
    _cut_zips(prod2, dxf_units=False)
    (tmp_path / "e.json").write_text(_extents_json(d, 1.0))
    row = [f for f in crafttools.verify_product(prod2, only=["cadcraft"]) if f["check"] == "size and units match the design"][0]
    assert not row["ok"] and "inches" in row["detail"]
    assert crafttools.dxf_size_check("not json", "", None)[0] is False


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


def _write_wav(path, amp, seconds=0.5, rate=24000):
    import wave

    import numpy as np
    t = np.arange(int(seconds * rate)) / rate
    x = (np.sin(2 * np.pi * 220 * t) * amp * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(x.tobytes())


def _peak(path):
    import wave

    import numpy as np
    with wave.open(str(path)) as w:
        return float(np.abs(np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")).max()) / 32768


def test_polish_wav_levels_narration_only_when_switched_on_and_never_harms_it(tmp_path, monkeypatch):
    tools = tmp_path / "tools"
    monkeypatch.setenv("MONEYHUB_CRAFT_DIR", str(tools))
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    wav = tmp_path / "mix.wav"
    _write_wav(wav, 0.2)
    # a stand-in "normalize": writes a full-scale copy of the audio, like a peak normalise would
    loud = tmp_path / "loud.wav"
    _write_wav(loud, 1.0)
    _fake(tools, "soundcraft", f'cp {loud} "$3"\n')
    _settings(monkeypatch)   # off: nothing happens
    assert crafttools.polish_wav(wav, 24000) is False and abs(_peak(wav) - 0.2) < 0.01
    _settings(monkeypatch, enabled=True, tools={"soundcraft": True})
    assert crafttools.polish_wav(wav, 24000) is True
    assert 0.85 < _peak(wav) <= 0.91   # louder than before, with headroom kept
    # a tool that fails, or returns silence, leaves the file as it was
    wav2 = tmp_path / "b.wav"
    _write_wav(wav2, 0.2)
    _fake(tools, "soundcraft", "exit 2\n")
    assert crafttools.polish_wav(wav2, 24000) is False and abs(_peak(wav2) - 0.2) < 0.01
    silent = tmp_path / "silent.wav"
    _write_wav(silent, 0.0)
    _fake(tools, "soundcraft", f'cp {silent} "$3"\n')
    assert crafttools.polish_wav(wav2, 24000) is False and abs(_peak(wav2) - 0.2) < 0.01


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


def _fake_filmcraft(base, mode="ok"):
    """A stand-in filmcraft-cli: answers `run` with one ok line per script line and `export` with a real video of the planned length."""
    import sys
    d = base / "filmcraft" / "current" / "filmcraft-cli-1.0-macos-universal"
    d.mkdir(parents=True, exist_ok=True)
    exe = d / "filmcraft-cli"
    exe.write_text(f'''#!{sys.executable}
import json, os, subprocess, sys
a = sys.argv[1:]
if "run" in a:
    lines = [json.loads(x) for x in open(a[a.index("run") + 1]) if x.strip()]
    if os.environ.get("FAKE_MODE") == "badrun":
        print(json.dumps({{"id": "x", "line": 1, "ok": False, "error": "boom"}})); sys.exit(1)
    n = sum(1 for x in lines if x["id"] == "timeline.place")
    for k, x in enumerate(lines, 1):
        res = {{"items": list(range(1, n + 1)), "errors": []}} if x["id"] == "file.import" else {{"clips": [100 + k]}} if x["id"] == "timeline.place" else None
        print(json.dumps({{"id": x["id"], "line": k, "ok": True, "result": res}}))
    sys.exit(0)
if "export" in a:
    out = a[a.index("export") + 1]
    secs = os.environ["FAKE_SECONDS"] if os.environ.get("FAKE_MODE") != "short" else "1"
    subprocess.run([os.environ["FFMPEG"], "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=red:s=64x64:r=10", "-t", secs, "-pix_fmt", "yuv420p", out], check=True)
    sys.exit(0)
sys.exit(2)
''')
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    (base / "filmcraft" / "VERSION").write_text("v1.0\n")


def test_filmcraft_video_engine_is_off_by_default_and_falls_back_when_it_fails(tmp_path, monkeypatch):
    import pytest
    from PIL import Image

    from moneyhub.design import choose_style
    from moneyhub.render import graphics as g
    from moneyhub.render import motion
    ff = motion.ffmpeg_exe()
    if not ff:
        pytest.skip("ffmpeg missing")
    tools = tmp_path / "tools"
    monkeypatch.setenv("MONEYHUB_CRAFT_DIR", str(tools))
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    monkeypatch.setenv("FFMPEG", ff)
    _fake_filmcraft(tools)
    plan = motion.builtin_plan("A Planner", "sub", ["one", "two", "three"], "Plan it")
    monkeypatch.setenv("FAKE_SECONDS", f"{sum(s.seconds for s in plan.scenes):.2f}")
    brush = g.Brush(choose_style(seed=2))
    pages = [Image.new("RGB", (400, 500), "#eee")]
    size = (270, 480)
    engine = motion.ENGINES["filmcraft"]

    _settings(monkeypatch)   # everything off: not available, never started
    assert not engine.available()
    assert motion.render_video(plan, pages, brush, tmp_path / "a.mp4", size, "t", 10, engines=["filmcraft"]) is None

    _settings(monkeypatch, enabled=True, tools={"filmcraft": True})
    assert engine.available()
    out = motion.render_video(plan, pages, brush, tmp_path / "b.mp4", size, "t", 10, engines=["filmcraft"])
    assert out and out.exists() and abs(motion.video_duration(out) - float(__import__("os").environ["FAKE_SECONDS"])) < 0.5

    for mode in ("badrun", "short"):     # a failing tool or a wrong-length video is dropped, and the next engine in the chain takes over
        monkeypatch.setenv("FAKE_MODE", mode)
        assert motion.render_video(plan, pages, brush, tmp_path / f"{mode}.mp4", size, "t", 10, engines=["filmcraft"]) is None
        assert not (tmp_path / f"{mode}.filmcraft.mp4").exists()
        out = motion.render_video(plan, pages, brush, tmp_path / f"{mode}-chain.mp4", size, "t", 10, engines=["filmcraft", "pillow"])
        assert out and out.exists()


def test_filmcraft_has_a_settings_switch():
    assert "filmcraft" in crafttools.CHECKERS and "filmcraft" in {t["tool"] for t in crafttools.settings_view()["tools"]}
