"""Seamless repeat patterns as SVG. Every pattern is drawn on a 1000 x 1000 tile whose edges wrap: a shape that crosses an edge
is drawn again on the opposite side, and grid patterns use whole numbers of cells. A paper is the tile repeated k x k times, so it
also tiles with no visible seam when a buyer repeats it."""
from __future__ import annotations

import math
import random

from .design import Palette, contrast

T = 1000
KINDS = ["dots", "gingham", "stripes", "waves", "scallops", "arches", "terrazzo", "sparkles", "leaves", "diamonds", "daisies", "checks",
         "plaid", "chevron", "hearts", "stars", "ditsy", "paisley", "hexagons", "rainbows", "celestial", "blobs", "memphis", "zigzag",
         "houndstooth", "argyle", "leopard", "quatrefoil", "ogee", "snowflakes", "cherries", "lemons", "tropical", "triangles", "brushstrokes", "confetti"]
HARD_EDGE = ("stripes", "gingham", "checks", "plaid", "chevron", "zigzag", "houndstooth", "argyle", "triangles")   # straight bands that meet the tile border by design


def _star(a: float, b: float, r: float, inner: float = .45, n: int = 5, rot: float = -90) -> str:
    return " ".join(f"{a + (r if i % 2 == 0 else r * inner) * math.cos(math.radians(rot + i * 180 / n)):.1f},{b + (r if i % 2 == 0 else r * inner) * math.sin(math.radians(rot + i * 180 / n)):.1f}" for i in range(n * 2))


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
    elif kind == "plaid":   # tartan-style: wide translucent bands one way, another colour the other way, thin lines between
        m = rng.choice([4, 6, 8])
        w = T / m
        p.append(f"<g fill='{c(0)}' opacity='.5'>" + "".join(f"<rect x='{i * w:.1f}' y='0' width='{w:.1f}' height='{T}'/>" for i in range(0, m, 2)) + "</g>")
        p.append(f"<g fill='{c(1)}' opacity='.5'>" + "".join(f"<rect x='0' y='{i * w:.1f}' width='{T}' height='{w:.1f}'/>" for i in range(0, m, 2)) + "</g>")
        p.append(f"<g stroke='{c(2)}' stroke-width='6' opacity='.85'>" + "".join(f"<line x1='{(i + .5) * w:.1f}' y1='0' x2='{(i + .5) * w:.1f}' y2='{T}'/><line x1='0' y1='{(i + .5) * w:.1f}' x2='{T}' y2='{(i + .5) * w:.1f}'/>" for i in range(m)) + "</g>")
    elif kind in ("chevron", "zigzag"):
        rows, k = rng.choice([6, 8, 10]), rng.choice([4, 6, 8])   # k even: the zig-zag meets itself across the wrap
        h, amp = T / rows, T / rows * (.42 if kind == "chevron" else .22)
        for i in range(-1, rows + 1):
            pts = " ".join(f"{x * T / k:.1f},{i * h + (amp if x % 2 else -amp) + h / 2:.1f}" for x in range(k + 1))
            if kind == "chevron":
                p.append(f"<polyline points='{pts}' fill='none' stroke='{c(i)}' stroke-width='{h * .42:.1f}' stroke-linejoin='miter'/>")
            else:
                p.append(f"<polyline points='{pts}' fill='none' stroke='{c(i)}' stroke-width='{h * .16:.1f}' stroke-linecap='round' stroke-linejoin='round'/>")
    elif kind == "hearts":
        for _ in range(24):
            x, y, s, ang = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(34, 62), rng.uniform(-25, 25)
            col = c(rng.randrange(len(fg)))
            p.append(_wrap(lambda a, b, s=s, ang=ang, col=col: (f"<path d='M{a:.1f} {b + .55 * s:.1f} C{a - 1.15 * s:.1f} {b - .25 * s:.1f} {a - .55 * s:.1f} {b - .95 * s:.1f} {a:.1f} {b - .4 * s:.1f} "
                                                                f"C{a + .55 * s:.1f} {b - .95 * s:.1f} {a + 1.15 * s:.1f} {b - .25 * s:.1f} {a:.1f} {b + .55 * s:.1f}Z' fill='{col}' transform='rotate({ang:.0f} {a:.1f} {b:.1f})'/>"), x, y, s * 1.3))
    elif kind == "stars":
        for _ in range(22):
            x, y, s, ang = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(34, 66), rng.uniform(-90, -60)
            col = c(rng.randrange(len(fg)))
            p.append(_wrap(lambda a, b, s=s, ang=ang, col=col: f"<polygon points='{_star(a, b, s, .46, 5, ang)}' fill='{col}'/>", x, y, s))
    elif kind == "ditsy":   # tiny scattered five-petal flowers with leaves
        for _ in range(46):
            x, y, s = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(20, 34)
            petal, centre, leaf = c(rng.randrange(len(fg))), c(rng.randrange(len(fg)) + 1), c(rng.randrange(len(fg)) + 2)

            def ditsy(a, b, s=s, petal=petal, centre=centre, leaf=leaf):
                ls = "".join(f"<ellipse cx='{a + s * 1.25 * math.cos(math.radians(k)):.1f}' cy='{b + s * 1.25 * math.sin(math.radians(k)):.1f}' rx='{s * .55:.1f}' ry='{s * .22:.1f}' fill='{leaf}' transform='rotate({k} {a + s * 1.25 * math.cos(math.radians(k)):.1f} {b + s * 1.25 * math.sin(math.radians(k)):.1f})'/>" for k in (20, 160))
                ps = "".join(f"<circle cx='{a + s * .62 * math.cos(math.radians(k * 72 - 90)):.1f}' cy='{b + s * .62 * math.sin(math.radians(k * 72 - 90)):.1f}' r='{s * .42:.1f}' fill='{petal}'/>" for k in range(5))
                return ls + ps + f"<circle cx='{a:.1f}' cy='{b:.1f}' r='{s * .26:.1f}' fill='{centre}'/>"
            p.append(_wrap(ditsy, x, y, s * 2))
    elif kind == "paisley":
        for _ in range(16):
            x, y, s, ang = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(46, 80), rng.uniform(0, 360)
            c1, c2 = c(rng.randrange(len(fg))), c(rng.randrange(len(fg)) + 1)

            def paisley(a, b, s=s, ang=ang, c1=c1, c2=c2):
                body = f"M{a:.1f} {b - s:.1f} C{a + s * .95:.1f} {b - s * .6:.1f} {a + s * .8:.1f} {b + s * .75:.1f} {a - s * .2:.1f} {b + s:.1f} C{a - s * .7:.1f} {b + s * 1.1:.1f} {a - s * .3:.1f} {b + s * .6:.1f} {a - s * .1:.1f} {b + s * .5:.1f} C{a - s * .6:.1f} {b + s * .1:.1f} {a - s * .55:.1f} {b - s * .6:.1f} {a:.1f} {b - s:.1f}Z"
                return (f"<g transform='rotate({ang:.0f} {a:.1f} {b:.1f})'><path d='{body}' fill='{c1}'/><ellipse cx='{a + s * .18:.1f}' cy='{b - s * .1:.1f}' rx='{s * .3:.1f}' ry='{s * .5:.1f}' fill='{c2}'/>"
                        f"<circle cx='{a + s * .18:.1f}' cy='{b - s * .1:.1f}' r='{s * .12:.1f}' fill='{c1}'/></g>")
            p.append(_wrap(paisley, x, y, s * 1.3))
    elif kind == "hexagons":   # honeycomb: whole numbers of cells in both directions, so it wraps
        m = rng.choice([4, 6])
        w, rowh = T / m, T / m
        ry = rowh * 2 / 3
        for row in range(m):
            for col in range(m):
                x = ((col + .5 + (.5 if row % 2 else 0)) * w) % T
                y = row * rowh + rowh / 2
                pts = [(0, -ry), (w / 2, -ry / 2), (w / 2, ry / 2), (0, ry), (-w / 2, ry / 2), (-w / 2, -ry / 2)]
                p.append(_wrap(lambda a, b, pts=pts, row=row, col=col: "<polygon points='" + " ".join(f"{a + u:.1f},{b + v:.1f}" for u, v in pts) + f"' fill='{c(row + col)}' stroke='{bg}' stroke-width='6'/>", x, y, w / 2 + 4))
    elif kind == "rainbows":
        for _ in range(14):
            x, y, r = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(52, 84)
            order = rng.randrange(len(fg))

            def rainbow(a, b, r=r, order=order):
                return "".join(f"<path d='M{a - r * (1 - k * .27):.1f} {b + r * .45:.1f} A{r * (1 - k * .27):.1f} {r * (1 - k * .27):.1f} 0 0 1 {a + r * (1 - k * .27):.1f} {b + r * .45:.1f}' fill='none' stroke='{c(order + k)}' stroke-width='{r * .2:.1f}' stroke-linecap='round'/>" for k in range(3))
            p.append(_wrap(rainbow, x, y, r * 1.2))
    elif kind == "celestial":
        for _ in range(30):
            x, y, s, which = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(22, 50), rng.randrange(3)
            col = c(rng.randrange(len(fg)))
            ang = rng.uniform(-40, 40)
            if which == 0:   # crescent moon
                shape = lambda a, b, s=s, col=col, ang=ang: f"<path d='M{a:.1f} {b - s:.1f} A{s:.1f} {s:.1f} 0 1 0 {a:.1f} {b + s:.1f} A{s * .72:.1f} {s * .72:.1f} 0 1 1 {a:.1f} {b - s:.1f}Z' fill='{col}' transform='rotate({ang:.0f} {a:.1f} {b:.1f})'/>"   # noqa: E731
            elif which == 1:   # four-point star
                shape = lambda a, b, s=s, col=col: f"<polygon points='{_star(a, b, s, .3, 4)}' fill='{col}'/>"   # noqa: E731
            else:
                shape = lambda a, b, s=s, col=col: f"<circle cx='{a:.1f}' cy='{b:.1f}' r='{s * .3:.1f}' fill='{col}'/>"   # noqa: E731
            p.append(_wrap(shape, x, y, s * 1.1))
    elif kind == "blobs":   # matisse-style cut-out shapes
        for _ in range(16):
            x, y, s = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(46, 96)
            col = c(rng.randrange(len(fg)))
            radii = [rng.uniform(.68, 1.18) for _ in range(8)]
            ang0 = rng.uniform(0, 6.28)

            def blob(a, b, s=s, col=col, radii=radii, ang0=ang0):
                pts = [(a + s * r * math.cos(ang0 + i * math.pi / 4), b + s * r * math.sin(ang0 + i * math.pi / 4)) for i, r in enumerate(radii)]
                mid = lambda q, r2: ((q[0] + r2[0]) / 2, (q[1] + r2[1]) / 2)   # noqa: E731
                m0 = mid(pts[0], pts[1])
                d = f"M{m0[0]:.1f} {m0[1]:.1f}" + "".join(f" Q{pts[(i + 1) % 8][0]:.1f} {pts[(i + 1) % 8][1]:.1f} {mid(pts[(i + 1) % 8], pts[(i + 2) % 8])[0]:.1f} {mid(pts[(i + 1) % 8], pts[(i + 2) % 8])[1]:.1f}" for i in range(8))
                return f"<path d='{d}Z' fill='{col}'/>"
            p.append(_wrap(blob, x, y, s * 1.3))
    elif kind == "memphis":   # 80s confetti: triangles, squiggles, rings and dots
        for _ in range(44):
            x, y, s, which = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(18, 40), rng.randrange(4)
            col = c(rng.randrange(len(fg)))
            ang = rng.uniform(0, 360)
            if which == 0:
                shape = lambda a, b, s=s, col=col, ang=ang: f"<polygon points='{a:.1f},{b - s:.1f} {a + s:.1f},{b + s * .8:.1f} {a - s:.1f},{b + s * .8:.1f}' fill='{col}' transform='rotate({ang:.0f} {a:.1f} {b:.1f})'/>"   # noqa: E731
            elif which == 1:
                shape = lambda a, b, s=s, col=col, ang=ang: (f"<polyline points='" + " ".join(f"{a - s * 1.5 + k * s * .5:.1f},{b + (s * .35 if k % 2 else -s * .35):.1f}" for k in range(7))   # noqa: E731
                                                              + f"' fill='none' stroke='{col}' stroke-width='{s * .22:.1f}' stroke-linecap='round' stroke-linejoin='round' transform='rotate({ang:.0f} {a:.1f} {b:.1f})'/>")
            elif which == 2:
                shape = lambda a, b, s=s, col=col: f"<circle cx='{a:.1f}' cy='{b:.1f}' r='{s * .7:.1f}' fill='none' stroke='{col}' stroke-width='{s * .26:.1f}'/>"   # noqa: E731
            else:
                shape = lambda a, b, s=s, col=col: f"<circle cx='{a:.1f}' cy='{b:.1f}' r='{s * .38:.1f}' fill='{col}'/>"   # noqa: E731
            p.append(_wrap(shape, x, y, s * 1.7))
    elif kind == "houndstooth":
        m = rng.choice([6, 8])
        w = T / m
        for row in range(m):
            for col in range(m):
                x, y = col * w, row * w
                if (row + col) % 2 == 0:
                    p.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{w:.1f}' height='{w:.1f}' fill='{c(0)}'/>")
                    p.append(f"<polygon points='{x + w:.1f},{y:.1f} {x + w * 1.5:.1f},{y + w * .5:.1f} {x + w:.1f},{y + w * .5:.1f}' fill='{c(0)}'/>")
                else:
                    p.append(f"<polygon points='{x:.1f},{y + w:.1f} {x + w * .5:.1f},{y + w:.1f} {x:.1f},{y + w * 1.5:.1f}' fill='{c(0)}'/>")
        p.append(f"<rect x='{T}' y='0' width='{w * 2}' height='{T}' fill='{bg}'/><rect x='0' y='{T}' width='{T}' height='{w * 2}' fill='{bg}'/>")
    elif kind == "argyle":
        m = rng.choice([4, 6])
        w = T / m
        for row in range(m * 2):
            for col in range(m):
                x, y = (col + (.5 if row % 2 else 0)) * w, row * w / 2
                p.append(_wrap(lambda a, b, row=row, col=col: f"<polygon points='{a:.1f},{b - w / 2:.1f} {a + w / 2:.1f},{b:.1f} {a:.1f},{b + w / 2:.1f} {a - w / 2:.1f},{b:.1f}' fill='{c(0) if (row // 2 + col) % 2 == 0 else c(1)}'/>", x % T, y, w / 2))
        p.append(f"<g stroke='{c(2)}' stroke-width='5' opacity='.9'>" + "".join(f"<line x1='{i * w:.1f}' y1='0' x2='{i * w + T:.1f}' y2='{T}'/><line x1='{i * w:.1f}' y1='{T}' x2='{i * w + T:.1f}' y2='0'/>" for i in range(-m, m + 1)) + "</g>")
    elif kind == "leopard":
        for _ in range(22):
            x, y, s, ang = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(30, 52), rng.uniform(0, 180)
            col = c(rng.randrange(len(fg)))
            ring = c(rng.randrange(len(fg)) + 1)

            def spot(a, b, s=s, ang=ang, col=col, ring=ring):
                return (f"<g transform='rotate({ang:.0f} {a:.1f} {b:.1f})'><path d='M{a - s:.1f} {b:.1f} C{a - s:.1f} {b - s * 1.1:.1f} {a + s * .6:.1f} {b - s * 1.2:.1f} {a + s:.1f} {b - s * .1:.1f} "
                        f"C{a + s * .9:.1f} {b + s * .8:.1f} {a - s * .3:.1f} {b + s * 1.1:.1f} {a - s:.1f} {b:.1f}Z' fill='none' stroke='{ring}' stroke-width='{s * .3:.1f}' stroke-linecap='round'/>"
                        f"<ellipse cx='{a:.1f}' cy='{b:.1f}' rx='{s * .22:.1f}' ry='{s * .16:.1f}' fill='{col}'/></g>")
            p.append(_wrap(spot, x, y, s * 1.3))
    elif kind == "quatrefoil":
        m = rng.choice([3, 4, 5])
        w = T / m
        r = w * .24
        for row in range(m):
            for col in range(m):
                cx, cy = (col + .5) * w, (row + .5) * w
                col_ = c((row + col) % 2)
                for dx, dy in ((-r, 0), (r, 0), (0, -r), (0, r)):
                    p.append(f"<circle cx='{cx + dx:.1f}' cy='{cy + dy:.1f}' r='{r * 1.05:.1f}' fill='{col_}'/>")
                p.append(f"<rect x='{cx - r:.1f}' y='{cy - r:.1f}' width='{2 * r:.1f}' height='{2 * r:.1f}' fill='{col_}'/>")
    elif kind == "ogee":
        cols = rng.choice([4, 5, 6])
        rows = rng.choice([4, 6]) * 2
        w, h = T / cols, T / rows
        for row in range(rows):
            for col in range(cols + 1):
                x, y = col * w + (w / 2 if row % 2 else 0), row * h
                p.append(_wrap(lambda a, b: f"<circle cx='{a:.1f}' cy='{b:.1f}' r='{w / 2:.1f}' fill='none' stroke='{c(0)}' stroke-width='7'/><circle cx='{a:.1f}' cy='{b:.1f}' r='{w / 2 - 14:.1f}' fill='none' stroke='{c(1)}' stroke-width='4'/>", x % T, y, w / 2))
    elif kind == "snowflakes":
        for _ in range(20):
            x, y, s = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(32, 64)
            col = c(rng.randrange(len(fg)))

            def flake(a, b, s=s, col=col):
                arms = "".join(f"<g transform='rotate({k * 60} {a:.1f} {b:.1f})'><line x1='{a:.1f}' y1='{b:.1f}' x2='{a:.1f}' y2='{b - s:.1f}'/><polyline points='{a - s * .3:.1f},{b - s * .7:.1f} {a:.1f},{b - s * .45:.1f} {a + s * .3:.1f},{b - s * .7:.1f}'/></g>" for k in range(6))
                return f"<g stroke='{col}' stroke-width='{s * .12:.1f}' stroke-linecap='round' fill='none'>{arms}</g>"
            p.append(_wrap(flake, x, y, s))
    elif kind == "cherries":
        for _ in range(14):
            x, y, s, ang = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(34, 56), rng.uniform(-25, 25)
            col, stem = c(rng.randrange(len(fg))), c(rng.randrange(len(fg)) + 1)

            def cherry(a, b, s=s, ang=ang, col=col, stem=stem):
                return (f"<g transform='rotate({ang:.0f} {a:.1f} {b:.1f})'><path d='M{a - s * .8:.1f} {b + s * .5:.1f} Q{a - s * .4:.1f} {b - s * 1.4:.1f} {a + s * .2:.1f} {b - s * 1.6:.1f} "
                        f"M{a + s * .8:.1f} {b + s * .6:.1f} Q{a + s * .5:.1f} {b - s:.1f} {a + s * .2:.1f} {b - s * 1.6:.1f}' fill='none' stroke='{stem}' stroke-width='{s * .12:.1f}' stroke-linecap='round'/>"
                        f"<circle cx='{a - s * .8:.1f}' cy='{b + s * .55:.1f}' r='{s * .55:.1f}' fill='{col}'/><circle cx='{a + s * .8:.1f}' cy='{b + s * .65:.1f}' r='{s * .55:.1f}' fill='{col}'/></g>")
            p.append(_wrap(cherry, x, y, s * 2))
    elif kind == "lemons":
        for _ in range(15):
            x, y, s, ang = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(40, 66), rng.uniform(0, 180)
            col, leaf = c(rng.randrange(len(fg))), c(rng.randrange(len(fg)) + 1)

            def lemon(a, b, s=s, ang=ang, col=col, leaf=leaf):
                return (f"<g transform='rotate({ang:.0f} {a:.1f} {b:.1f})'><ellipse cx='{a:.1f}' cy='{b:.1f}' rx='{s:.1f}' ry='{s * .7:.1f}' fill='{col}'/>"
                        f"<polygon points='{a - s * 1.15:.1f},{b:.1f} {a - s * .85:.1f},{b - s * .12:.1f} {a - s * .85:.1f},{b + s * .12:.1f}' fill='{col}'/>"
                        f"<ellipse cx='{a + s * .5:.1f}' cy='{b - s * .85:.1f}' rx='{s * .35:.1f}' ry='{s * .16:.1f}' fill='{leaf}' transform='rotate(-30 {a + s * .5:.1f} {b - s * .85:.1f})'/></g>")
            p.append(_wrap(lemon, x, y, s * 1.5))
    elif kind == "tropical":
        for _ in range(12):
            x, y, s, ang = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(70, 120), rng.uniform(0, 360)
            col, vein = c(rng.randrange(len(fg))), c(rng.randrange(len(fg)) + 1)

            def leaf(a, b, s=s, ang=ang, col=col, vein=vein):
                return (f"<g transform='rotate({ang:.0f} {a:.1f} {b:.1f})'><path d='M{a:.1f} {b + s:.1f} C{a - s * .9:.1f} {b + s * .3:.1f} {a - s * .8:.1f} {b - s * .7:.1f} {a:.1f} {b - s:.1f} "
                        f"C{a + s * .8:.1f} {b - s * .7:.1f} {a + s * .9:.1f} {b + s * .3:.1f} {a:.1f} {b + s:.1f}Z' fill='{col}'/><path d='M{a:.1f} {b + s * .9:.1f} V{b - s * .8:.1f}' stroke='{vein}' stroke-width='{s * .06:.1f}'/></g>")
            p.append(_wrap(leaf, x, y, s * 1.1))
    elif kind == "triangles":
        m = rng.choice([4, 6])
        w = T / m
        h = T / m
        for row in range(m):
            for col in range(m):
                x, y = col * w, row * h
                p.append(f"<polygon points='{x:.1f},{y:.1f} {x + w:.1f},{y:.1f} {x:.1f},{y + h:.1f}' fill='{c(rng.randrange(len(fg) + 1))}'/>")
                p.append(f"<polygon points='{x + w:.1f},{y:.1f} {x + w:.1f},{y + h:.1f} {x:.1f},{y + h:.1f}' fill='{c(rng.randrange(len(fg) + 2))}'/>")
    elif kind == "brushstrokes":
        for _ in range(26):
            x, y, ln, ang = rng.uniform(0, T), rng.uniform(0, T), rng.uniform(80, 170), rng.uniform(-35, 35)
            col = c(rng.randrange(len(fg)))
            wd = rng.uniform(14, 26)
            p.append(_wrap(lambda a, b, ln=ln, ang=ang, col=col, wd=wd: f"<path d='M{a - ln / 2:.1f} {b:.1f} q{ln / 2:.1f} {-ln * .18:.1f} {ln:.1f} 0' fill='none' stroke='{col}' stroke-width='{wd:.1f}' stroke-linecap='round' opacity='.9' transform='rotate({ang:.0f} {a:.1f} {b:.1f})'/>", x, y, ln))
    elif kind == "confetti":
        for _ in range(60):
            x, y, r = rng.uniform(0, T), rng.uniform(0, T), rng.choice([8, 12, 18, 26])
            col = c(rng.randrange(len(fg)))
            p.append(_wrap(lambda a, b, r=r, col=col: f"<circle cx='{a:.1f}' cy='{b:.1f}' r='{r}' fill='{col}'/>", x, y, r))
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
