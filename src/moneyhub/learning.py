"""Early-learning worksheet pages for children (ages 3-7): colours, opposites, days, seasons, feelings, telling time, counting charts,
shadow matching, patterns and word tracing. Same bold black line style as kidsart.py; each page is a 1000 x 1000 SVG plus a caption."""
from __future__ import annotations

import math
import random

from . import kidsart
from .activities import FONT, INK, _dashed, _wrap
from .translations import tr

COLOURS = [("red", "#e53935"), ("blue", "#1e88e5"), ("yellow", "#fdd835"), ("green", "#43a047"), ("orange", "#fb8c00"), ("purple", "#8e24aa"),
           ("pink", "#ec407a"), ("brown", "#6d4c41")]
OBJECTS = {"red": ["apple", "heartface", "ladybug"], "blue": ["whale", "fish", "umbrella"], "yellow": ["sunface", "duck", "bee"], "green": ["frog", "tree", "turtle"],
           "orange": ["pumpkin", "fox", "icecream"], "purple": ["unicorn", "octopus", "butterfly"], "pink": ["pig", "cupcake", "flower"], "brown": ["bear", "dog", "mushroom"]}
OPPOSITES = [("big", "small"), ("tall", "short"), ("happy", "sad"), ("day", "night"), ("hot", "cold"), ("full", "empty"), ("open", "closed"), ("fast", "slow")]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WORDS = {"cat": "cat", "pig": "pig", "cow": "cow", "fox": "fox", "bee": "bee", "owl": "owl", "bat": "bat", "bus": "bus", "frog": "frog", "bear": "bear", "duck": "duck",
         "fish": "fish", "lion": "lion", "crab": "crab", "kite": "kite", "tree": "tree", "sunface": "sun", "apple": "apple", "pizza": "pizza", "house": "house"}
FEELINGS = ["happy", "sad", "angry", "surprised", "sleepy", "scared"]
SEASONS = [("Spring", "flower"), ("Summer", "sunface"), ("Autumn", "mushroom"), ("Winter", "snowflake")]
PATTERN_SHAPES = ["circle", "square", "triangle", "star", "heart"]


def _fig(kind: str, x: float, y: float, size: float, seed: int, width: float = 14, fill: str | None = None) -> str:
    s = size / 1000
    body = kidsart.figure(kind, seed, width / s * .6 if width > 4 else width, True)
    if fill:   # a solid silhouette (shadow matching)
        body = body.replace("fill='#ffffff'", f"fill='{fill}'")
    return f"<g transform='translate({x - 500 * s:.0f} {y - 500 * s:.0f}) scale({s:.3f})'>{body}</g>"


def _text(t: str, x: float, y: float, size: float, anchor: str = "middle", weight: str = "") -> str:
    return f"<text x='{x:.0f}' y='{y:.0f}' font-size='{size:.0f}' text-anchor='{anchor}' {FONT} fill='{INK}'>{t}</text>"


def _shape(name: str, cx: float, cy: float, r: float, fill: str = "#ffffff") -> str:
    st = f"fill='{fill}' stroke='{INK}' stroke-width='9' stroke-linejoin='round'"
    if name == "circle":
        return f"<circle cx='{cx:.0f}' cy='{cy:.0f}' r='{r:.0f}' {st}/>"
    if name == "square":
        return f"<rect x='{cx - r:.0f}' y='{cy - r:.0f}' width='{2 * r:.0f}' height='{2 * r:.0f}' rx='8' {st}/>"
    if name == "triangle":
        return f"<polygon points='{cx:.0f},{cy - r:.0f} {cx + r:.0f},{cy + r * .85:.0f} {cx - r:.0f},{cy + r * .85:.0f}' {st}/>"
    if name == "star":
        return f"<polygon points='{' '.join(f'{x:.0f},{y:.0f}' for x, y in kidsart._star_pts(cx, cy, r * 1.1, .45))}' {st}/>"
    s = r / 55
    return (f"<path d='M{cx:.0f} {cy + 50 * s:.0f} C{cx - 110 * s:.0f} {cy - 15 * s:.0f} {cx - 55 * s:.0f} {cy - 90 * s:.0f} {cx:.0f} {cy - 38 * s:.0f} "
            f"C{cx + 55 * s:.0f} {cy - 90 * s:.0f} {cx + 110 * s:.0f} {cy - 15 * s:.0f} {cx:.0f} {cy + 50 * s:.0f} Z' {st}/>")


# --------------------------------------------------------------------------- pages
def colour_page(i: int, seed: int, lang: str = "en") -> tuple[str, str]:
    name, hexv = COLOURS[i % len(COLOURS)]
    kinds = OBJECTS[name]
    out = [f"<circle cx='500' cy='190' r='110' fill='{hexv}' stroke='{INK}' stroke-width='9'/>", _text(tr(name, lang).upper(), 500, 400, 120 if len(tr(name, lang)) < 9 else 90)]
    for k, kind in enumerate(kinds):
        out.append(_fig(kind, 190 + k * 310, 640, 290, seed + k, 12))
    out.append(_text(f"Color the {name} things {name}!" if lang == "en" else f"{tr(name, lang)} = {name}", 500, 900, 52))
    return _wrap("".join(out)), f"This is {name}" + (f" ({tr(name, lang)})" if lang != "en" else "") + f". Color the {name} things!"


def opposite_page(i: int, seed: int, lang: str = "en") -> tuple[str, str]:
    a, b = OPPOSITES[i % len(OPPOSITES)]
    pool = ["bear", "cat", "house", "tree", "dog", "elephant", "owl"]
    kind = pool[(seed + i) % len(pool)]
    out = []
    if a == "big":
        out = [_fig(kind, 290, 520, 480, seed), _fig(kind, 770, 700, 150, seed)]
    elif a == "tall":
        out = [_fig("giraffe", 290, 520, 520, seed), _fig("snail", 770, 760, 220, seed)]
    elif a == "happy":
        out = [_fig("sunface", 290, 520, 400, seed), _fig("moonface", 770, 520, 400, seed)]
    elif a == "day":
        out = [_fig("sunface", 290, 520, 400, seed), _fig("moonface", 770, 520, 400, seed)]
    elif a == "hot":
        out = [_fig("sunface", 290, 520, 400, seed), _fig("snowflake", 770, 520, 400, seed)]
    elif a == "full":
        out = [_fig("cupcake", 290, 520, 400, seed), _fig("balloons", 770, 520, 400, seed)]
    elif a == "open":
        out = [_fig("house", 290, 520, 400, seed), _fig("castle", 770, 520, 400, seed)]
    else:
        out = [_fig("car", 290, 520, 400, seed), _fig("snail", 770, 600, 330, seed)]
    out += [_text(tr(a, lang).upper(), 290, 880, 78 if len(tr(a, lang)) < 9 else 58), _text(tr(b, lang).upper(), 770, 880, 78 if len(tr(b, lang)) < 9 else 58), "<line x1='500' y1='160' x2='500' y2='940' stroke='#222' stroke-width='5' stroke-dasharray='4 14' stroke-linecap='round'/>"]
    return _wrap("".join(out)), f"{a.capitalize()} and {b}" + (f" ({tr(a, lang)} / {tr(b, lang)})" if lang != "en" else "") + ": trace the words and color!"


def days_page(i: int, seed: int, lang: str = "en") -> tuple[str, str]:
    out = []
    for k, d in enumerate(DAYS):
        y = 90 + k * 125
        out.append(f"<rect x='60' y='{y}' width='880' height='105' rx='20' fill='#fff' stroke='{INK}' stroke-width='6'/>")
        out.append(_dashed(tr(d, lang), 110, y + 76, 66, 3, "start"))
        out.append(_fig(["sunface", "moonface", "rainbowcloud", "umbrella", "kite", "flower", "heartface"][k], 850, y + 52, 90, seed + k, 5))
    return _wrap("".join(out)), "Days of the week: trace each day!"


def seasons_page(i: int, seed: int, lang: str = "en") -> tuple[str, str]:
    out = []
    for k, (name, kind) in enumerate(SEASONS):
        x, y = 280 + (k % 2) * 440, 270 + (k // 2) * 440
        out.append(f"<rect x='{x - 205}' y='{y - 215}' width='410' height='430' rx='30' fill='#fff' stroke='{INK}' stroke-width='6'/>")
        out.append(_fig(kind, x, y - 25, 250, seed + k, 10))
        out.append(_dashed(tr(name, lang), x, y + 175, 60, 3))
    return _wrap("".join(out)), "Four seasons: trace each name and color the picture!"


def feelings_page(i: int, seed: int, lang: str = "en") -> tuple[str, str]:
    out = []
    for k, f in enumerate(FEELINGS):
        cx, cy = 190 + (k % 3) * 310, 260 + (k // 3) * 440
        out.append(f"<circle cx='{cx}' cy='{cy}' r='130' fill='#fff' stroke='{INK}' stroke-width='9'/>")
        eyes = {"happy": ("dot", "dot"), "sad": ("dot", "dot"), "angry": ("dot", "dot"), "surprised": ("ring", "ring"), "sleepy": ("line", "line"), "scared": ("ring", "ring")}[f]
        for sx in (-1, 1):
            ex, ey = cx + sx * 48, cy - 25
            if eyes[0] == "dot":
                out.append(f"<circle cx='{ex}' cy='{ey}' r='13' fill='{INK}'/>")
            elif eyes[0] == "ring":
                out.append(f"<circle cx='{ex}' cy='{ey}' r='20' fill='#fff' stroke='{INK}' stroke-width='6'/><circle cx='{ex}' cy='{ey}' r='7' fill='{INK}'/>")
            else:
                out.append(f"<path d='M{ex - 20} {ey} q20 18 40 0' fill='none' stroke='{INK}' stroke-width='7' stroke-linecap='round'/>")
        if f == "angry":
            out.append(f"<path d='M{cx - 78} {cy - 62} L{cx - 22} {cy - 42} M{cx + 78} {cy - 62} L{cx + 22} {cy - 42}' stroke='{INK}' stroke-width='8' stroke-linecap='round'/>")
        mouth = {"happy": f"M{cx - 55} {cy + 35} Q{cx} {cy + 95} {cx + 55} {cy + 35}", "sad": f"M{cx - 50} {cy + 70} Q{cx} {cy + 25} {cx + 50} {cy + 70}",
                 "angry": f"M{cx - 50} {cy + 65} Q{cx} {cy + 35} {cx + 50} {cy + 65}", "surprised": "", "sleepy": f"M{cx - 25} {cy + 55} h50", "scared": f"M{cx - 45} {cy + 60} q15 -15 30 0 t30 0 t30 0"}[f]
        if mouth:
            out.append(f"<path d='{mouth}' fill='none' stroke='{INK}' stroke-width='8' stroke-linecap='round'/>")
        else:
            out.append(f"<ellipse cx='{cx}' cy='{cy + 62}' rx='24' ry='30' fill='#fff' stroke='{INK}' stroke-width='7'/>")
        out.append(_dashed(tr(f, lang), cx, cy + 235, 52 if len(tr(f, lang)) < 10 else 40, 3))
    return _wrap("".join(out)), "How do you feel? Trace the word and color the face!"


def clock_page(i: int, seed: int, lang: str = "en") -> tuple[str, str]:
    rng = random.Random(seed)
    out = []
    hours = [rng.randrange(1, 13) for _ in range(4)]
    for k, h in enumerate(hours):
        cx, cy, r = 260 + (k % 2) * 480, 230 + (k // 2) * 470, 170
        out.append(f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='#fff' stroke='{INK}' stroke-width='9'/>")
        for n in range(1, 13):
            a = math.radians(n * 30 - 90)
            out.append(_text(str(n), cx + (r - 38) * math.cos(a), cy + (r - 38) * math.sin(a) + 14, 40))
        a = math.radians(h * 30 - 90)
        out.append(f"<line x1='{cx}' y1='{cy}' x2='{cx + (r - 85) * math.cos(a):.0f}' y2='{cy + (r - 85) * math.sin(a):.0f}' stroke='{INK}' stroke-width='14' stroke-linecap='round'/>")
        out.append(f"<line x1='{cx}' y1='{cy}' x2='{cx}' y2='{cy - (r - 45)}' stroke='{INK}' stroke-width='8' stroke-linecap='round'/><circle cx='{cx}' cy='{cy}' r='12' fill='{INK}'/>")
        out.append(f"<line x1='{cx - 110}' y1='{cy + r + 70}' x2='{cx + 30}' y2='{cy + r + 70}' stroke='{INK}' stroke-width='5'/>" + _text(":00", cx + 85, cy + r + 70, 52))
    return _wrap("".join(out)), "What time is it? Write the hour!"


def count_chart_page(i: int, seed: int, lang: str = "en") -> tuple[str, str]:
    start = 1 + (i % 2) * 10
    out = []
    kind = kidsart.THEMES["mixed"][1][(seed + i) % 16]
    for k in range(10):
        n = start + k
        y = 90 + k * 90
        out.append(_text(str(n), 90, y + 58, 62))
        for d in range(min(n, 20)):
            out.append(f"<circle cx='{190 + d * 38}' cy='{y + 40}' r='15' fill='#fff' stroke='{INK}' stroke-width='5'/>")
    return _wrap("".join(out)), f"Count and color the dots: {start} to {start + 9}!"


def shadow_page(i: int, seed: int, lang: str = "en") -> tuple[str, str]:
    rng = random.Random(seed)
    kinds = rng.sample(kidsart.KINDS[:38], 4)
    shadows = kinds[:]
    rng.shuffle(shadows)
    out = []
    for k, kind in enumerate(kinds):
        y = 170 + k * 215
        out.append(_fig(kind, 190, y, 190, seed + k, 12))
        out.append(_fig(shadows[k], 810, y, 190, seed + kinds.index(shadows[k]), 12, INK))
        out.append(f"<circle cx='330' cy='{y}' r='11' fill='{INK}'/><circle cx='670' cy='{y}' r='11' fill='{INK}'/>")
    return _wrap("".join(out)), "Draw a line from each picture to its shadow!"


def pattern_page(i: int, seed: int, lang: str = "en") -> tuple[str, str]:
    rng = random.Random(seed)
    out = []
    for r in range(4):
        a, b = rng.sample(PATTERN_SHAPES, 2)
        seq = [a, b] * 3 if r % 2 == 0 else [a, a, b] * 2
        seq = seq[:6]
        for c, nm in enumerate(seq[:-1]):
            out.append(_shape(nm, 110 + c * 150, 130 + r * 230, 55))
        out.append(f"<rect x='{110 + 5 * 150 - 60}' y='{130 + r * 230 - 60}' width='120' height='120' rx='14' fill='#fff' stroke='{INK}' stroke-width='6' stroke-dasharray='10 12'/>")
        out.append(_text("?", 110 + 5 * 150, 130 + r * 230 + 28, 80))
    return _wrap("".join(out)), "What comes next? Draw the shape!"


def word_page(i: int, seed: int, lang: str = "en") -> tuple[str, str]:
    kinds = list(WORDS)
    kind = kinds[i % len(kinds)]
    w = tr(WORDS[kind], lang)
    out = [_fig(kind, 500, 290, 420, seed, 12)]
    out.append(_dashed(w, 500, 640, 190 if len(w) <= 4 else 150, 6))
    for k in range(2):
        out.append(_dashed(w, 500, 790 + k * 130, 100, 4))
        out.append(f"<line x1='90' y1='{805 + k * 130}' x2='910' y2='{805 + k * 130}' stroke='{INK}' stroke-width='3'/>")
    return _wrap("".join(out)), f"Trace the word: {w}!" + (f" ({WORDS[kind]})" if lang != "en" else "")


PAGES = {"colours": colour_page, "opposites": opposite_page, "days": days_page, "seasons": seasons_page, "feelings": feelings_page, "time": clock_page,
         "counting": count_chart_page, "shadows": shadow_page, "patterns": pattern_page, "words": word_page}
FOCUS = {
    "mixed": ["colours", "words", "counting", "shadows", "opposites", "patterns", "feelings", "time", "days", "seasons"],
    "colours": ["colours", "colours", "shadows", "patterns"],
    "words": ["words", "words", "shadows", "colours"],
    "numbers": ["counting", "patterns", "time", "counting"],
    "time": ["days", "time", "seasons", "time"],
    "feelings": ["feelings", "opposites", "feelings", "shadows"],
}


def page_art(i: int, seed: int, focus: str = "mixed", lang: str = "en") -> tuple[str, str, str]:
    plan = FOCUS.get(focus, FOCUS["mixed"])
    kind = plan[i % len(plan)]
    n = sum(1 for j in range(i) if plan[j % len(plan)] == kind)
    svg, cap = PAGES[kind](n, seed * 1009 + i * 17, lang)
    return kind, svg, cap
