"""Line art for coloring pages, drawn by the same engines as the rest of the art: new radial mandalas, plus the repeat patterns and
shape motifs converted to outlines. Outlines are drawn with a white fill so shapes that overlap hide the lines behind them, which
is how a real coloring page reads. Everything is a 1000 x 1000 SVG, ready to colour at any page size."""
from __future__ import annotations

import math
import random
import re

from .art import MOTIFS, motif_svg
from .design import Palette
from .patterns import pattern_tile

INK = "#222222"
STROKE = 5
PATTERN_KINDS = ["scallops", "daisies", "arches", "leaves", "diamonds", "waves", "dots", "sparkles"]
DENSE = ("daisies", "leaves", "sparkles", "dots")   # scatter patterns drawn 2 x 2 so the page is full enough to colour
LINE_MOTIFS = [m for m in MOTIFS if m not in ("terrazzo",)]
_TAG = re.compile(r"<(path|circle|ellipse|rect|polygon|line|polyline)\b([^>]*?)(/?)>")


def lineart(svg_inner: str, width: float = STROKE) -> str:
    """Turn filled shapes into outlined shapes with a white fill (so overlaps hide what is behind). Thick strokes (bands, wavy ribbons)
    become outlined bands; thin strokes keep their width in ink colour."""
    def fix(m: re.Match) -> str:
        tag, attrs, close = m.group(1), m.group(2), m.group(3)
        attrs = re.sub(r"\s(opacity|fill-opacity|stroke-opacity)='[^']*'", "", attrs)
        sw = re.search(r"stroke-width='([\d.]+)'", attrs)
        stroked = "stroke='" in attrs
        if stroked and sw and float(sw.group(1)) > 3 * width and "fill='none'" in attrs:   # a band: black outline under a white core
            w = float(sw.group(1))
            outer = re.sub(r"stroke='#[0-9a-fA-F]{3,8}'", f"stroke='{INK}'", re.sub(r"stroke-width='[\d.]+'", f"stroke-width='{w + 2 * width:.1f}'", attrs))
            inner = re.sub(r"stroke='#[0-9a-fA-F]{3,8}'", "stroke='#ffffff'", attrs)
            return f"<{tag}{outer}{close}><{tag}{inner}{close}>"
        if "fill='" in attrs:
            attrs = re.sub(r"fill='#[0-9a-fA-F]{3,8}'", "fill='#ffffff'", attrs)
        else:
            attrs += " fill='#ffffff'"
        attrs = re.sub(r"stroke='#[0-9a-fA-F]{3,8}'", f"stroke='{INK}'", attrs)
        if not stroked and "fill='none'" not in attrs:
            attrs += f" stroke='{INK}' stroke-width='{width}' stroke-linejoin='round'"
        elif stroked and not sw:
            attrs += f" stroke-width='{width}'"
        return f"<{tag}{attrs}{close}>"
    svg_inner = re.sub(r"(<g\b[^>]*?)\s(?:fill|stroke)='#[0-9a-fA-F]{3,8}'", r"\1", svg_inner)   # group colours would only be inherited by shapes we already set
    return _TAG.sub(fix, svg_inner)


def _wrap_svg(inner: str) -> str:
    return f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 1000' preserveAspectRatio='xMidYMid meet'>{inner}</svg>"


def _inner(svg: str) -> str:
    return re.sub(r"^<svg[^>]*>|</svg>$", "", svg.strip())


# --------------------------------------------------------------------------- mandalas
def _petal(s: float) -> str:
    return f"M0 {s:.1f} C{s * .7:.1f} {s * .3:.1f} {s * .5:.1f} {-s * .6:.1f} 0 {-s:.1f} C{-s * .5:.1f} {-s * .6:.1f} {-s * .7:.1f} {s * .3:.1f} 0 {s:.1f}Z"


def _element(kind: str, s: float) -> str:
    if kind == "petal":
        return f"<path d='{_petal(s)}'/>"
    if kind == "circle":
        return f"<circle cx='0' cy='0' r='{s * .6:.1f}'/><circle cx='0' cy='0' r='{s * .24:.1f}'/>"
    if kind == "triangle":
        return f"<polygon points='0,{-s:.1f} {s * .62:.1f},{s * .6:.1f} {-s * .62:.1f},{s * .6:.1f}'/>"
    if kind == "diamond":
        return f"<polygon points='0,{-s:.1f} {s * .55:.1f},0 0,{s:.1f} {-s * .55:.1f},0'/>"
    if kind == "arc":
        return f"<path d='M{-s * .7:.1f} {s * .4:.1f} A{s * .7:.1f} {s * .7:.1f} 0 0 1 {s * .7:.1f} {s * .4:.1f} Z'/>"
    if kind == "drop":
        return f"<path d='M0 {-s:.1f} C{s * .8:.1f} {-s * .1:.1f} {s * .6:.1f} {s * .9:.1f} 0 {s * .9:.1f} C{-s * .6:.1f} {s * .9:.1f} {-s * .8:.1f} {-s * .1:.1f} 0 {-s:.1f}Z'/>"
    return f"<circle cx='0' cy='0' r='{s * .5:.1f}'/>"   # dot


ELEMENTS = ["petal", "circle", "triangle", "diamond", "arc", "drop", "dot"]


def mandala(seed: int) -> str:
    """A radial mandala: rings of repeated shapes from the outside in, with thin circles between them. Unique for every seed."""
    rng = random.Random(seed * 7919 + 13)
    rings = rng.randint(5, 8)
    parts = []
    radius = 470.0
    for i in range(rings):
        step = radius / (rings - i + 1.2)
        r = max(radius - step * .55, 60)
        n = rng.choice([8, 12, 16, 20, 24]) if i < rings - 2 else rng.choice([6, 8, 12])
        s = min(max(2 * math.pi * r / n * rng.uniform(.34, .46), 26), step * .78)
        el = rng.choice(ELEMENTS)
        parts.append(f"<circle cx='500' cy='500' r='{r + step * .1:.1f}' fill='#ffffff'/>")
        body = _element(el, s)
        parts.append("".join(f"<g transform='translate(500 500) rotate({k * 360 / n:.2f}) translate(0 {-r:.1f})'>{body}</g>" for k in range(n)))
        if rng.random() < .5:
            parts.append(f"<circle cx='500' cy='500' r='{r - s * .9:.1f}' fill='none'/>")
        radius = r - step * .65
    parts.append(f"<circle cx='500' cy='500' r='{max(radius, 40):.1f}' fill='#ffffff'/><circle cx='500' cy='500' r='{max(radius * .45, 16):.1f}' fill='#ffffff'/>")
    return _wrap_svg(lineart("".join(parts)))


def pattern_page(index: int, seed: int, pal: Palette) -> str:
    kind = PATTERN_KINDS[index % len(PATTERN_KINDS)]
    no_bg = lambda t: re.sub(r"^<rect width='1000' height='1000' fill='[^']*'/>", "", t)   # noqa: E731  (the page is white)
    if kind in DENSE:   # four different scatters, so the page is evenly full and nothing lines up along the seams
        return _wrap_svg("".join(f"<g transform='translate({i * 500} {j * 500}) scale(.5)'>{lineart(no_bg(pattern_tile(kind, pal, seed + 31 * (i * 2 + j + 1), index)), STROKE * 2)}</g>"
                                 for i in range(2) for j in range(2)))
    return _wrap_svg(lineart(no_bg(pattern_tile(kind, pal, seed, index))))


def motif_page(index: int, seed: int, pal: Palette) -> str:
    return _wrap_svg(lineart(_inner(motif_svg(LINE_MOTIFS[index % len(LINE_MOTIFS)], pal, seed))))


def page_art(i: int, seed: int, pal: Palette) -> tuple[str, str]:
    """(kind, svg) for coloring page number i: a steady mix of mandalas (40%), patterns (35%) and shape pictures (25%)."""
    slot = i % 20
    if slot in (0, 2, 4, 6, 8, 11, 14, 17):
        return "mandala", mandala(seed * 101 + i)
    if slot in (1, 3, 5, 9, 12, 15, 18):
        return "pattern", pattern_page(i, seed * 101 + i, pal)
    return "motif", motif_page(i, seed * 101 + i, pal)
