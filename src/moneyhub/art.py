"""Decorative art: procedural SVG motifs (always available, licence-free) and optional AI image providers.

AI providers are off unless listed under `render.art` in moneyhub.yaml. Each is an HTTP API you supply a key for;
read that provider's terms before selling images they generate."""
from __future__ import annotations

import base64
import io
import math
import os
import random
from abc import ABC, abstractmethod

import httpx
from PIL import Image

from .config import get_config
from .design import Palette

# ------------------------------------------------------------------ procedural motifs
MOTIFS = ["arches", "sun", "waves", "blobs", "botanical", "geo", "sparkles"]


def _cols(p: Palette) -> list[str]:
    return [p.accent, p.accent2, p.soft, p.line]


def motif_svg(kind: str, p: Palette, seed: int, on_dark: bool = False) -> str:
    """Return an <svg> string (viewBox 0 0 1000 1000, transparent background)."""
    rng = random.Random(seed)
    accent, accent2, soft, line = p.accent, p.accent2, p.soft, p.line
    if on_dark:  # drawn over an accent-coloured page: use light tones
        accent, accent2, soft, line = p.paper, p.soft, p.accent2, p.line
    parts: list[str] = []
    if kind == "arches":
        cx, base = 500, 820
        for i, (r, c) in enumerate(zip([330, 270, 210, 150, 90], [accent, accent2, soft, line, accent])):
            parts.append(f"<path d='M{cx - r} {base} A{r} {r} 0 0 1 {cx + r} {base} Z' fill='{c}'/>")
    elif kind == "sun":
        parts.append(f"<circle cx='500' cy='430' r='170' fill='{accent2}'/>")
        for a in range(0, 360, 20):
            x1, y1 = 500 + 215 * math.cos(math.radians(a)), 430 + 215 * math.sin(math.radians(a))
            x2, y2 = 500 + 300 * math.cos(math.radians(a)), 430 + 300 * math.sin(math.radians(a))
            parts.append(f"<line x1='{x1:.0f}' y1='{y1:.0f}' x2='{x2:.0f}' y2='{y2:.0f}' stroke='{accent2}' stroke-width='14' stroke-linecap='round'/>")
        parts.append(f"<ellipse cx='260' cy='900' rx='420' ry='210' fill='{accent}'/><ellipse cx='760' cy='930' rx='460' ry='190' fill='{soft}'/>")
    elif kind == "waves":
        for i, c in enumerate([soft, line, accent2, accent]):
            y = 520 + i * 105
            amp = 55 + i * 10
            d = f"M0 {y} " + " ".join(f"Q{x + 125} {y - amp if (x // 250) % 2 == 0 else y + amp} {x + 250} {y}" for x in range(0, 1000, 250)) + " V1000 H0 Z"
            parts.append(f"<path d='{d}' fill='{c}'/>")
    elif kind == "blobs":
        for c, (cx, cy, r) in zip([soft, accent2, accent], [(380, 430, 250), (640, 560, 200), (470, 640, 150)]):
            pts = []
            n = 9
            ph = [rng.uniform(0, 6.28) for _ in range(3)]
            for k in range(n):
                a = 2 * math.pi * k / n
                rr = r * (1 + 0.18 * math.sin(2 * a + ph[0]) + 0.1 * math.sin(3 * a + ph[1]))
                pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
            d = "M" + " ".join(f"{x:.0f},{y:.0f}" for x, y in pts[:1])
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                d += f" Q{x0:.0f},{y0:.0f} {mx:.0f},{my:.0f}"
            parts.append(f"<path d='{d} Z' fill='{c}' opacity='0.92'/>")
    elif kind == "botanical":
        parts.append(f"<path d='M500 960 C470 760 540 560 500 300' stroke='{accent}' stroke-width='9' fill='none' stroke-linecap='round'/>")
        for i in range(9):
            t = i / 8
            y = 900 - t * 560
            x = 500 + (-18 if i % 2 else 12) * (1 - t) * 3
            side = -1 if i % 2 else 1
            L = 150 - t * 55
            ang = side * (55 - t * 15)
            c = accent if i % 3 else accent2
            parts.append(f"<ellipse cx='{x + side * L * 0.55:.0f}' cy='{y:.0f}' rx='{L * 0.55:.0f}' ry='{L * 0.2:.0f}' fill='{c}' transform='rotate({-ang} {x:.0f} {y:.0f})' opacity='0.95'/>")
        parts.append(f"<ellipse cx='500' cy='290' rx='34' ry='70' fill='{accent2}'/>")
    elif kind == "geo":
        cell = 250
        for gx in range(4):
            for gy in range(4):
                x, y = gx * cell, gy * cell
                shape = rng.choice(["c", "q1", "q2", "s", "h"])
                c = rng.choice([accent, accent2, soft, line])
                if shape == "c":
                    parts.append(f"<circle cx='{x + cell / 2}' cy='{y + cell / 2}' r='{cell / 2 - 14}' fill='{c}'/>")
                elif shape == "q1":
                    parts.append(f"<path d='M{x} {y + cell} A{cell} {cell} 0 0 1 {x + cell} {y} L{x + cell} {y + cell} Z' fill='{c}'/>")
                elif shape == "q2":
                    parts.append(f"<path d='M{x} {y} A{cell} {cell} 0 0 0 {x + cell} {y + cell} L{x} {y + cell} Z' fill='{c}'/>")
                elif shape == "s":
                    parts.append(f"<rect x='{x + 24}' y='{y + 24}' width='{cell - 48}' height='{cell - 48}' fill='{c}'/>")
                else:
                    parts.append(f"<path d='M{x + 10} {y + cell / 2} A{cell / 2 - 10} {cell / 2 - 10} 0 0 1 {x + cell - 10} {y + cell / 2} Z' fill='{c}'/>")
    else:  # sparkles
        for _ in range(16):
            x, y, s = rng.randint(80, 920), rng.randint(80, 920), rng.randint(24, 90)
            c = rng.choice([accent, accent2, soft])
            parts.append(f"<path d='M{x} {y - s} Q{x} {y} {x + s} {y} Q{x} {y} {x} {y + s} Q{x} {y} {x - s} {y} Q{x} {y} {x} {y - s}Z' fill='{c}'/>")
    return f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 1000' preserveAspectRatio='xMidYMid meet'>{''.join(parts)}</svg>"


# ------------------------------------------------------------------ optional AI providers
class ImageProvider(ABC):
    name = "base"

    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def generate(self, prompt: str, size: tuple[int, int]) -> Image.Image: ...


def _round64(v: int) -> int:
    return max(256, min(1440, int(round(v / 64)) * 64))


class HuggingFaceProvider(ImageProvider):
    """FLUX.1-schnell (Apache-2.0 model) through Hugging Face inference. Needs HF_TOKEN."""
    name = "huggingface"

    def available(self) -> bool:
        return bool(os.environ.get("HF_TOKEN"))

    def generate(self, prompt, size):
        w, h = _round64(size[0]), _round64(size[1])
        r = httpx.post(
            "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell",
            headers={"Authorization": f"Bearer {os.environ['HF_TOKEN']}"},
            json={"inputs": prompt, "parameters": {"width": w, "height": h}}, timeout=180)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB")


class TogetherProvider(ImageProvider):
    name = "together"

    def available(self) -> bool:
        return bool(os.environ.get("TOGETHER_API_KEY"))

    def generate(self, prompt, size):
        r = httpx.post(
            "https://api.together.xyz/v1/images/generations",
            headers={"Authorization": f"Bearer {os.environ['TOGETHER_API_KEY']}"},
            json={"model": "black-forest-labs/FLUX.1-schnell-Free", "prompt": prompt, "width": _round64(size[0]),
                  "height": _round64(size[1]), "steps": 4, "n": 1, "response_format": "b64_json"}, timeout=180)
        r.raise_for_status()
        return Image.open(io.BytesIO(base64.b64decode(r.json()["data"][0]["b64_json"]))).convert("RGB")


class OpenAIImageProvider(ImageProvider):
    name = "openai"

    def available(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY"))

    def generate(self, prompt, size):
        portrait = size[1] >= size[0]
        r = httpx.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            json={"model": "gpt-image-1", "prompt": prompt, "size": "1024x1536" if portrait else "1536x1024"}, timeout=240)
        r.raise_for_status()
        return Image.open(io.BytesIO(base64.b64decode(r.json()["data"][0]["b64_json"]))).convert("RGB")


class ComfyLikeProvider(ImageProvider):
    """Any local server that returns image bytes for POST {url} json {prompt,width,height} (e.g. a tiny wrapper around
    diffusers/MLX on your Mac). Set MONEYHUB_ART_URL."""
    name = "local_http"

    def available(self) -> bool:
        return bool(os.environ.get("MONEYHUB_ART_URL"))

    def generate(self, prompt, size):
        r = httpx.post(os.environ["MONEYHUB_ART_URL"], json={"prompt": prompt, "width": size[0], "height": size[1]}, timeout=600)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB")


PROVIDERS: dict[str, ImageProvider] = {p.name: p for p in (HuggingFaceProvider(), TogetherProvider(), OpenAIImageProvider(), ComfyLikeProvider())}


def art_status() -> list[dict]:
    chain = get_config().get("render.art") or []
    return [{"name": n, "available": n in PROVIDERS and PROVIDERS[n].available(), "enabled": n in chain} for n in PROVIDERS]


def generate_art(prompt: str, size: tuple[int, int], providers: list[str] | None = None) -> tuple[Image.Image, str] | None:
    """First configured provider that works, or None (callers then use procedural motifs)."""
    for n in providers if providers is not None else (get_config().get("render.art") or []):
        p = PROVIDERS.get(n)
        if not p or not p.available():
            continue
        try:
            return p.generate(prompt, size), n
        except Exception:  # noqa: BLE001 - try the next provider
            continue
    return None
