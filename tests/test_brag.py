import json
import wave

import numpy as np
import pytest
from PIL import Image
from typer.testing import CliRunner

from moneyhub.brag import audio, plan as planmod, voice as voicemod
from moneyhub.brag.pipeline import make_brag
from moneyhub.brag.render import FORMATS, BragRenderer, build_timeline, srt
from moneyhub.brag.sources import Material
from moneyhub.brag.tones import TONES, resolve_tone
from moneyhub.design import choose_style
from moneyhub.render import graphics as g

FACTS = planmod.Facts(
    name="Cosy Week Planner", kind="product", one_liner="A calm weekly planner.", audience="busy parents",
    features=["52 weekly spreads", "Habit tracker", "Goal pages", "Instant PDF download"], pains=["Forgetting what matters"],
    price="$9", cta="Instant download", n_pages=3)


def _mat(tmp_path):
    pages = [Image.new("RGB", (800, 1000), c) for c in ("#fdf6ec", "#e8f0e6", "#f0e6e6")]
    return Material(FACTS, pages, choose_style(seed=4), "t", tmp_path / "brag")


def test_every_tone_resolves_and_builtin_plan_is_valid():
    for key, tone in TONES.items():
        t, _ = resolve_tone(key)
        assert t.key == key
        plan = planmod.builtin_plan(FACTS, tone, 20)
        assert not planmod.violations(plan), (key, planmod.violations(plan))
        assert 12 <= sum(s.seconds for s in plan.scenes) <= 32


def test_free_text_tone_falls_back_to_default():
    t, direction = resolve_tone("calm and cosy like a library")
    assert t.key in TONES and "cosy" in direction


def test_violations_flag_wordy_scenes():
    plan = planmod.builtin_plan(FACTS, TONES["polished"] if "polished" in TONES else next(iter(TONES.values())), 20)
    plan.scenes[0].headline = "word " * 20
    assert planmod.violations(plan)


def test_timeline_respects_reading_time_and_snaps():
    tone = next(iter(TONES.values()))
    plan = planmod.builtin_plan(FACTS, tone, 20)
    tl = build_timeline(plan, tone, tone.bpm, 20)
    assert 12 <= tl.total <= 32
    assert all(it.end > it.start for it in tl.items)


def test_music_and_sfx_are_clean():
    for mood in audio.MOODS:
        x = audio.compose(mood, 100, 6.0, 3)
        assert x.shape[0] == 2 and np.isfinite(x).all() and np.abs(x).max() <= 1.5
        assert np.abs(x).max() > 0.01
    assert audio.sfx("chime").size > 0


def test_wav_roundtrip(tmp_path):
    p = audio.write_wav(tmp_path / "a.wav", audio.compose(next(iter(audio.MOODS)), 100, 2.0, 1))
    with wave.open(str(p)) as w:
        assert w.getframerate() == audio.SR and w.getnchannels() == 2


def test_renderer_frames_all_formats(tmp_path):
    mat = _mat(tmp_path)
    tone = next(iter(TONES.values()))
    plan = planmod.builtin_plan(FACTS, tone, 20)
    tl = build_timeline(plan, tone, tone.bpm, 20)
    for fm, (w, h) in FORMATS.items():
        size = (w // 4, h // 4)
        r = BragRenderer(plan, mat.pages, g.Brush(mat.style), tone, size, tl, None, None)
        for t in (0.0, tl.total / 2, tl.total - 0.05):
            assert r.frame(t).size == size
        assert r.poster_time() >= 0


def test_srt_format():
    tone = next(iter(TONES.values()))
    plan = planmod.builtin_plan(FACTS, tone, 20)
    tl = build_timeline(plan, tone, tone.bpm, 20)
    out = srt([s.headline for s in plan.scenes], tl)
    assert out.startswith("1\n00:00:") and "-->" in out


def test_make_brag_preview_end_to_end(tmp_path):
    from moneyhub.render.motion import ffmpeg_exe
    if not ffmpeg_exe():
        pytest.skip("ffmpeg missing")
    res = make_brag(_mat(tmp_path), fmt="vertical", duration=14, preview=True, use_llm=False)
    assert res.video.exists() and res.video.stat().st_size > 10_000
    assert res.poster.exists() and "Pinterest title" in res.share.read_text()
    assert "Facts used" in res.plan_md.read_text()
    assert res.plan_source == "builtin"


def test_make_brag_with_fake_voice(tmp_path, monkeypatch):
    from moneyhub.render.motion import ffmpeg_exe
    if not ffmpeg_exe():
        pytest.skip("ffmpeg missing")

    class Fake(voicemod.Voice):
        name = "fake"
        def available(self): return True
        def synth(self, text, dst, ffmpeg):
            audio.write_wav(dst, np.zeros((2, int(1.2 * audio.SR))) + 0.01)
            return 1.2
    monkeypatch.setattr(voicemod, "pick", lambda preferred=None: Fake())
    res = make_brag(_mat(tmp_path), duration=14, voice=True, preview=True, use_llm=False, music="none")
    assert res.voice_engine == "fake" and res.video.exists()
    assert res.video.with_suffix(".srt").exists()


def test_cli_brag_help_and_voices():
    from moneyhub.cli import app
    r = CliRunner().invoke(app, ["brag", "--help"])
    assert r.exit_code == 0 and "--tone" in r.output
    assert CliRunner().invoke(app, ["voices", "status"]).exit_code == 0
    assert CliRunner().invoke(app, ["brag"]).exit_code != 0


def test_ui_brag_job_and_product_page(monkeypatch):
    from fastapi.testclient import TestClient
    import moneyhub.web.app as web
    from moneyhub.pipeline import Request, generate
    queued = []

    class FakeQueue:
        def put(self, item):
            queued.append(item)
    monkeypatch.setattr(web, "_queue", FakeQueue())
    c = TestClient(web.app)
    r = generate(Request("teacher", "card_deck", sizes=["letter"], providers=["builtin"], seed=3, with_images=False, with_video=False))
    page = c.get(f"/product/{r.product_id}")
    assert page.status_code == 200 and "Launch video" in page.text
    assert c.post(f"/product/{r.product_id}/brag", data={"fmt": "bogus"}).status_code == 400
    assert c.post(f"/product/{r.product_id}/brag", data={"fmt": "square"}, follow_redirects=False).status_code == 303
    assert web.JOBS[queued[0][0]]["label"] == f"Launch video for #{r.product_id}"


def test_growth_helpers(tmp_path):
    from datetime import date
    from moneyhub import growth
    from moneyhub.cli import app
    assert growth.bundle_price([9.0, 7.0, 5.0]) >= 10.0
    assert growth.net_after_fees(10, "kofi") == 10.0 and growth.net_after_fees(10, "etsy") < 9
    cal = growth.calendar(date(2026, 6, 15), 3)
    assert {r["month"] for r in cal} == {6, 7, 8}
    assert any("printable" in k for k in growth.keyword_ideas("budget"))
    r = CliRunner().invoke(app, ["calendar"])
    assert r.exit_code == 0 and r.output.strip()
    assert CliRunner().invoke(app, ["bundle", "--help"]).exit_code == 0


def test_bundle_and_sample_end_to_end():
    from moneyhub import growth
    from moneyhub.pipeline import Request, generate
    a = generate(Request("teacher", "card_deck", sizes=["letter"], providers=["builtin"], seed=3, with_images=False, with_video=False))
    b = generate(Request("nurse", "checklist_pack", sizes=["letter"], providers=["builtin"], seed=4, with_images=False, with_video=False))
    out = growth.make_bundle([a.product_id, b.product_id], "Helpers Bundle")
    assert (out / "listing.md").read_text().count("sold separately") == 2 and list((out / "product").glob("*.zip"))
    s = growth.make_sample(a.product_id, 1)
    assert s and s.exists()


def _fake_voice(monkeypatch):
    class Fake(voicemod.Voice):
        name = "fake"
        def available(self): return True
        def synth(self, text, dst, ffmpeg):
            audio.write_wav(dst, np.zeros((2, int(1.2 * audio.SR))) + 0.01)
            return 1.2
    monkeypatch.setattr(voicemod, "pick", lambda preferred=None: Fake())


def test_brag_voice_is_polished_only_when_soundcraft_is_switched_on(tmp_path, monkeypatch):
    import stat

    from moneyhub import crafttools
    from moneyhub.render.motion import ffmpeg_exe
    if not ffmpeg_exe():
        pytest.skip("ffmpeg missing")
    _fake_voice(monkeypatch)
    tools = tmp_path / "tools"
    exe = tools / "soundcraft" / "current" / "soundcraft-cli-1.0-macos-universal" / "soundcraft-cli"
    exe.parent.mkdir(parents=True)
    marker = tmp_path / "soundcraft-was-started"
    exe.write_text(f"#!/bin/bash\ntouch {marker}\nexit 2\n")
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("MONEYHUB_CRAFT_DIR", str(tools))
    monkeypatch.setattr(crafttools, "_cfg", lambda key, default=None: {"enabled": False, "tools": {}}.get(key, default))
    res = make_brag(_mat(tmp_path / "a"), duration=14, voice=True, preview=True, use_llm=False, music="none")
    assert res.video.exists() and not marker.exists()     # switched off: the tool is never started

    seen = []
    monkeypatch.setattr("moneyhub.brag.pipeline.polish_wav", lambda f: seen.append(f.name) or True)
    msgs = []
    res = make_brag(_mat(tmp_path / "b"), duration=14, voice=True, preview=True, use_llm=False, music="none", progress=msgs.append)
    assert res.video.exists() and seen and all(n.startswith("vo-") for n in seen)
    assert any("levelled with soundcraft" in m for m in msgs)

    monkeypatch.setattr("moneyhub.brag.pipeline.polish_wav", lambda f: False)   # a failing tool changes nothing
    res = make_brag(_mat(tmp_path / "c"), duration=14, voice=True, preview=True, use_llm=False, music="none")
    assert res.video.exists()
