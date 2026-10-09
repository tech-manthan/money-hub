"""Seamless repeat patterns as SVG. Every pattern is drawn on a 1000 x 1000 tile whose edges wrap: a shape that crosses an edge
is drawn again on the opposite side, and grid patterns use whole numbers of cells. A paper is the tile repeated k x k times, so it
also tiles with no visible seam when a buyer repeats it."""
from __future__ import annotations

import math
import random

from .design import Palette, contrast

T = 1000
KINDS = ["dots", "gingham", "stripes", "waves", "scallops", "arches", "terrazzo", "sparkles", "leaves", "diamonds", "daisies", "checks"]


def _wrap(shape, cx: float, cy: float, r: float) -> str:
    """shape(x, y) -> svg, drawn at every wrapped position whose reach (radius r) touches the tile."""
    out = []
    for dx in (-T, 0, T):
        for dy in (-T, 0, T):
            if cx + dx + r > 0 and cx + dx - r < T and cy + dy + r > 0 and cy + dy - r < T:
                out.append(shape(cx + dx, cy + dy))
    return "".join(out)


def colours(pal: Palette, index: int) -> tuple[str, list[str]]:
    """(background, shape colours) for paper number `index`: the palette's own colours, kept apart enough to read."""
    pool = [pal.paper, pal.soft, pal.accent, pal.accent2, pal.line, pal.ink]
    bgs = [pal.paper, pal.soft, pal.accent, pal.accent2]
    bg = bgs[index % len(bgs)]
    fg = [c for c in pool if c != bg and contrast(bg, c) >= 1.35][:4]
    return bg, fg or [pal.ink if contrast(bg, pal.ink) > 1.5 else pal.paper]


def pattern_tile(kind: str, pal: Palette, seed: int, index: int = 0) -> str:
    """The inner SVG (no <svg> wrapper) of one seamless 1000 x 1000 tile."""
    rng = random.Random(seed * 997 + index)
    bg, fg = colours(pal, index)
    c = lambda i: fg[i % len(fg)]   # noqa: E731
    p: list[str] = [f"<rect width='{T}' height='{T}' fill='{bg}'/>"]
    n = rng.choice([4, 6])   # even: staggered rows must pair up across the wrap
    cell = T / n
    if kind == "dots":
        r = cell * rng.uniform(.16, .24)
        for row in range(n):
            for col in range(n):
                x = (col + (.5 if row % 2 else 0) + .5) * cell % T
                p.append(_wrap(lambda a, b, row=row, col=col: f"<circle cx='{a:.1f}' cy='{b:.1f}' r='{r:.1f}' fill='{c(row + col)}'/>", x, (row + .5) * cell, r))
    elif kind == "gingham":
        m = rng.choice([4, 6, 8])   # even, so the stripe pattern continues across the edge
        w = T / m
        p.append(f"<g opacity='.55' fill='{c(0)}'>" + "".join(f"<rect x='{i * w * 2:.1f}' y='0' width='{w:.1f}' height='{T}'/>" for i in range(m // 2 + 1) if i * w * 2 < T) + "</g>")
        p.append(f"<g opacity='.55' fill='{c(0)}'>" + "".join(f"<rect x='0' y='{i * w * 2:.1f}' width='{T}' height='{w:.1f}'/>" for i in range(m // 2 + 1) if i * w * 2 < T) + "</g>")
    elif kind == "stripes":
        m = rng.choice([6, 8, 10])
        w = T / m
        for i in range(0, m, 2):
            p.append(f"<rect x='{i * w:.1f}' y='0' width='{w:.1f}' height='{T}' fill='{c(i // 2)}'/>")
    elif kind == "waves":
        rows, k, amp = rng.choice([5, 6, 8]), rng.choice([2, 3, 4]), rng.uniform(.12, .22)
        h = T / rows
        for i in range(rows):
            pts = " ".join(f"{x:.1f},{(i + .5) * h + amp * h * math.sin(2 * math.pi * k * x / T):.1f}" for x in range(0, T + 1, 10))
            p.append(f"<polyline points='{pts}' fill='none' stroke='{c(i)}' stroke-width='{h * .22:.1f}' stroke-linecap='round'/>")
    elif kind == "scallops":
        rows = rng.choice([4, 6]) * 2 // 2 * 2
        cols = rng.choice([4, 5, 6])
        w, h = T / cols, T / rows
        r = w / 2
        for row in range(rows):
            for col in range(cols + 1):
                x = col * w + (w / 2 if row % 2 else 0)
                y = row * h
                p.append(_wrap(lambda a, b, row=row, col=col: f"<circle cx='{a:.1f}' cy='{b:.1f}' r='{r:.1f}' fill='{c(row + col)}' stroke='{bg}' stroke-width='6'/>", x % T, y, r))
    elif kind == "arches":
        cols = rng.choice([3, 4, 5])
        rows = cols * 2 // 2 * 2 if cols % 2 == 0 else cols + 1
        w, h = T / cols, T / rows
        for row in range(rows):
            for col in range(cols):
                x = col * w + (w / 2 if row % 2 else 0)
                y = row * h
                def arch(a, b, row=row, col=col):
                    r = w * .36
                    return f"<path d='M{a - r:.1f} {b + h * .42:.1f} V{b:.1f} A{r:.1f} {r:.1f} 0 0 1 {a + r:.1f} {b:.1f} V{b + h * .42:.1f} Z' fill='{c(row + col)}'/>"
                p.append(_wrap(arch, x % T, y + h * .25, w * .5 + h * .4))
    elif kind == "terrazzo":
        for _ in range(70):
            x, y, r = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(14, 40)
            pts = [(r * rng.uniform(.6, 1.2) * math.cos(a), r * rng.uniform(.6, 1.2) * math.sin(a)) for a in [i * 2 * math.pi / 6 + rng.uniform(-.3, .3) for i in range(6)]]
            col = c(rng.randrange(len(fg)))
            p.append(_wrap(lambda a, b, pts=pts, col=col: "<polygon points='" + " ".join(f"{a + u:.1f},{b + v:.1f}" for u, v in pts) + f"' fill='{col}'/>", x, y, r * 1.3))
    elif kind == "sparkles":
        for _ in range(26):
            x, y, s = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(22, 60)
            col = c(rng.randrange(len(fg)))
            p.append(_wrap(lambda a, b, s=s, col=col: f"<path d='M{a:.1f} {b - s:.1f} Q{a:.1f} {b:.1f} {a + s:.1f} {b:.1f} Q{a:.1f} {b:.1f} {a:.1f} {b + s:.1f} Q{a:.1f} {b:.1f} {a - s:.1f} {b:.1f} Q{a:.1f} {b:.1f} {a:.1f} {b - s:.1f}Z' fill='{col}'/>", x, y, s))
    elif kind == "leaves":
        for _ in range(34):
            x, y, s, ang = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(34, 70), rng.uniform(0, 180)
            col = c(rng.randrange(len(fg)))
            p.append(_wrap(lambda a, b, s=s, ang=ang, col=col: f"<ellipse cx='{a:.1f}' cy='{b:.1f}' rx='{s * .38:.1f}' ry='{s:.1f}' fill='{col}' transform='rotate({ang:.0f} {a:.1f} {b:.1f})'/>", x, y, s))
    elif kind == "diamonds":
        m = rng.choice([4, 6])
        w = T / m
        for row in range(m * 2):
            for col in range(m):
                x = (col + (.5 if row % 2 else 0)) * w
                y = row * w / 2
                p.append(_wrap(lambda a, b, row=row, col=col: f"<polygon points='{a:.1f},{b - w / 2:.1f} {a + w / 2:.1f},{b:.1f} {a:.1f},{b + w / 2:.1f} {a - w / 2:.1f},{b:.1f}' fill='{c(row + col)}' stroke='{bg}' stroke-width='5'/>", x % T, y, w / 2))
    elif kind == "daisies":
        for _ in range(14):
            x, y, s = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(46, 80)
            petal, centre = c(rng.randrange(len(fg))), c(rng.randrange(len(fg)) + 1)

            def flower(a, b, s=s, petal=petal, centre=centre):
                ps = "".join(f"<ellipse cx='{a + s * .62 * math.cos(math.radians(k * 45)):.1f}' cy='{b + s * .62 * math.sin(math.radians(k * 45)):.1f}' rx='{s * .36:.1f}' ry='{s * .17:.1f}' "
                              f"fill='{petal}' transform='rotate({k * 45} {a + s * .62 * math.cos(math.radians(k * 45)):.1f} {b + s * .62 * math.sin(math.radians(k * 45)):.1f})'/>" for k in range(8))
                return ps + f"<circle cx='{a:.1f}' cy='{b:.1f}' r='{s * .24:.1f}' fill='{centre}'/>"
            p.append(_wrap(flower, x, y, s))
    else:   # checks
        m = rng.choice([6, 8, 10])
        w = T / m
        for row in range(m):
            for col in range(m):
                if (row + col) % 2 == 0:
                    p.append(f"<rect x='{col * w:.1f}' y='{row * w:.1f}' width='{w:.1f}' height='{w:.1f}' fill='{c(0)}'/>")
    return "".join(p)


def paper_svg(kind: str, pal: Palette, seed: int, index: int = 0, repeat: int = 2) -> str:
    """A full paper: the tile repeated repeat x repeat times, as a square SVG (viewBox 0 0 1000 1000)."""
    tile = pattern_tile(kind, pal, seed, index)
    k = max(1, repeat)
    s = 1 / k
    body = "".join(f"<g transform='translate({i * T * s:.4f} {j * T * s:.4f}) scale({s:.5f})'>{tile}</g>" for i in range(k) for j in range(k))
    return f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {T} {T}' preserveAspectRatio='none'>{body}</svg>"


def seam_excess(img) -> float:
    """How much brighter the join between opposite edges is than the join between ordinary neighbouring pixels (0-255 scale, both axes).
    About 0 for a seamless tile; large when a shape is cut at the edge."""
    import numpy as np
    a = np.asarray(img.convert("L").resize((600, 600)), dtype=float)
    out = []
    for arr in (a, a.T):
        inner = np.abs(np.diff(arr, axis=1)).mean()
        seam = np.abs(arr[:, 0] - arr[:, -1]).mean()
        out.append(seam - inner)
    return float(max(out))
