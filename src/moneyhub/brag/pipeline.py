"""make_brag: source -> plan -> voice -> timeline -> music + SFX -> video + poster + share copy."""
from __future__ import annotations

import json
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image

from ..llm import get_router
from ..render import graphics as g
from ..render.motion import ffmpeg_exe
from ..crafttools import polish_wav
from . import audio, voice as voicemod
from .plan import BragPlan, make_plan
from .render import FORMATS, BragRenderer, build_timeline, encode, srt
from .sources import Material
from .tones import resolve_tone


@dataclass
class BragResult:
    folder: Path
    video: Path
    poster: Path
    share: Path
    plan_md: Path
    plan_source: str
    seconds: float
    voice_engine: str | None
    music: str
    extra_videos: list[Path]


def _read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
        if w.getnchannels() == 2:
            return x.reshape(-1, 2).T
        return np.stack([x, x])


def _decode_music_file(src: Path, dst: Path, ffmpeg: str, seconds: float) -> np.ndarray:
    import subprocess

    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(src), "-t", f"{seconds + 1:.2f}", "-ar", str(audio.SR), "-ac", "2", str(dst)], check=True)
    return _read_wav(dst)


def plan_markdown(mat: Material, plan: BragPlan, tone_key: str, tl, source: str, fmt: str, music: str, voice_engine: str | None) -> str:
    rows = "\n".join(
        f"| {i + 1} | {it.start:.1f}-{it.end:.1f}s | {sc.kind} | {sc.visual} | {sc.transition} | {sc.headline}"
        + (f" / {sc.subline}" if sc.subline else "") + (f" [{'; '.join(sc.bullets)}]" if sc.bullets else "") + " |"
        for i, (sc, it) in enumerate(zip(plan.scenes, tl.items)))
    p = mat.style.palette
    return (
        f"# Brag plan - {mat.facts.name}\n\n- **Angle:** {plan.angle}\n- **Hook:** {plan.hook}\n- **Punchline:** {plan.punchline}\n"
        f"- **Tone:** {tone_key} · **Format:** {fmt} · **Length:** {tl.total:.1f}s · **Plan by:** {source}\n"
        f"- **Identity:** palette `{p.key}` (accent {p.accent}, ink {p.ink}), fonts {mat.style.fonts.heading} / {mat.style.fonts.body}\n"
        f"- **Sound:** {music}" + (f", voice-over by {voice_engine}" if voice_engine else ", no voice-over") + "\n\n"
        f"## Storyboard\n\n| # | Time | Kind | Visual | Transition | On screen |\n|---|---|---|---|---|---|\n{rows}\n\n"
        f"## Facts used (nothing else is claimed)\n\n```json\n{mat.facts.model_dump_json(indent=2)}\n```\n")


def share_text(plan: BragPlan, mat: Material) -> str:
    s = plan.share
    sections = [("Primary (post as-is)", s.primary), ("Pinterest title", s.pinterest_title), ("Pinterest description", s.pinterest_description),
                ("Instagram / Reels", s.instagram), ("TikTok", s.tiktok), ("X", s.x), ("Reddit (read the subreddit's self-promotion rules first)", s.reddit),
                ("Email subject", s.email_subject), ("Email preview", s.email_preview)]
    body = "\n\n".join(f"## {h}\n{t}" for h, t in sections)
    return (f"{body}\n\n---\nPosting notes: use the vertical video for Pinterest video pins, Reels, TikTok and Shorts; keep captions on (many viewers watch muted); "
            "5 hashtags or fewer; post natively rather than sharing links; disclose AI-assisted creation where a platform asks.\n")


def make_brag(mat: Material, tone: str | None = None, fmt: str = "vertical", duration: float = 20.0, voice: bool | str = False,
              music: str = "generated", music_file: Path | None = None, captions: bool = False, providers: list[str] | None = None,
              fps: int = 30, progress: Callable[[str], None] | None = None, seed: int = 11, use_llm: bool = True, preview: bool = False) -> BragResult:
    say = progress or (lambda m: None)
    ffmpeg = ffmpeg_exe()
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required (brew install ffmpeg, or pip install imageio-ffmpeg)")
    duration = min(30.0, max(12.0, float(duration)))
    tone_obj, direction = resolve_tone(tone)
    out = mat.out_dir
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)

    say("Planning the story")
    plan, plan_source = make_plan(get_router() if use_llm else None, mat.facts, tone_obj, direction, duration, providers)
    (work / "plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")

    voice_engine = None
    lens = [0.0] * len(plan.scenes)
    vo_files: list[Path | None] = [None] * len(plan.scenes)
    vo_lines = [""] * len(plan.scenes)
    if voice:
        v = voicemod.pick(voice if isinstance(voice, str) else None)
        if v is None:
            say("No voice engine available (install kokoro: moneyhub voices install) - continuing without voice-over")
        else:
            voice_engine = v.name
            say(f"Recording voice-over ({v.name})")
            for i, sc in enumerate(plan.scenes):
                line = (sc.vo or sc.headline).strip()
                if line:
                    f = work / f"vo-{i + 1:02d}.wav"
                    lens[i] = v.synth(line, f, ffmpeg)
                    vo_files[i], vo_lines[i] = f, line
            if polish_wav is not None:   # optional soundcraft levelling of each spoken line; off unless switched on in Settings
                done = sum(1 for f in vo_files if f is not None and polish_wav(f))
                if done:
                    say(f"Voice-over levelled with soundcraft ({done} line{'s' if done != 1 else ''})")

    fps = 15 if preview else fps
    fmts = list(FORMATS) if fmt == "all" else [fmt]
    extra: list[Path] = []
    first: BragResult | None = None
    for fm in fmts:
        size = FORMATS[fm] if not preview else (FORMATS[fm][0] // 2, FORMATS[fm][1] // 2)
        say(f"Building the timeline ({fm})")
        tl = build_timeline(plan, tone_obj, tone_obj.bpm, duration, lens)
        wall = None
        if mat.is_wall_art and len(mat.pages) >= 1:
            wall = g.gallery_wall(mat.pages, "", "", g.Brush(mat.style), size).convert("RGBA")
        scenes = [s.model_copy(update={"visual": "mockup"}) if (wall is not None and s.visual in ("page", "pages") and s.kind == "show") else s for s in plan.scenes]
        plan_f = plan.model_copy(update={"scenes": scenes})
        caps = vo_lines if (voice_engine and (captions or True)) else ([s.headline for s in plan.scenes] if captions else None)
        brush = g.Brush(mat.style)
        r = BragRenderer(plan_f, mat.pages or [Image.new("RGB", (800, 1000), "white")], brush, tone_obj, size, tl, wall, caps)

        say("Mixing the soundtrack")
        total = tl.total
        music_label = "none"
        mix = np.zeros((2, int((total + 1.0) * audio.SR)))
        if music == "generated":
            m = audio.compose(tone_obj.mood, tone_obj.bpm, total, seed)
            mix[:, : m.shape[1]] += m[:, : mix.shape[1]]
            music_label = f"generated ({tone_obj.mood}, {tone_obj.bpm} bpm)"
        elif music == "file" and music_file:
            m = _decode_music_file(Path(music_file), work / "music-src.wav", ffmpeg, total)
            n = min(mix.shape[1], m.shape[1])
            mix[:, :n] += m[:, :n] * 0.6
            music_label = f"file: {Path(music_file).name}"
        spans = []
        for i, f in enumerate(vo_files):
            if f is not None:
                x = _read_wav(f)
                t0 = tl.items[i].start + tl.items[i].td + 0.15
                spans.append((t0, t0 + x.shape[1] / audio.SR))
        mix_music = audio.duck_under(mix, spans) if spans else mix
        sfx = audio.render_sfx_track([(e.t, e.kind) for e in r.events], total)
        n = min(mix_music.shape[1], sfx.shape[1])
        mix_music[:, :n] += sfx[:, :n] * (0.8 if voice_engine else 1.0)
        for i, f in enumerate(vo_files):
            if f is not None:
                x = _read_wav(f)
                i0 = int((tl.items[i].start + tl.items[i].td + 0.15) * audio.SR)
                j0 = min(mix_music.shape[1], i0 + x.shape[1])
                mix_music[:, i0:j0] += x[:, : j0 - i0] * 1.25
        raw = audio.write_wav(work / f"mix-{fm}.wav", mix_music)
        final_audio = audio.master(raw, work / f"audio-{fm}.wav", ffmpeg, total) if (music != "none" or voice_engine or r.events) else None

        say("Choosing the poster frame")
        poster_im = r.frame(r.poster_time()).convert("RGB")
        name = "brag" if len(fmts) == 1 else f"brag-{fm}"
        poster_path = out / f"{name}.jpg"
        poster_im.save(poster_path, quality=93)
        say(f"Rendering video ({fm})")
        video = encode(r, out / f"{name}.mp4", final_audio, ffmpeg, fps, poster_im, say)
        if vo_files and any(vo_files):
            (out / f"{name}.srt").write_text(srt(vo_lines, tl), encoding="utf-8")
        res = BragResult(out, video, poster_path, out / "share-copy.txt", out / "brag-plan.md", plan_source, tl.total, voice_engine, music_label, [])
        if first is None:
            first = res
            (out / "brag-plan.md").write_text(plan_markdown(mat, plan, tone_obj.key, tl, plan_source, fm, music_label, voice_engine), encoding="utf-8")
            (out / "share-copy.txt").write_text(share_text(plan, mat), encoding="utf-8")
        else:
            extra.append(video)
    assert first is not None
    first.extra_videos = extra
    say("Done")
    return first
