"""Procedural soundtrack: music + sound effects synthesised with NumPy (no samples, so no licence questions), then mastered
with ffmpeg. Everything is deterministic for a given seed."""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 44100
_MAJOR = [0, 2, 4, 5, 7, 9, 11]
_MINOR = [0, 2, 3, 5, 7, 8, 10]

# mood -> key (midi root), scale, progression (scale degrees, 0-based), drums, density, brightness
MOODS: dict[str, dict] = {
    "bright": dict(root=60, scale=_MAJOR, prog=[0, 4, 5, 3], drums="four", arp=True, bass="eighth", pad=0.5, cut=3200, swing=0.0),
    "calm": dict(root=62, scale=_MAJOR, prog=[0, 5, 3, 4], drums="soft", arp=True, bass="long", pad=0.9, cut=2200, swing=0.0),
    "corporate": dict(root=65, scale=_MAJOR, prog=[0, 3, 4, 5], drums="four", arp=True, bass="eighth", pad=0.4, cut=3600, swing=0.0),
    "driving": dict(root=57, scale=_MINOR, prog=[0, 5, 2, 6], drums="drive", arp=True, bass="sixteenth", pad=0.25, cut=4200, swing=0.0),
    "minimal": dict(root=60, scale=_MAJOR, prog=[0, 3, 0, 4], drums="none", arp=False, bass="long", pad=0.7, cut=1800, swing=0.0),
    "epic": dict(root=57, scale=_MINOR, prog=[0, 5, 2, 6], drums="epic", arp=False, bass="long", pad=1.0, cut=2800, swing=0.0),
}


def _hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def _env(n: int, a: float, d: float, s: float, r: float, hold: float | None = None) -> np.ndarray:
    """ADSR envelope of n samples (hold = sustain duration; defaults to the rest of the note)."""
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    ns = max(0, n - na - nd - nr) if hold is None else int(hold * SR)
    e = np.concatenate([np.linspace(0, 1, max(na, 1), endpoint=False), np.linspace(1, s, max(nd, 1), endpoint=False),
                        np.full(ns, s), np.linspace(s, 0, max(nr, 1))])
    return e[:n] if len(e) >= n else np.pad(e, (0, n - len(e)))


def _fft_conv(x: np.ndarray, k: np.ndarray) -> np.ndarray:
    n = len(x) + len(k) - 1
    nfft = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(k, nfft), nfft)[:n]


def lowpass(x: np.ndarray, cutoff: float, taps: int = 255) -> np.ndarray:
    fc = min(cutoff / SR, 0.49)
    n = np.arange(taps) - (taps - 1) / 2
    k = np.sinc(2 * fc * n) * np.hanning(taps)
    k /= k.sum()
    return _fft_conv(x, k)[taps // 2: taps // 2 + len(x)]


def highpass(x: np.ndarray, cutoff: float, taps: int = 255) -> np.ndarray:
    return x - lowpass(x, cutoff, taps)


def reverb(x: np.ndarray, mix: float = 0.25, seconds: float = 1.4, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 7, n))
    ir = lowpass(ir, 5000)
    ir /= np.abs(ir).sum() + 1e-9
    wet = _fft_conv(x, ir * 6)[: len(x)]
    return (1 - mix) * x + mix * wet


def _place(buf: np.ndarray, sig: np.ndarray, t: float, gain: float = 1.0, pan: float = 0.0) -> None:
    i = int(t * SR)
    if i >= buf.shape[1] or i < 0:
        return
    j = min(buf.shape[1], i + len(sig))
    seg = sig[: j - i] * gain
    buf[0, i:j] += seg * (1 - max(0, pan))
    buf[1, i:j] += seg * (1 + min(0, pan))


# ----------------------------------------------------------------------------- instruments
def kick() -> np.ndarray:
    n = int(0.42 * SR)
    t = np.arange(n) / SR
    f = 42 + 120 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 9) * 0.95 + np.random.default_rng(1).standard_normal(n) * np.exp(-t * 180) * 0.12


def snare(rng) -> np.ndarray:
    n = int(0.26 * SR)
    t = np.arange(n) / SR
    noise = highpass(rng.standard_normal(n), 1400) * np.exp(-t * 20)
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 28) * 0.5
    return (noise * 0.8 + tone) * 0.7


def clap(rng) -> np.ndarray:
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    burst = sum(np.roll(np.exp(-t * 90), int(k * 0.011 * SR)) for k in range(3))
    return highpass(rng.standard_normal(n), 900) * burst * 0.5 * np.exp(-t * 10)


def hat(rng, open_: bool = False) -> np.ndarray:
    n = int((0.16 if open_ else 0.05) * SR)
    t = np.arange(n) / SR
    return highpass(rng.standard_normal(n), 7000, 127) * np.exp(-t * (28 if open_ else 80)) * 0.28


def bass_note(freq: float, dur: float) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    saw = 2 * ((freq * t) % 1) - 1
    sig = lowpass(0.55 * np.sin(2 * np.pi * freq * t) + 0.35 * saw, 420, 127)
    return sig * _env(n, 0.005, 0.08, 0.7, min(0.08, dur / 2))


def pad_chord(freqs: list[float], dur: float, cut: float) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for f in freqs:
        for det in (-0.004, 0.0, 0.004):
            ff = f * (1 + det)
            sig += 2 * ((ff * t) % 1) - 1
    sig = lowpass(sig / (3 * len(freqs)), cut, 191)
    return sig * _env(n, min(0.5, dur * 0.3), 0.2, 0.8, min(0.6, dur * 0.4))


def pluck(freq: float, dur: float = 0.35) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    tri = 2 * np.abs(2 * ((freq * t) % 1) - 1) - 1
    return lowpass(tri * 0.7 + np.sin(2 * np.pi * 2 * freq * t) * 0.15, 5200, 127) * np.exp(-t * 9)


def bell(freq: float, dur: float = 1.2) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    mod = np.sin(2 * np.pi * freq * 3.5 * t) * 2.2 * np.exp(-t * 5)
    return np.sin(2 * np.pi * freq * t + mod) * np.exp(-t * 3.2) * 0.5


# ----------------------------------------------------------------------------- sound effects
def sfx(kind: str, seed: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if kind == "whoosh":
        n = int(0.55 * SR)
        t = np.arange(n) / SR
        noise = rng.standard_normal(n)
        sweep = lowpass(noise, 2500) * 0.0
        out = np.zeros(n)
        chunk = 2048
        for i in range(0, n, chunk):          # band-pass noise with a rising centre
            c = 400 + 3800 * (i / n) ** 1.2
            seg = noise[i:i + chunk]
            out[i:i + chunk] = (lowpass(seg, c * 1.4, 63) - lowpass(seg, c * 0.6, 63))[: len(seg)]
        env = np.sin(np.pi * np.clip(t / 0.55, 0, 1)) ** 2
        return out * env * 2.2
    if kind == "pop":
        n = int(0.14 * SR)
        t = np.arange(n) / SR
        f = 380 + 700 * np.exp(-t * 40)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 32) * 0.7
    if kind == "tick":
        n = int(0.05 * SR)
        t = np.arange(n) / SR
        return lowpass(rng.standard_normal(n), 2800, 63) * np.exp(-t * 110) * 0.5 + np.sin(2 * np.pi * 1500 * t) * np.exp(-t * 140) * 0.25
    if kind == "type":
        n = int(0.03 * SR)
        t = np.arange(n) / SR
        return lowpass(rng.standard_normal(n), 3500, 63) * np.exp(-t * 200) * 0.45
    if kind == "chime":
        a, b = bell(1320, 1.4) * 0.8, bell(1980, 1.0) * 0.4
        a[: len(b)] += b
        return a
    if kind == "riser":
        n = int(1.4 * SR)
        t = np.arange(n) / SR
        noise = highpass(rng.standard_normal(n), 1500, 127)
        f = 220 * 2 ** (t * 1.6)
        sw = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
        return (noise * 0.5 + sw) * (t / 1.4) ** 2 * 1.2
    if kind == "impact":
        n = int(1.6 * SR)
        t = np.arange(n) / SR
        body = np.sin(2 * np.pi * np.cumsum(48 + 90 * np.exp(-t * 14)) / SR) * np.exp(-t * 3.2)
        crack = lowpass(rng.standard_normal(n), 2500, 127) * np.exp(-t * 14) * 0.5
        return reverb(body + crack, 0.35, 1.2)[:n] * 0.9
    if kind == "flash":
        n = int(0.3 * SR)
        t = np.arange(n) / SR
        return (highpass(rng.standard_normal(n), 3000, 127) * np.exp(-t * 18) * 0.55 + np.sin(2 * np.pi * 90 * t) * np.exp(-t * 14) * 0.5)
    raise ValueError(f"unknown sfx {kind}")


SFX_LEVEL = {"whoosh": 0.30, "pop": 0.26, "tick": 0.20, "type": 0.14, "chime": 0.22, "riser": 0.26, "impact": 0.55, "flash": 0.30}


# ----------------------------------------------------------------------------- music
def compose(mood: str, bpm: int, duration: float, seed: int = 1) -> np.ndarray:
    """Stereo float array [2, n] for `duration` seconds, with intro build, full groove and a closing hit."""
    cfg = MOODS[mood]
    rng = np.random.default_rng(seed)
    n = int((duration + 1.2) * SR)           # + tail for reverb/ring-out
    mix = np.zeros((2, n))
    beat = 60.0 / bpm
    bar = beat * 4
    scale = cfg["scale"]

    def note(deg: int, octave: int = 0) -> float:
        o, d = divmod(deg, 7)
        return _hz(cfg["root"] + scale[d] + 12 * (o + octave))

    def triad(deg: int) -> list[float]:
        return [note(deg), note(deg + 2), note(deg + 4)]

    bars = int(np.ceil(duration / bar))
    kicks: list[float] = []
    k_s, hat_buf = kick(), None
    for b in range(bars):
        t0 = b * bar
        deg = cfg["prog"][b % len(cfg["prog"])]
        full = b >= 1 and (t0 + bar) <= duration + 0.01          # first bar is the intro
        last = t0 + bar >= duration - 0.01
        # pad
        _place(mix, pad_chord([f / 2 for f in triad(deg)] + [note(deg + 7)], bar + 0.4, cfg["cut"]), t0, 0.5 * cfg["pad"], 0.0)
        # bass
        if b >= 1 or cfg["bass"] == "long":
            if cfg["bass"] == "long":
                _place(mix, bass_note(note(deg, -2), bar * 0.95), t0, 0.5)
            else:
                step = beat / (2 if cfg["bass"] == "eighth" else 4)
                for i in range(int(bar / step)):
                    d = deg if i % 4 != 3 else deg + 4
                    _place(mix, bass_note(note(d, -2), step * 0.9), t0 + i * step, 0.42)
        # arpeggio / plucks
        if cfg["arp"] and b >= 1:
            tones = triad(deg) + [note(deg + 7)]
            step = beat / 2
            for i in range(8):
                f = tones[[0, 1, 2, 3, 2, 1, 2, 1][i]]
                _place(mix, pluck(f * 2), t0 + i * step, 0.2 + (0.05 if i % 2 == 0 else 0), (-0.3 if i % 2 else 0.3))
        # drums
        style = cfg["drums"]
        if style != "none":
            for q in range(4):
                tq = t0 + q * beat
                dense = (b >= 1)
                if style in ("four", "drive") and dense:
                    _place(mix, k_s, tq, 0.95); kicks.append(tq)
                elif style == "soft" and dense and q % 2 == 0:
                    _place(mix, k_s, tq, 0.55); kicks.append(tq)
                elif style == "epic" and (q == 0) and dense:
                    _place(mix, k_s, tq, 1.0); kicks.append(tq)
                if style in ("four", "drive", "soft") and q in (1, 3) and dense:
                    _place(mix, clap(rng) if style != "drive" else snare(rng), tq, 0.45 if style != "soft" else 0.25)
                if style in ("four", "drive") and dense:
                    _place(mix, hat(rng), tq + beat / 2, 0.30)
                    if style == "drive":
                        _place(mix, hat(rng), tq + beat / 4, 0.18)
                        _place(mix, hat(rng), tq + 3 * beat / 4, 0.18)
                if style == "soft" and dense:
                    _place(mix, hat(rng), tq + beat / 2, 0.16)
        if last:
            _place(mix, sfx("impact"), min(t0 + bar - 0.02, duration - 0.3), 0.5)
            _place(mix, bell(note(deg + 7, 1), 1.6), min(t0 + bar - 0.02, duration - 0.3), 0.5)
    # sidechain: duck everything slightly on each kick
    duck = np.ones(n)
    kn = int(0.22 * SR)
    shape = 1 - 0.38 * np.exp(-np.linspace(0, 6, kn))
    for kt in kicks:
        i = int(kt * SR)
        seg = duck[i:i + kn]
        duck[i:i + len(seg)] = np.minimum(seg, shape[: len(seg)])
    mix *= duck
    # fade in/out
    fi, fo = int(0.15 * SR), int(0.5 * SR)
    end = int((duration + 0.9) * SR)
    mix[:, :fi] *= np.linspace(0, 1, fi)
    mix[:, end - fo:end] *= np.linspace(1, 0, fo)
    mix[:, end:] = 0
    mix = np.stack([reverb(mix[0], 0.14, 1.1, 5), reverb(mix[1], 0.14, 1.1, 6)])
    return mix[:, : int((duration + 1.0) * SR)]


def render_sfx_track(events: list[tuple[float, str]], duration: float) -> np.ndarray:
    n = int((duration + 1.0) * SR)
    buf = np.zeros((2, n))
    cache: dict[str, np.ndarray] = {}
    for t, kind in events:
        if kind not in cache:
            cache[kind] = lowpass(sfx(kind), 9000, 63)       # keep effects soft, never spiky
        _place(buf, cache[kind], t, SFX_LEVEL.get(kind, 0.25))
    return buf


def duck_under(music: np.ndarray, voice_spans: list[tuple[float, float]], depth: float = 0.35) -> np.ndarray:
    g = np.ones(music.shape[1])
    ramp = int(0.15 * SR)
    for a, b in voice_spans:
        i, j = int(max(0, a - 0.1) * SR), min(music.shape[1], int((b + 0.2) * SR))
        g[i:j] = np.minimum(g[i:j], depth)
        if i - ramp >= 0:
            g[i - ramp:i] = np.minimum(g[i - ramp:i], np.linspace(1, depth, ramp))
        if j + ramp <= len(g):
            g[j:j + ramp] = np.minimum(g[j:j + ramp], np.linspace(depth, 1, ramp))
    return music * g


def write_wav(path: Path, audio: np.ndarray) -> Path:
    peak = float(np.max(np.abs(audio))) or 1.0
    if peak > 0.98:
        audio = audio / peak * 0.98
    data = (np.clip(audio.T, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    return path


def master(src: Path, dst: Path, ffmpeg: str, duration: float) -> Path:
    """Loudness-normalise (about -16 LUFS, safe for social platforms) and add a limiter + a short fade-out."""
    fade = f"afade=t=out:st={max(0.1, duration - 0.5):.2f}:d=0.6"
    af = f"highpass=f=30,acompressor=threshold=-18dB:ratio=2.5:attack=15:release=160,loudnorm=I=-16:TP=-1.5:LRA=9,{fade}"
    r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(src), "-af", af, "-ar", str(SR), "-ac", "2", str(dst)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg mastering failed: {r.stderr[-300:]}")
    return dst
