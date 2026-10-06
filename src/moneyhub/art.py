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
MOTIFS = ["arches", "sun", "waves", "blobs", "botanical", "geo", "sparkles", "terrazzo", "rainbow", "scallop", "topo", "bouquet", "retro"]


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
    elif kind == "terrazzo":   # scattered speckled chips
        for _ in range(70):
            cx, cy, r = rng.randint(60, 940), rng.randint(60, 940), rng.randint(14, 46)
            n = rng.randint(5, 8)
            ang = rng.uniform(0, 6.28)
            pts = " ".join(f"{cx + r * rng.uniform(.65, 1.15) * math.cos(ang + 2 * math.pi * k / n):.0f},{cy + r * rng.uniform(.65, 1.15) * math.sin(ang + 2 * math.pi * k / n):.0f}" for k in range(n))
            parts.append(f"<polygon points='{pts}' fill='{rng.choice([accent, accent2, soft, line, accent2])}' opacity='0.95'/>")
    elif kind == "rainbow":   # boho rainbow over two clouds
        for i, c in enumerate([accent, accent2, soft, line, accent, accent2]):
            r = 400 - i * 52
            parts.append(f"<path d='M{500 - r} 760 A{r} {r} 0 0 1 {500 + r} 760' fill='none' stroke='{c}' stroke-width='44' stroke-linecap='round'/>")
        for cx, cy, sc in ((250, 790, 1.0), (760, 800, 0.85)):
            parts.append(f"<g fill='{soft}'><circle cx='{cx}' cy='{cy}' r='{60 * sc:.0f}'/><circle cx='{cx + 70 * sc:.0f}' cy='{cy + 18 * sc:.0f}' r='{48 * sc:.0f}'/>"
                         f"<circle cx='{cx - 70 * sc:.0f}' cy='{cy + 20 * sc:.0f}' r='{46 * sc:.0f}'/><rect x='{cx - 90 * sc:.0f}' y='{cy + 20 * sc:.0f}' width='{180 * sc:.0f}' height='{46 * sc:.0f}' rx='{23 * sc:.0f}'/></g>")
    elif kind == "scallop":   # overlapping fish-scale arcs
        r, cols = 80, [accent, accent2, soft, line]
        for row in range(8):
            y = 380 + row * 62
            for k in range(-1, 8):
                x = k * 2 * r + (r if row % 2 else 0)
                parts.append(f"<path d='M{x} {y} a{r} {r} 0 0 0 {2 * r} 0 Z' fill='{cols[(row + k) % 4]}' stroke='{accent}' stroke-width='3' opacity='0.96'/>")
    elif kind == "topo":   # contour lines of a hill
        for i in range(12):
            r = 440 - i * 36
            ph = [rng.uniform(0, 6.28) for _ in range(2)]
            pts = []
            for k in range(36):
                a = 2 * math.pi * k / 36
                rr = r * (1 + 0.1 * math.sin(3 * a + ph[0]) + 0.06 * math.sin(5 * a + ph[1]))
                pts.append((500 + rr * math.cos(a), 500 + rr * math.sin(a) * .92))
            d = "M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in pts) + "Z"
            parts.append(f"<path d='{d}' fill='none' stroke='{accent if i % 3 == 0 else accent2 if i % 3 == 1 else line}' stroke-width='{7 if i % 3 == 0 else 4}' stroke-linejoin='round'/>")
    elif kind == "bouquet":   # a handful of stems with leaves and blooms
        for s_i, x0 in enumerate((260, 380, 500, 620, 740)):
            top = 230 + abs(s_i - 2) * 90
            parts.append(f"<path d='M{x0} 930 C{x0 + (s_i - 2) * -20} 700 {x0 + (s_i - 2) * 30} 520 {500 + (s_i - 2) * 90} {top}' stroke='{accent}' stroke-width='8' fill='none' stroke-linecap='round'/>")
            bx, by = 500 + (s_i - 2) * 90, top
            for k in range(7):
                a = 2 * math.pi * k / 7
                parts.append(f"<ellipse cx='{bx + 34 * math.cos(a):.0f}' cy='{by + 34 * math.sin(a):.0f}' rx='24' ry='14' fill='{[accent2, soft, accent2, line, soft][s_i % 5]}' transform='rotate({math.degrees(a):.0f} {bx + 34 * math.cos(a):.0f} {by + 34 * math.sin(a):.0f})'/>")
            parts.append(f"<circle cx='{bx}' cy='{by}' r='18' fill='{accent}'/>")
            for j in range(3):
                ly = 860 - j * 110
                side = -1 if (j + s_i) % 2 else 1
                parts.append(f"<ellipse cx='{x0 + side * 38}' cy='{ly}' rx='46' ry='17' fill='{accent if j % 2 else accent2}' transform='rotate({-side * 38} {x0 + side * 38} {ly})' opacity='0.92'/>")
    elif kind == "retro":   # 70s concentric bands from a corner
        for i, c in enumerate([accent, accent2, soft, line, accent, accent2][::-1]):
            r = 980 - i * 150
            parts.append(f"<path d='M0 1000 L0 {1000 - r} A{r} {r} 0 0 1 {r} 1000 Z' fill='{c}'/>")
        parts.append(f"<circle cx='760' cy='260' r='110' fill='{accent2}'/><circle cx='760' cy='260' r='60' fill='{soft}'/>")
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
    avail = {**{n: p.available() for n, p in PROVIDERS.items()}, **{n: p.available() for n, p in SVG_PROVIDERS.items()}}
    return [{"name": n, "available": avail[n], "enabled": n in chain} for n in [*PROVIDERS, *SVG_PROVIDERS]]


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


# ------------------------------------------------------------------ vector art drawn by a language model (claude -p etc.)
_SVG_TAGS = {"svg", "g", "path", "circle", "ellipse", "rect", "line", "polyline", "polygon", "defs", "lineargradient", "radialgradient", "stop", "clippath"}
_SVG_ATTRS = {"d", "cx", "cy", "r", "rx", "ry", "x", "y", "x1", "y1", "x2", "y2", "width", "height", "points", "fill", "stroke", "stroke-width",
              "stroke-linecap", "stroke-linejoin", "opacity", "fill-opacity", "stroke-opacity", "transform", "viewbox", "xmlns", "id", "offset",
              "stop-color", "stop-opacity", "gradientunits", "gradienttransform", "fx", "fy", "clip-path", "fill-rule", "clip-rule",
              "stroke-dasharray", "preserveaspectratio", "version", "stroke-miterlimit"}


def sanitize_svg(svg: str) -> str | None:
    """Keep only plain vector shapes from model output: no scripts, text, images, links or external references.
    Returns a cleaned <svg> string, or None when it is unusable."""
    import re
    import xml.etree.ElementTree as ET

    svg = re.sub(r"<!DOCTYPE[^>]*>|<!ENTITY[^>]*>|<\?xml[^>]*\?>", "", svg).strip()
    if len(svg) > 60_000:
        return None
    try:
        root = ET.fromstring(svg)
    except ET.ParseError:
        return None
    shapes = 0
    for el in root.iter():
        tag = el.tag.split("}")[-1].lower()
        if tag not in _SVG_TAGS:
            return None
        shapes += tag in {"path", "circle", "ellipse", "rect", "line", "polyline", "polygon"}
        for k, v in list(el.attrib.items()):
            name = k.split("}")[-1].lower()
            low = v.lower()
            if name not in _SVG_ATTRS or "javascript:" in low or "data:" in low or "http" in low and name != "xmlns" \
                    or ("url(" in low and not re.fullmatch(r"\s*url\(#[\w-]+\)\s*", low)):
                return None
    if shapes < 3 or root.tag.split("}")[-1].lower() != "svg":
        return None
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    if "viewBox" not in root.attrib:
        root.set("viewBox", "0 0 1000 1000")
    for k in ("width", "height"):
        root.attrib.pop(k, None)
    root.set("preserveAspectRatio", "xMidYMid meet")
    return ET.tostring(root, encoding="unicode")


class LLMSvgProvider:
    """Asks the writing model (Claude Code `claude -p`, the Anthropic API, Gemini...) to draw flat vector motifs.
    Needs no image key: it uses whichever writing helper is already set up."""
    name = "claude_svg"

    def available(self) -> bool:
        from .llm import get_router
        r = get_router()
        return any((p := r.provider(n)) and p.available() for n in r.chain("art") if n != "builtin")

    def motifs(self, palette: Palette, audience: str, mood: str, count: int = 3, providers: list[str] | None = None) -> list[str]:
        import re

        from .llm import get_router
        r = get_router()
        colours = f"{palette.accent}, {palette.accent2}, {palette.soft}, {palette.line}"
        prompt = (
            f"Draw {count} different decorative SVG motifs for printable wall art aimed at {audience} (mood: {mood}). "
            f"Use ONLY these colours: {colours}. Flat vector style, simple confident shapes, generous empty space, no text, no people, "
            "no <image>, no <script>, no <text>, no external links, no filters. Each one must be a complete <svg> with "
            "viewBox=\"0 0 1000 1000\" and a transparent background, using only path, circle, ellipse, rect, line, polygon, polyline and g. "
            f"Reply with exactly {count} <svg>...</svg> blocks separated by a line containing only ---. No other text.")
        for n in r.chain("art", providers):
            p = r.provider(n) if n != "builtin" else None
            if not p or not p.available():
                continue
            try:
                raw = p.complete("You are a precise vector illustrator who outputs only valid SVG.", prompt, max_tokens=12000)
            except Exception:  # noqa: BLE001 - try the next provider
                continue
            found = [x for x in (sanitize_svg(m) for m in re.findall(r"<svg\b.*?</svg>", raw, re.S | re.I)) if x]
            if found:
                return found
        return []


SVG_PROVIDERS = {"claude_svg": LLMSvgProvider()}
ALL_ART_PROVIDERS = [*PROVIDERS, *SVG_PROVIDERS]
