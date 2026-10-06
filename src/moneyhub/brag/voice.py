"""Voice-over engines (all optional, all local): Kokoro (Apache-2.0, `pip install kokoro-onnx` + model files),
macOS `say`, espeak-ng. Voice is off unless you pass --voice."""
from __future__ import annotations

import os
import shutil
import subprocess
import urllib.request
import wave
from pathlib import Path

import numpy as np

from ..config import get_config

KOKORO_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
KOKORO_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")


def kokoro_dir() -> Path:
    return Path(os.environ.get("MONEYHUB_KOKORO_DIR") or get_config().get("voice.kokoro_dir") or Path.home() / ".cache" / "moneyhub" / "kokoro")


def install_kokoro(progress=print) -> Path:
    d = kokoro_dir()
    d.mkdir(parents=True, exist_ok=True)
    for f in KOKORO_FILES:
        dst = d / f
        if dst.exists() and dst.stat().st_size > 1_000_000:
            continue
        progress(f"downloading {f} ...")
        urllib.request.urlretrieve(f"{KOKORO_BASE}/{f}", dst)
    return d


def _wav_duration(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


class Voice:
    name = "base"

    def available(self) -> bool:
        raise NotImplementedError

    def synth(self, text: str, out: Path, ffmpeg: str) -> float:
        """Write a 44.1 kHz mono WAV and return its length in seconds."""
        raise NotImplementedError


class KokoroVoice(Voice):
    name = "kokoro"

    def __init__(self):
        self._k = None

    def available(self) -> bool:
        try:
            import kokoro_onnx  # noqa: F401
        except ImportError:
            return False
        d = kokoro_dir()
        return all((d / f).exists() for f in KOKORO_FILES)

    def synth(self, text: str, out: Path, ffmpeg: str) -> float:
        from kokoro_onnx import Kokoro

        if self._k is None:
            d = kokoro_dir()
            self._k = Kokoro(str(d / KOKORO_FILES[0]), str(d / KOKORO_FILES[1]))
        voice = os.environ.get("MONEYHUB_VOICE") or get_config().get("voice.kokoro_voice") or "af_heart"
        samples, sr = self._k.create(text, voice=voice, speed=float(get_config().get("voice.speed") or 1.0), lang="en-us")
        tmp = out.with_suffix(".raw.wav")
        data = (np.clip(np.asarray(samples), -1, 1) * 32767).astype("<i2")
        with wave.open(str(tmp), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(int(sr))
            w.writeframes(data.tobytes())
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp), "-ar", "44100", "-ac", "1", str(out)], check=True)
        tmp.unlink(missing_ok=True)
        return _wav_duration(out)


class SayVoice(Voice):
    name = "say"

    def available(self) -> bool:
        return shutil.which("say") is not None

    def synth(self, text: str, out: Path, ffmpeg: str) -> float:
        tmp = out.with_suffix(".aiff")
        voice = os.environ.get("MONEYHUB_VOICE") or get_config().get("voice.say_voice")
        subprocess.run(["say"] + (["-v", voice] if voice else []) + ["-o", str(tmp), text], check=True)
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp), "-ar", "44100", "-ac", "1", str(out)], check=True)
        tmp.unlink(missing_ok=True)
        return _wav_duration(out)


class EspeakVoice(Voice):
    name = "espeak"

    def _exe(self) -> str | None:
        return shutil.which("espeak-ng") or shutil.which("espeak")

    def available(self) -> bool:
        return self._exe() is not None

    def synth(self, text: str, out: Path, ffmpeg: str) -> float:
        tmp = out.with_suffix(".raw.wav")
        subprocess.run([self._exe(), "-s", "165", "-w", str(tmp), text], check=True)
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp), "-ar", "44100", "-ac", "1", str(out)], check=True)
        tmp.unlink(missing_ok=True)
        return _wav_duration(out)


VOICES: dict[str, Voice] = {v.name: v for v in (KokoroVoice(), SayVoice(), EspeakVoice())}


def voice_status() -> list[dict]:
    return [{"name": n, "available": v.available()} for n, v in VOICES.items()]


def pick(preferred: str | None = None) -> Voice | None:
    order = [preferred] if preferred and preferred != "auto" else []
    order += get_config().get("voice.chain") or ["kokoro", "say", "espeak"]
    for n in order:
        v = VOICES.get(n)
        if v and v.available():
            return v
    return None
