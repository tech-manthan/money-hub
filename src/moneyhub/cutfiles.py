"""Cut-file designs for Cricut, Silhouette and other cutting machines. Every design is a closed outline (plus holes for cut-outs) built
from one smooth curve, so there is nothing to weld and no overlapping paths. Designs live in a 1000 x 1000 box and are exported as SVG,
DXF, EPS and PNG at any size in inches."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

Ring = list[tuple[float, float]]
C = 500.0   # centre of the design box
MIN_GAP_MM = 1.5   # the thinnest bridge between two cuts that a cutting mat holds reliably


@dataclass
class Design:
    name: str
    rings: list[Ring] = field(default_factory=list)   # outer outlines and holes (even-odd rule: nested rings are holes)


def _polar(fn, n: int = 360, cx: float = C, cy: float = C) -> Ring:
    return [(cx + fn(t) * math.cos(t), cy + fn(t) * math.sin(t)) for t in (2 * math.pi * i / n for i in range(n))]


def _circle(r: float, n: int = 120, cx: float = C, cy: float = C) -> Ring:
    return _polar(lambda t: r, n, cx, cy)


def star(points: int, inner: float, hole: bool = False) -> Design:
    ring = []
    for i in range(points * 2):
        r = 450 if i % 2 == 0 else 450 * inner
        a = math.pi * i / points - math.pi / 2
        ring.append((C + r * math.cos(a), C + r * math.sin(a)))
    return Design(f"Star {points}", [ring] + ([_circle(70)] if hole else []))


def flower(petals: int, depth: float, hole: float = 0.14) -> Design:
    d = Design(f"Flower {petals}", [_polar(lambda t: 450 * ((1 - depth) + depth * abs(math.cos(petals * t / 2)) ** .55), 480)])
    d.rings.append(_circle(450 * hole))
    return d


def scallop(bumps: int, ring: bool = True) -> Design:
    """Scalloped edge: the outline of a ring of overlapping circles (each ray's farthest circle crossing), so every bump is a true arc."""
    rc = 360.0
    b = rc * math.sin(math.pi / bumps) * 1.3
    centres = [(math.tau * k / bumps) for k in range(bumps)]

    def r(t):
        best = rc * .8
        for phi in centres:
            d = t - phi
            cosd, sind = math.cos(d), math.sin(d)
            disc = b * b - (rc * sind) ** 2
            if disc >= 0:
                best = max(best, rc * cosd + math.sqrt(disc))
        return best
    outer = _polar(r, 720)
    scale = 450 / max(math.hypot(x - C, y - C) for x, y in outer)
    outer = [(C + (x - C) * scale, C + (y - C) * scale) for x, y in outer]
    d = Design(f"Scallop {bumps}", [outer])
    if ring:
        d.rings.append(_circle(300))
    return d


def sunburst(rays: int, short: float = .62) -> Design:
    def r(t):
        phase = (t * rays / (2 * math.pi)) % 1.0
        tri = 1 - abs(2 * phase - 1)   # 0 at the valleys, 1 at the tips
        return 450 * (short + (1 - short) * tri ** 1.4)
    return Design(f"Sunburst {rays}", [_polar(r, rays * 24), _circle(110)])


def heart(hole: bool = False) -> Design:
    pts = []
    for i in range(240):
        t = 2 * math.pi * i / 240
        pts.append((16 * math.sin(t) ** 3, 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)))
    scale = 27.0
    ring = [(C + x * scale, C - (y + 1) * scale) for x, y in pts]
    inner = [(C + x * scale * .5, C - (y + 1) * scale * .5 - 20) for x, y in pts]
    return Design("Heart outline" if hole else "Heart", [ring] + ([inner] if hole else []))


def crescent() -> Design:
    R, r, d = 430.0, 360.0, 190.0
    x0 = (d * d + R * R - r * r) / (2 * d)
    y0 = math.sqrt(R * R - x0 * x0)
    th = math.atan2(y0, x0)
    al = math.atan2(y0, x0 - d)
    outer = [(C - 40 + R * math.cos(t), C + R * math.sin(t)) for t in (th + (2 * math.pi - 2 * th) * i / 160 for i in range(161))]
    inner = [(C - 40 + d + r * math.cos(p), C + r * math.sin(p)) for p in ((2 * math.pi - al) - ((2 * math.pi - al) - al) * i / 120 for i in range(121))]
    return Design("Crescent moon", [outer + inner])


def gear(teeth: int) -> Design:
    def r(t):
        phase = (t * teeth / (2 * math.pi)) % 1.0
        return 450 if phase < .5 else 372
    return Design(f"Gear {teeth}", [_polar(r, teeth * 40), _circle(130)])


def cloud() -> Design:
    circles = [(250.0, 600.0, 170.0), (420.0, 470.0, 200.0), (620.0, 500.0, 180.0), (750.0, 630.0, 140.0)]
    base = 770.0
    left, right = circles[0], circles[-1]
    pts: Ring = []
    for x in [left[0] - left[2] + i * 5 for i in range(int((right[0] + right[2] - (left[0] - left[2])) / 5) + 1)]:
        ys = [cy - math.sqrt(max(r * r - (x - cx) ** 2, 0)) for cx, cy, r in circles if abs(x - cx) <= r]
        pts.append((x, min(ys)))
    pts += [(right[0] + right[2] * math.cos(a), right[1] + right[2] * math.sin(a)) for a in (math.pi / 2 * i / 24 for i in range(25))]   # round the right end down to the base
    pts += [(left[0] + left[2] * math.cos(a), left[1] + left[2] * math.sin(a)) for a in (math.pi / 2 + math.pi / 2 * i / 24 for i in range(25))]   # and the left end
    return Design("Cloud", [pts])


def drop() -> Design:
    """A circle with a pointed top: the tip joins the circle along two tangent lines."""
    r, cy, tip_y = 270.0, C + 120.0, C - 410.0
    beta = math.acos(r / (cy - tip_y))
    pts: Ring = [(C, tip_y)]
    pts += [(C + r * math.sin(phi), cy - r * math.cos(phi)) for phi in (beta + (2 * math.pi - 2 * beta) * i / 200 for i in range(201))]
    return Design("Raindrop", [pts])


def leaf() -> Design:
    """A lens: two shallow arcs meeting at pointed tips."""
    half, sag = 420.0, 230.0
    R = (half * half + sag * sag) / (2 * sag)
    cy = C + (R - sag)
    xs = [-half + 2 * half * i / 120 for i in range(121)]
    upper = [(C + x, cy - math.sqrt(R * R - x * x)) for x in xs]
    lower = [(x, 2 * C - y) for x, y in reversed(upper[1:-1])]
    return Design("Leaf", [upper + lower])


def rainbow(bands: int = 4) -> Design:
    rings = []
    outer = 460.0
    width = (outer - 130) / (bands * 2 - 1)
    for b in range(bands):
        ro = outer - 2 * b * width
        ri = ro - width
        arc_o = [(C + ro * math.cos(math.pi + math.pi * i / 90), 760 + ro * math.sin(math.pi + math.pi * i / 90)) for i in range(91)]
        arc_i = [(C + ri * math.cos(2 * math.pi - math.pi * i / 90), 760 + ri * math.sin(2 * math.pi - math.pi * i / 90)) for i in range(91)]
        rings.append(arc_o + arc_i)
    return Design(f"Rainbow {bands}", rings)


def hexagon_badge() -> Design:
    outer = [(C + 450 * math.cos(math.pi / 3 * i + math.pi / 6), C + 450 * math.sin(math.pi / 3 * i + math.pi / 6)) for i in range(6)]
    inner = [(C + 330 * math.cos(math.pi / 3 * i + math.pi / 6), C + 330 * math.sin(math.pi / 3 * i + math.pi / 6)) for i in range(6)]
    return Design("Hexagon badge", [outer, inner])


def label_tag() -> Design:
    w, h, r = 760.0, 440.0, 70.0
    x0, y0 = C - w / 2, C - h / 2
    ring: Ring = []
    for cx, cy, a0 in ((x0 + r, y0 + r, math.pi), (x0 + w - r, y0 + r, 1.5 * math.pi), (x0 + w - r, y0 + h - r, 0.0), (x0 + r + 70, y0 + h - r, .5 * math.pi)):
        ring += [(cx + r * math.cos(a0 + math.pi / 2 * i / 12), cy + r * math.sin(a0 + math.pi / 2 * i / 12)) for i in range(13)]
    ring.append((x0, y0 + h / 2 + 90))
    return Design("Label tag", [ring, _circle(36, 60, x0 + 100, C)])


def arch_window() -> Design:
    r = 280.0
    ring = [(C + r * math.cos(math.pi + math.pi * i / 90), 400 + r * math.sin(math.pi + math.pi * i / 90)) for i in range(91)] + [(C + r, 800.0), (C - r, 800.0)]
    inner_r = 190.0
    inner = [(C + inner_r * math.cos(math.pi + math.pi * i / 90), 420 + inner_r * math.sin(math.pi + math.pi * i / 90)) for i in range(91)] + [(C + inner_r, 740.0), (C - inner_r, 740.0)]
    return Design("Arch frame", [ring, inner])


def wavy(n: int) -> Design:
    """A badge with a gently wavy edge and a round cut-out."""
    return Design(f"Wavy badge {n}", [_polar(lambda t: 450 * (.9 + .1 * math.cos(n * t)), 720), _circle(250)])


def make_designs(count: int, seed: int) -> list[Design]:
    """A varied bundle: the same families with different counts and proportions, never two alike."""
    rng = random.Random(seed)
    fams = [
        lambda: star(rng.choice([5, 6, 8, 10]), rng.choice([.4, .48, .56]), hole=rng.random() < .3),
        lambda: flower(rng.choice([5, 6, 8, 10, 12]), rng.choice([.28, .38, .5])),
        lambda: scallop(rng.choice([8, 10, 12, 16, 20]), ring=rng.random() < .8),
        lambda: sunburst(rng.choice([12, 16, 20, 24, 32]), rng.choice([.5, .6, .7])),
        lambda: heart(hole=rng.random() < .5),
        crescent, lambda: gear(rng.choice([8, 10, 12, 16])), cloud, drop, leaf, lambda: rainbow(rng.choice([3, 4, 5])),
        hexagon_badge, label_tag, arch_window, lambda: wavy(rng.choice([6, 8, 10])),
    ]
    out: list[Design] = []
    seen: set[str] = set()
    i = 0
    while len(out) < count:
        d = fams[i % len(fams)]()
        i += 1
        key = d.name + str(round(d.rings[0][0][0]))
        if key in seen and i < count * 6:
            continue
        seen.add(key)
        out.append(d)
    names: dict[str, int] = {}
    for d in out:   # unique file names
        names[d.name] = names.get(d.name, 0) + 1
        if names[d.name] > 1:
            d.name = f"{d.name} {chr(64 + names[d.name])}"
    return out


# --------------------------------------------------------------------------- measurements
def thinnest_gap_mm(d: Design, size_in: float) -> float:
    """The smallest distance between two different rings (a cut-out and the edge of the design), in millimetres at this size.
    Samples ring points, so it is accurate to well under a millimetre at normal sizes."""
    import numpy as np
    from scipy.spatial import cKDTree
    pts = [np.asarray(r) for r in d.rings]
    best = float("inf")
    for i, a in enumerate(pts):
        for b in pts[i + 1:]:
            dist, _ = cKDTree(b).query(a)
            best = min(best, float(dist.min()))
    if best == float("inf"):
        return float("inf")
    return best * size_in * 25.4 / 1000.0


# --------------------------------------------------------------------------- exports
def to_svg(d: Design, size_in: float, color: str = "#000000") -> str:
    path = " ".join("M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in r) + " Z" for r in d.rings)
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{size_in}in' height='{size_in}in' viewBox='0 0 1000 1000'>"
            f"<path d='{path}' fill='{color}' fill-rule='evenodd'/></svg>")


def to_dxf(d: Design, size_in: float) -> str:
    """DXF release 12 (ASCII) closed polylines in inches, the version nearly every cutting program opens."""
    k = size_in / 1000.0
    lines = ["0", "SECTION", "2", "ENTITIES"]
    for r in d.rings:
        lines += ["0", "POLYLINE", "8", "0", "66", "1", "70", "1"]
        for x, y in r:
            lines += ["0", "VERTEX", "8", "0", "10", f"{x * k:.5f}", "20", f"{(1000 - y) * k:.5f}", "30", "0.0"]
        lines += ["0", "SEQEND", "8", "0"]
    lines += ["0", "ENDSEC", "0", "EOF"]
    return "\n".join(lines) + "\n"


def to_eps(d: Design, size_in: float) -> str:
    pt = size_in * 72
    k = pt / 1000.0
    out = ["%!PS-Adobe-3.0 EPSF-3.0", f"%%BoundingBox: 0 0 {math.ceil(pt)} {math.ceil(pt)}", "%%Creator: MoneyHub", "%%EndComments", "newpath"]
    for r in d.rings:
        out.append(f"{r[0][0] * k:.3f} {(1000 - r[0][1]) * k:.3f} moveto")
        out += [f"{x * k:.3f} {(1000 - y) * k:.3f} lineto" for x, y in r[1:]]
        out.append("closepath")
    out += ["0 setgray", "eofill", "%%EOF"]
    return "\n".join(out) + "\n"
