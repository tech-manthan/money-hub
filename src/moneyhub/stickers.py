"""Sticker art: the friendly children's figures from kidsart.py, filled with a palette's colours instead of left white, plus little
decorations (stars, hearts, suns, clouds, flowers). Each sticker gets a white die-cut border so it reads as a real sticker, and stickers are
packed onto printable sheets. Everything is seeded, so every pack is different."""
from __future__ import annotations

import random
import re

from PIL import Image, ImageFilter

from . import kidsart
from .design import Palette

DECOR = ["star", "heart", "sun", "cloud"]
BORDER_IN = 0.07   # white die-cut margin around each sticker


def _mix(a: str, b: str, t: float) -> str:
    ra, rb = [int(a.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)], [int(b.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ra, rb))


def fills(pal: Palette) -> list[str]:
    return [pal.accent, pal.accent2, _mix(pal.accent, "#ffffff", .55), pal.soft, _mix(pal.accent2, "#ffffff", .5), _mix(pal.accent, pal.accent2, .5)]


def recolor(inner: str, pal: Palette, seed: int) -> str:
    """Replace the white fills (and the white core of limbs) with palette colours, and the dark ink with the palette's ink."""
    rng = random.Random(seed)
    cols = fills(pal)
    start = rng.randrange(len(cols))
    n = {"i": start}

    def nxt(m: re.Match) -> str:
        n["i"] += 1
        return f"{m.group(1)}'{cols[n['i'] % len(cols)]}'"
    inner = re.sub(r"(fill=)'#ffffff'", nxt, inner)
    inner = re.sub(r"(stroke=)'#ffffff'", lambda m: f"{m.group(1)}'{cols[start]}'", inner)
    return inner.replace(kidsart.INK, pal.ink)


def sticker_svg(i: int, seed: int, theme: str, pal: Palette) -> tuple[str, str]:
    """(name, svg) for sticker number i: three in four are figures from the theme, the rest decorations."""
    pool = list(kidsart.THEMES.get(theme, kidsart.THEMES["mixed"])[1])
    random.Random(seed).shuffle(pool)
    rng = random.Random(seed * 211 + i)
    if i % 4 == 3:
        kind = DECOR[(i // 4 + seed) % len(DECOR)]
        p = kidsart.Pen(rng, 12)
        kidsart._decor(p, (500, 500), kind, 640 if kind != "cloud" else 620)
        name = kind
        inner = p.svg()
    else:
        kind = pool[(i - i // 4) % len(pool)]
        name = kidsart.NAMES[kind]
        inner = kidsart.figure(kind, seed * 977 + i, 12, False)
    return name, f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 1000'>{recolor(inner, pal, seed * 13 + i)}</svg>"


def die_cut(im: Image.Image, dpi: int = 300) -> Image.Image:
    """Trim to the artwork and add the white sticker border (transparent outside)."""
    im = im.convert("RGBA")
    box = im.getchannel("A").getbbox()
    if not box:
        return im
    im = im.crop(box)
    r = round(BORDER_IN * dpi)
    pad = r + 4
    canvas = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    canvas.paste(im, (pad, pad), im)
    alpha = canvas.getchannel("A").point(lambda v: 255 if v > 20 else 0)
    grown = alpha.filter(ImageFilter.MaxFilter(2 * r + 1 if (2 * r + 1) % 2 else 2 * r + 3)).filter(ImageFilter.GaussianBlur(1.2)).point(lambda v: 255 if v > 127 else 0)
    out = Image.new("RGBA", canvas.size, (255, 255, 255, 0))
    out.paste(Image.new("RGBA", canvas.size, (255, 255, 255, 255)), (0, 0), grown)
    out.alpha_composite(canvas)
    return out


def pack_sheet(stickers: list[Image.Image], w_px: int, h_px: int, margin_px: int, cols: int = 3, rows: int = 4, bg: str | None = None) -> Image.Image:
    """Lay stickers out in a grid, each scaled to fit its cell (never enlarged beyond the cell)."""
    sheet = Image.new("RGB", (w_px, h_px), bg or "#ffffff")
    cw, ch = (w_px - 2 * margin_px) / cols, (h_px - 2 * margin_px) / rows
    for k, im in enumerate(stickers[: cols * rows]):
        s = min((cw - 40) / im.width, (ch - 40) / im.height)
        t = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
        x = margin_px + (k % cols) * cw + (cw - t.width) / 2
        y = margin_px + (k // cols) * ch + (ch - t.height) / 2
        sheet.paste(t, (round(x), round(y)), t)
    return sheet
