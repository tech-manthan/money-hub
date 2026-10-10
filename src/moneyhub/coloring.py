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
PATTERN_KINDS = ["scallops", "daisies", "arches", "leaves", "diamonds", "waves", "dots", "sparkles", "hearts", "stars", "ditsy", "paisley", "hexagons", "rainbows", "celestial",
                 "blobs", "memphis", "chevron", "zigzag", "plaid", "quatrefoil", "triangles", "ogee", "snowflakes", "cherries", "lemons", "tropical", "argyle", "houndstooth", "leopard"]
DENSE = ("daisies", "leaves", "sparkles", "dots")
ZOOM = {"hearts": 1.35, "stars": 1.35, "ditsy": 1.5, "paisley": 1.3, "rainbows": 1.4, "celestial": 1.4, "blobs": 1.15, "memphis": 1.4, "snowflakes": 1.4, "cherries": 1.4, "lemons": 1.35, "tropical": 1.25, "leopard": 1.35}   # small scatter shapes, enlarged so they are big enough to colour   # scatter patterns drawn 2 x 2 so the page is full enough to colour
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


def pattern_page(index: int, seed: int, pal: Palette, kind: str | None = None) -> str:
    kind = kind or PATTERN_KINDS[index % len(PATTERN_KINDS)]
    no_bg = lambda t: re.sub(r"^<rect width='1000' height='1000' fill='[^']*'/>", "", t)   # noqa: E731  (the page is white)
    if kind in DENSE:   # four different scatters, so the page is evenly full and nothing lines up along the seams
        return _wrap_svg("".join(f"<g transform='translate({i * 500} {j * 500}) scale(.5)'>{lineart(no_bg(pattern_tile(kind, pal, seed + 31 * (i * 2 + j + 1), index)), STROKE * 2)}</g>"
                                 for i in range(2) for j in range(2)))
    if kind in ZOOM:
        z = ZOOM[kind]
        t = -500 * (z - 1)
        return _wrap_svg(f"<g transform='translate({t:.0f} {t:.0f}) scale({z})'>{lineart(no_bg(pattern_tile(kind, pal, seed, index)), STROKE / z * 1.2)}</g>")
    return _wrap_svg(lineart(no_bg(pattern_tile(kind, pal, seed, index))))


def motif_page(index: int, seed: int, pal: Palette) -> str:
    return _wrap_svg(lineart(_inner(motif_svg(LINE_MOTIFS[index % len(LINE_MOTIFS)], pal, seed))))


# --------------------------------------------------------------------------- more page styles: spirograph, flower of life, stained glass, kaleidoscope, tile sampler, wreath, sunburst
def _ink(d: str, w: float = STROKE, fill: str = "none") -> str:
    return f"<path d='{d}' fill='{fill}' stroke='{INK}' stroke-width='{w}' stroke-linejoin='round' stroke-linecap='round'/>"


def spirograph(seed: int) -> str:
    rng = random.Random(seed * 31 + 7)
    out = []
    for k in range(3):
        R = 440 - k * 120
        r = rng.choice([R * q for q in (.2, .25, .3, .35, .4, .45)])
        d = r * rng.uniform(.6, 1.1)
        n = 720
        pts = []
        for i in range(n + 1):
            t = i * 2 * math.pi * (round(r) / math.gcd(round(R), round(r))) / n
            x = (R - r) * math.cos(t) + d * math.cos((R - r) / r * t)
            y = (R - r) * math.sin(t) - d * math.sin((R - r) / r * t)
            pts.append(f"{500 + x:.1f},{500 + y:.1f}")
        out.append(f"<polyline points='{' '.join(pts)}' fill='none' stroke='{INK}' stroke-width='{STROKE * .8}' stroke-linejoin='round'/>")
    out.append(f"<circle cx='500' cy='500' r='38' fill='#fff' stroke='{INK}' stroke-width='{STROKE}'/>")
    return _wrap_svg("".join(out))


def flower_of_life(seed: int) -> str:
    rng = random.Random(seed)
    r = rng.choice([125, 138, 146])
    pts = [(0, 0)]
    for ring in (1, 2):
        for k in range(6 * ring):
            side, off = divmod(k, ring)
            a1, a2 = math.radians(60 * side), math.radians(60 * (side + 2))
            x = ring * r * math.cos(a1) + off * r * (math.cos(a2) - math.cos(a1)) * 1.0
            y = ring * r * math.sin(a1) + off * r * (math.sin(a2) - math.sin(a1)) * 1.0
            pts.append((x, y))
    out = [f"<circle cx='{500 + x:.0f}' cy='{500 + y:.0f}' r='{r}' fill='none' stroke='{INK}' stroke-width='{STROKE}'/>" for x, y in pts]
    out.append(f"<circle cx='500' cy='500' r='{r * 3.0:.0f}' fill='none' stroke='{INK}' stroke-width='{STROKE * 1.6}'/>")
    out.append(f"<circle cx='500' cy='500' r='{r * 3.0 + 22:.0f}' fill='none' stroke='{INK}' stroke-width='{STROKE}'/>")
    return _wrap_svg("".join(out))


def stained_glass(seed: int) -> str:
    import numpy as np
    from scipy.spatial import Voronoi
    rng = np.random.default_rng(seed * 13 + 5)
    n = 34
    ang = rng.uniform(0, 2 * np.pi, n)
    rad = 440 * np.sqrt(rng.uniform(.02, 1, n))
    pts = np.c_[500 + rad * np.cos(ang), 500 + rad * np.sin(ang)]
    far = np.array([[500 + 2000 * math.cos(a), 500 + 2000 * math.sin(a)] for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)])
    vor = Voronoi(np.vstack([pts, far]))
    segs = []
    for (a, b) in vor.ridge_vertices:
        if a < 0 or b < 0:
            continue
        p, q = vor.vertices[a], vor.vertices[b]
        segs.append(f"M{p[0]:.1f} {p[1]:.1f} L{q[0]:.1f} {q[1]:.1f}")
    return _wrap_svg(f"<clipPath id='g'><circle cx='500' cy='500' r='460'/></clipPath><g clip-path='url(#g)'><rect width='1000' height='1000' fill='#fff'/>"
                     f"<path d='{' '.join(segs)}' fill='none' stroke='{INK}' stroke-width='{STROKE * 1.5}' stroke-linecap='round'/></g>"
                     f"<circle cx='500' cy='500' r='460' fill='none' stroke='{INK}' stroke-width='{STROKE * 2.4}'/>")


def kaleidoscope(seed: int) -> str:
    rng = random.Random(seed * 17 + 3)
    n = rng.choice([6, 8])
    wedge = []
    for j in range(5):
        cx, cy = 90 + j * 80 + rng.uniform(-10, 10), rng.uniform(-45, 45) * (1 + j * .25)
        k = rng.choice([3, 4, 5, 6])
        rr = rng.uniform(36, 52) + j * 9
        a0 = rng.uniform(0, 6.28)
        pts = " ".join(f"{cx + rr * math.cos(a0 + i * 2 * math.pi / k):.1f},{cy + rr * (math.sin(a0 + i * 2 * math.pi / k)) * rng.uniform(.7, 1.1):.1f}" for i in range(k))
        wedge.append(f"<polygon points='{pts}' fill='#fff' stroke='{INK}' stroke-width='{STROKE}' stroke-linejoin='round'/>")
    body = "".join(wedge)
    out = []
    for i in range(n):
        out.append(f"<g transform='translate(500 500) rotate({i * 360 / n:.1f})'>{body}</g>")
        out.append(f"<g transform='translate(500 500) rotate({i * 360 / n:.1f}) scale(1 -1)'>{body}</g>")
    out.append(f"<circle cx='500' cy='500' r='36' fill='#fff' stroke='{INK}' stroke-width='{STROKE}'/>")
    out.append(f"<circle cx='500' cy='500' r='470' fill='none' stroke='{INK}' stroke-width='{STROKE * 1.6}'/>")
    return _wrap_svg("".join(out))


def tile_sampler(seed: int) -> str:
    rng = random.Random(seed * 19 + 11)
    n = 4
    cell = 220
    ox = 500 - n * cell / 2
    kinds = ["rings", "diag", "dots", "check", "petals", "waves", "tri", "cross", "scales", "star"]
    out = []
    for r in range(n):
        for c in range(n):
            x, y = ox + c * cell, ox + r * cell
            kind = kinds[(r * n + c + rng.randrange(len(kinds))) % len(kinds)]
            cx, cy = x + cell / 2, y + cell / 2
            clip = f"t{r}{c}"
            body = ""
            if kind == "rings":
                body = "".join(f"<circle cx='{cx}' cy='{cy}' r='{rr}' fill='none' stroke='{INK}' stroke-width='{STROKE * .8}'/>" for rr in range(14, 110, 24))
            elif kind == "diag":
                body = "".join(f"<line x1='{x - 20 + k * 30}' y1='{y}' x2='{x + k * 30 - 240}' y2='{y + cell}' stroke='{INK}' stroke-width='{STROKE * .8}'/>" for k in range(0, 16))
            elif kind == "dots":
                body = "".join(f"<circle cx='{x + 30 + i * 52}' cy='{y + 30 + j * 52}' r='14' fill='#fff' stroke='{INK}' stroke-width='{STROKE * .8}'/>" for i in range(4) for j in range(4))
            elif kind == "check":
                body = "".join(f"<rect x='{x + i * 55}' y='{y + j * 55}' width='55' height='55' fill='none' stroke='{INK}' stroke-width='{STROKE * .8}'/>" for i in range(4) for j in range(4))
            elif kind == "petals":
                body = "".join(f"<ellipse cx='{cx}' cy='{cy - 52}' rx='24' ry='52' fill='#fff' stroke='{INK}' stroke-width='{STROKE * .8}' transform='rotate({k * 45} {cx} {cy})'/>" for k in range(8))
            elif kind == "waves":
                body = "".join(f"<path d='M{x} {y + 28 + k * 36} q27 -30 55 0 t55 0 t55 0 t55 0 t55 0' fill='none' stroke='{INK}' stroke-width='{STROKE * .8}'/>" for k in range(6))
            elif kind == "tri":
                body = "".join(f"<polygon points='{x + i * 73},{y + j * 73 + 73} {x + i * 73 + 36},{y + j * 73} {x + i * 73 + 73},{y + j * 73 + 73}' fill='none' stroke='{INK}' stroke-width='{STROKE * .8}'/>" for i in range(4) for j in range(3))
            elif kind == "cross":
                body = "".join(f"<path d='M{x + 30 + i * 52} {y + 14 + j * 52} v32 M{x + 14 + i * 52} {y + 30 + j * 52} h32' stroke='{INK}' stroke-width='{STROKE * .9}' stroke-linecap='round'/>" for i in range(4) for j in range(4))
            elif kind == "scales":
                body = "".join(f"<circle cx='{x + i * 55 + (27 if j % 2 else 0)}' cy='{y + j * 36}' r='28' fill='#fff' stroke='{INK}' stroke-width='{STROKE * .8}'/>" for j in range(8) for i in range(-1, 5))
            else:
                body = f"<polygon points='{' '.join(f'{px:.0f},{py:.0f}' for px, py in [(cx + (95 if i % 2 == 0 else 38) * math.cos(math.radians(-90 + i * 36)), cy + (95 if i % 2 == 0 else 38) * math.sin(math.radians(-90 + i * 36))) for i in range(10)])}' fill='none' stroke='{INK}' stroke-width='{STROKE * .8}'/>"
            out.append(f"<clipPath id='{clip}'><rect x='{x + 6}' y='{y + 6}' width='{cell - 12}' height='{cell - 12}' rx='14'/></clipPath><g clip-path='url(#{clip})'>{body}</g>"
                       f"<rect x='{x + 6}' y='{y + 6}' width='{cell - 12}' height='{cell - 12}' rx='14' fill='none' stroke='{INK}' stroke-width='{STROKE * 1.4}'/>")
    return _wrap_svg("".join(out))


def wreath(seed: int) -> str:
    rng = random.Random(seed * 23 + 1)
    out = []
    n = 18
    for i in range(n):
        a = i * 2 * math.pi / n + rng.uniform(-.04, .04)
        cx, cy = 500 + 330 * math.cos(a), 500 + 330 * math.sin(a)
        rot = math.degrees(a) + (24 if i % 2 else -24)
        out.append(f"<ellipse cx='{cx:.0f}' cy='{cy:.0f}' rx='34' ry='80' fill='#fff' stroke='{INK}' stroke-width='{STROKE}' transform='rotate({rot:.0f} {cx:.0f} {cy:.0f})'/>"
                   f"<path d='M{cx:.0f} {cy - 60:.0f} V{cy + 60:.0f}' stroke='{INK}' stroke-width='3' transform='rotate({rot:.0f} {cx:.0f} {cy:.0f})'/>")
    for i in range(9):
        a = rng.uniform(0, 6.28)
        cx, cy = 500 + 330 * math.cos(a), 500 + 330 * math.sin(a)
        out.append(f"<circle cx='{cx:.0f}' cy='{cy:.0f}' r='{rng.randint(20, 30)}' fill='#fff' stroke='{INK}' stroke-width='{STROKE}'/>")
    out.append(f"<path d='M500 805 C430 740 380 800 420 850 C450 885 500 840 500 805 C500 840 550 885 580 850 C620 800 570 740 500 805 Z' fill='#fff' stroke='{INK}' stroke-width='{STROKE}'/>")
    return _wrap_svg("".join(out))


def sunburst(seed: int) -> str:
    rng = random.Random(seed * 29 + 9)
    n = rng.choice([16, 20, 24])
    out = []
    for i in range(n):
        a1, a2 = math.radians(i * 360 / n), math.radians((i + .5) * 360 / n)
        a3 = math.radians((i + 1) * 360 / n)
        r1, r2 = 450, 250
        out.append(f"<polygon points='{500 + r2 * math.cos(a1):.0f},{500 + r2 * math.sin(a1):.0f} {500 + r1 * math.cos(a2):.0f},{500 + r1 * math.sin(a2):.0f} {500 + r2 * math.cos(a3):.0f},{500 + r2 * math.sin(a3):.0f}' "
                   f"fill='#fff' stroke='{INK}' stroke-width='{STROKE}' stroke-linejoin='round'/>")
    for rr in (250, 200, 150):
        out.append(f"<circle cx='500' cy='500' r='{rr}' fill='#fff' stroke='{INK}' stroke-width='{STROKE}'/>")
    for i in range(n // 2):
        a = math.radians(i * 720 / n)
        out.append(f"<ellipse cx='{500 + 175 * math.cos(a):.0f}' cy='{500 + 175 * math.sin(a):.0f}' rx='18' ry='34' fill='#fff' stroke='{INK}' stroke-width='{STROKE * .8}' transform='rotate({math.degrees(a) + 90:.0f} {500 + 175 * math.cos(a):.0f} {500 + 175 * math.sin(a):.0f})'/>")
    out.append(f"<circle cx='500' cy='500' r='72' fill='#fff' stroke='{INK}' stroke-width='{STROKE}'/>")
    return _wrap_svg("".join(out))


SPECIALS = [("spirograph", spirograph), ("flower of life", flower_of_life), ("stained glass", stained_glass), ("kaleidoscope", kaleidoscope),
            ("tile sampler", tile_sampler), ("wreath", wreath), ("sunburst", sunburst)]


def page_art(i: int, seed: int, pal: Palette) -> tuple[str, str]:
    """(kind, svg) for coloring page number i: a steady mix of mandalas (40%), patterns (35%) and shape pictures (25%)."""
    slot = i % 20
    if slot in (6, 14):   # two of the eight mandala slots become one of the other radial and geometric styles, walking through all of them
        n = (i // 20) * 2 + (0 if slot == 6 else 1)
        order = sorted(range(len(SPECIALS)), key=lambda k: random.Random(f"{seed}-sp-{k}").random())
        name, fn = SPECIALS[order[n % len(SPECIALS)]]
        return "special", fn(seed * 101 + i)
    if slot in (0, 2, 4, 8, 11, 17):
        return "mandala", mandala(seed * 101 + i)
    if slot in (1, 3, 5, 9, 12, 15, 18):
        slots = (1, 3, 5, 9, 12, 15, 18)
        n = (i // 20) * len(slots) + slots.index(slot)   # which pattern page this is, so a book walks through a seeded shuffle of every pattern before repeating
        order = sorted(PATTERN_KINDS, key=lambda k: random.Random(f"{seed}-{k}").random())
        return "pattern", pattern_page(i, seed * 101 + i, pal, order[n % len(order)])
    return "motif", motif_page(i, seed * 101 + i, pal)
