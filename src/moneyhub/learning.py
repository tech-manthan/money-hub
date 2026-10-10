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


def page_art(i: int, seed: int, focus: str = "mixed", lang: str = "en", grade: str = "k") -> tuple[str, str, str]:
    if focus in ("handwriting", "cursive"):
        style = "cursive" if focus == "cursive" else "print"
        if i < 26:
            kind, svg, cap = "letterform", *_hw.letter_page(i, seed, style)
        else:
            kind = "handwords" if i % 2 == 0 else "lined"
            svg, cap = (_hw.words_page if kind == "handwords" else _hw.lined_page)((i - 26) // 2, seed, style)
        return kind, svg, cap
    plan = FOCUS.get(focus, FOCUS["mixed"])
    kind = plan[i % len(plan)]
    n = sum(1 for j in range(i) if plan[j % len(plan)] == kind)
    extra = (grade,) if kind.startswith("sight_") else ()
    svg, cap = PAGES[kind](n, seed * 1009 + i * 17, lang, *extra)
    return kind, svg, cap


# --------------------------------------------------------------------------- handwriting, sight words and STEM shapes (English only)
from . import handwriting as _hw   # noqa: E402

DOLCH = {
    "prek": ("Pre-K", "a and away big blue can come down find for funny go help here I in is it jump little look make me my not one play red run said see the "
                      "three to two up we where yellow you"),
    "k": ("Kindergarten", "all am are at ate be black brown but came did do eat four get good have he into like must new no now on our out please pretty ran "
                          "ride saw say she so soon that there they this too under want was well went what white who will with yes"),
    "1": ("1st Grade", "after again an any as ask by could every fly from give going had has her him his how just know let live may of old once open over put "
                       "round some stop take thank them then think walk were when"),
    "2": ("2nd Grade", "always around because been before best both buy call cold does don't fast first five found gave goes green its made many off or pull "
                       "read right sing sit sleep tell their these those upon us use very wash which why wish work would write your"),
    "3": ("3rd Grade", "about better bring carry clean cut done draw drink eight fall far full got grow hold hot hurt if keep kind laugh light long much myself "
                       "never only own pick seven shall show six small start ten today together try warm"),
}
GRADES = list(DOLCH)


def sight_words(grade: str) -> list[str]:
    return DOLCH[grade][1].split()


def _chunk(words: list[str], n: int, size: int) -> list[str]:
    return [words[(n * size + k) % len(words)] for k in range(size)]


def sight_trace_page(n: int, seed: int, lang: str = "en", grade: str = "k") -> tuple[str, str]:
    out = []
    for k, w in enumerate(_chunk(sight_words(grade), n, 3)):
        top = 40 + k * 315
        out.append(f"<rect x='50' y='{top}' width='900' height='290' rx='24' fill='#fff' stroke='{INK}' stroke-width='5'/>")
        out.append(_dashed(w, 500, top + 165, 190 if len(w) <= 4 else 160 if len(w) <= 6 else 120, 6))
        for r in range(2):
            y = top + 215 + r * 55
            out.append(f"<line x1='90' y1='{y}' x2='910' y2='{y}' stroke='{INK}' stroke-width='3'/>")
    return _wrap("".join(out)), "Trace each sight word, then write it two times!"


def sight_rainbow_page(n: int, seed: int, lang: str = "en", grade: str = "k") -> tuple[str, str]:
    out = []
    for k, w in enumerate(_chunk(sight_words(grade), n + 3, 3)):
        top = 40 + k * 315
        out.append(f"<rect x='50' y='{top}' width='900' height='290' rx='24' fill='#fff' stroke='{INK}' stroke-width='5'/>")
        out.append(f"<text x='500' y='{top + 175}' font-size='{150 if len(w) <= 5 else 110}' text-anchor='middle' {FONT} fill='#ffffff' stroke='{INK}' stroke-width='5' "
                   f"stroke-linejoin='round'>{w}</text>")
        for c, col in enumerate(("#e53935", "#fb8c00", "#fdd835", "#43a047", "#1e88e5", "#8e24aa")):
            out.append(f"<circle cx='{300 + c * 80}' cy='{top + 245}' r='16' fill='{col}' stroke='{INK}' stroke-width='3'/>")
    return _wrap("".join(out)), "Rainbow write: trace each word in different colors!"


def sight_fill_page(n: int, seed: int, lang: str = "en", grade: str = "k") -> tuple[str, str]:
    rng = random.Random(seed + n)
    out = []
    for k, w in enumerate(_chunk(sight_words(grade), n + 1, 6)):
        top = 40 + k * 155
        i = rng.randrange(len(w)) if len(w) > 1 else 0
        out.append(f"<rect x='50' y='{top}' width='900' height='135' rx='20' fill='#fff' stroke='{INK}' stroke-width='5'/>")
        out.append(_text(w, 190, top + 90, 70))
        out.append(f"<text x='400' y='{top + 88}' font-size='60' text-anchor='middle' {FONT} fill='#777'>&#8594;</text>")
        x = 660 - (len(w) * 62) / 2
        for j, ch in enumerate(w):
            cx = x + j * 62
            if j == i:
                out.append(f"<rect x='{cx - 24:.0f}' y='{top + 28}' width='48' height='80' rx='8' fill='#fff' stroke='{INK}' stroke-width='5' stroke-dasharray='8 8'/>")
            else:
                out.append(_text(ch, cx, top + 90, 70))
    return _wrap("".join(out)), "Fill in the missing letter in each word!"


def sight_lookcover_page(n: int, seed: int, lang: str = "en", grade: str = "k") -> tuple[str, str]:
    out = [_text("LOOK", 220, 80, 46), _text("COVER, WRITE", 610, 80, 46), _text("CHECK", 880, 80, 46)]
    for k, w in enumerate(_chunk(sight_words(grade), n + 2, 5)):
        top = 120 + k * 170
        out.append(f"<rect x='50' y='{top}' width='340' height='150' rx='20' fill='#fff' stroke='{INK}' stroke-width='5'/>")
        out.append(_text(w, 220, top + 100, 80 if len(w) <= 6 else 62))
        out.append(f"<rect x='410' y='{top}' width='390' height='150' rx='20' fill='#fff' stroke='{INK}' stroke-width='5'/>")
        out.append(f"<rect x='820' y='{top}' width='130' height='150' rx='20' fill='#fff' stroke='{INK}' stroke-width='5'/><circle cx='885' cy='{top + 75}' r='30' fill='none' stroke='{INK}' stroke-width='4' stroke-dasharray='6 8'/>")
    return _wrap("".join(out)), "Look at the word, cover it, write it, then check!"


def _poly_shape(name: str, cx: float, cy: float, r: float, fill: str = "#ffffff") -> str:
    st = f"fill='{fill}' stroke='{INK}' stroke-width='9' stroke-linejoin='round'"
    if name == "rectangle":
        return f"<rect x='{cx - r * 1.35:.0f}' y='{cy - r * .75:.0f}' width='{r * 2.7:.0f}' height='{r * 1.5:.0f}' rx='6' {st}/>"
    if name == "oval":
        return f"<ellipse cx='{cx:.0f}' cy='{cy:.0f}' rx='{r * 1.3:.0f}' ry='{r * .85:.0f}' {st}/>"
    if name == "diamond":
        return f"<polygon points='{cx:.0f},{cy - r * 1.15:.0f} {cx + r * .85:.0f},{cy:.0f} {cx:.0f},{cy + r * 1.15:.0f} {cx - r * .85:.0f},{cy:.0f}' {st}/>"
    if name == "hexagon":
        pts = [(cx + r * 1.05 * math.cos(math.radians(60 * i)), cy + r * 1.05 * math.sin(math.radians(60 * i))) for i in range(6)]
        return f"<polygon points='{' '.join(f'{x:.0f},{y:.0f}' for x, y in pts)}' {st}/>"
    return _shape(name, cx, cy, r, fill)


SHAPE_NAMES = ["circle", "square", "triangle", "rectangle", "oval", "star", "heart", "diamond", "hexagon"]


def shape_names_page(n: int, seed: int, lang: str = "en") -> tuple[str, str]:
    out = []
    for k in range(3):
        name = SHAPE_NAMES[(n * 3 + k) % len(SHAPE_NAMES)]
        cy = 190 + k * 300
        out.append(f"<rect x='50' y='{cy - 130}' width='900' height='260' rx='24' fill='#fff' stroke='{INK}' stroke-width='5'/>")
        out.append(_poly_shape(name, 250, cy, 90))
        out.append(_dashed(name, 640, cy + 40, 150 if len(name) < 7 else 120 if len(name) < 9 else 100, 5))
    return _wrap("".join(out)), "Trace the shape name and color the shape!"


def _solid3d(name: str, cx: float, cy: float, s: float) -> str:
    st = f"stroke='{INK}' stroke-width='8' stroke-linejoin='round'"
    if name == "cube":
        a = s * .55
        return (f"<polygon points='{cx - a:.0f},{cy - a + 40:.0f} {cx + a - 40:.0f},{cy - a + 40:.0f} {cx + a - 40:.0f},{cy + a:.0f} {cx - a:.0f},{cy + a:.0f}' fill='#fff' {st}/>"
                f"<polygon points='{cx - a:.0f},{cy - a + 40:.0f} {cx - a + 40:.0f},{cy - a:.0f} {cx + a:.0f},{cy - a:.0f} {cx + a - 40:.0f},{cy - a + 40:.0f}' fill='#fff' {st}/>"
                f"<polygon points='{cx + a - 40:.0f},{cy - a + 40:.0f} {cx + a:.0f},{cy - a:.0f} {cx + a:.0f},{cy + a - 40:.0f} {cx + a - 40:.0f},{cy + a:.0f}' fill='#fff' {st}/>")
    if name == "rectangular prism":
        w, h = s * .8, s * .45
        return (f"<polygon points='{cx - w:.0f},{cy - h + 40:.0f} {cx + w - 40:.0f},{cy - h + 40:.0f} {cx + w - 40:.0f},{cy + h:.0f} {cx - w:.0f},{cy + h:.0f}' fill='#fff' {st}/>"
                f"<polygon points='{cx - w:.0f},{cy - h + 40:.0f} {cx - w + 40:.0f},{cy - h:.0f} {cx + w:.0f},{cy - h:.0f} {cx + w - 40:.0f},{cy - h + 40:.0f}' fill='#fff' {st}/>"
                f"<polygon points='{cx + w - 40:.0f},{cy - h + 40:.0f} {cx + w:.0f},{cy - h:.0f} {cx + w:.0f},{cy + h - 40:.0f} {cx + w - 40:.0f},{cy + h:.0f}' fill='#fff' {st}/>")
    if name == "sphere":
        r = s * .6
        return (f"<circle cx='{cx:.0f}' cy='{cy:.0f}' r='{r:.0f}' fill='#fff' {st}/>"
                f"<ellipse cx='{cx:.0f}' cy='{cy:.0f}' rx='{r:.0f}' ry='{r * .28:.0f}' fill='none' stroke='{INK}' stroke-width='5' stroke-dasharray='10 10'/>"
                f"<path d='M{cx - r * .55:.0f} {cy - r * .45:.0f} Q{cx - r * .3:.0f} {cy - r * .75:.0f} {cx + r * .1:.0f} {cy - r * .78:.0f}' fill='none' stroke='{INK}' stroke-width='6' stroke-linecap='round'/>")
    if name == "cone":
        r, h = s * .5, s * 1.0
        return (f"<path d='M{cx - r:.0f} {cy + h * .45:.0f} A{r:.0f} {r * .3:.0f} 0 0 0 {cx + r:.0f} {cy + h * .45:.0f} L{cx:.0f} {cy - h * .55:.0f} Z' fill='#fff' {st}/>"
                f"<path d='M{cx - r:.0f} {cy + h * .45:.0f} A{r:.0f} {r * .3:.0f} 0 0 1 {cx + r:.0f} {cy + h * .45:.0f}' fill='none' stroke='{INK}' stroke-width='5' stroke-dasharray='10 10'/>")
    if name == "cylinder":
        r, h = s * .5, s * .95
        return (f"<path d='M{cx - r:.0f} {cy - h * .4:.0f} V{cy + h * .4:.0f} A{r:.0f} {r * .3:.0f} 0 0 0 {cx + r:.0f} {cy + h * .4:.0f} V{cy - h * .4:.0f}' fill='#fff' {st}/>"
                f"<ellipse cx='{cx:.0f}' cy='{cy - h * .4:.0f}' rx='{r:.0f}' ry='{r * .3:.0f}' fill='#fff' {st}/>")
    a = s * .6   # square pyramid
    return (f"<polygon points='{cx - a:.0f},{cy + a * .55:.0f} {cx:.0f},{cy - a:.0f} {cx + a * .35:.0f},{cy + a * .8:.0f}' fill='#fff' {st}/>"
            f"<polygon points='{cx:.0f},{cy - a:.0f} {cx + a:.0f},{cy + a * .55:.0f} {cx + a * .35:.0f},{cy + a * .8:.0f}' fill='#fff' {st}/>"
            f"<path d='M{cx - a:.0f} {cy + a * .55:.0f} L{cx + a:.0f} {cy + a * .55:.0f}' stroke='{INK}' stroke-width='5' stroke-dasharray='10 10'/>")


SOLIDS = [("cube", "like a dice"), ("sphere", "like a ball"), ("cone", "like a party hat"), ("cylinder", "like a can"),
          ("rectangular prism", "like a cereal box"), ("pyramid", "like a tent roof")]


def solids_page(n: int, seed: int, lang: str = "en") -> tuple[str, str]:
    out = []
    for k in range(3):
        name, like = SOLIDS[(n * 3 + k) % len(SOLIDS)]
        cy = 190 + k * 300
        out.append(f"<rect x='50' y='{cy - 130}' width='900' height='260' rx='24' fill='#fff' stroke='{INK}' stroke-width='5'/>")
        out.append(_solid3d(name, 240, cy, 190 if name != "rectangular prism" else 150))
        out.append(_dashed(name, 640, cy - 5, 110 if len(name) < 7 else 84 if len(name) < 10 else 62, 4))
        out.append(f"<text x='640' y='{cy + 70}' font-size='44' text-anchor='middle' {FONT} fill='#777'>{like}</text>")
    return _wrap("".join(out)), "3D shapes: trace the name and color the shape!"


def _machine(name: str, cx: float, cy: float) -> str:
    st = f"stroke='{INK}' stroke-width='8' stroke-linejoin='round' stroke-linecap='round'"
    if name == "lever":
        return (f"<polygon points='{cx - 40:.0f},{cy + 80:.0f} {cx + 40:.0f},{cy + 80:.0f} {cx:.0f},{cy + 10:.0f}' fill='#fff' {st}/>"
                f"<polygon points='{cx - 190:.0f},{cy + 5:.0f} {cx + 190:.0f},{cy - 55:.0f} {cx + 190:.0f},{cy - 30:.0f} {cx - 190:.0f},{cy + 30:.0f}' fill='#fff' {st}/>"
                f"<circle cx='{cx - 165:.0f}' cy='{cy - 20:.0f}' r='26' fill='#fff' {st}/><rect x='{cx + 135:.0f}' y='{cy - 100:.0f}' width='50' height='45' fill='#fff' {st}/>")
    if name == "wheel and axle":
        return (f"<circle cx='{cx:.0f}' cy='{cy:.0f}' r='90' fill='#fff' {st}/><circle cx='{cx:.0f}' cy='{cy:.0f}' r='18' fill='{INK}'/>"
                + "".join(f"<line x1='{cx:.0f}' y1='{cy:.0f}' x2='{cx + 90 * math.cos(math.radians(a)):.0f}' y2='{cy + 90 * math.sin(math.radians(a)):.0f}' {st}/>" for a in range(0, 360, 60)))
    if name == "pulley":
        return (f"<line x1='{cx:.0f}' y1='{cy - 110:.0f}' x2='{cx:.0f}' y2='{cy - 60:.0f}' {st}/><circle cx='{cx:.0f}' cy='{cy - 20:.0f}' r='42' fill='#fff' {st}/>"
                f"<circle cx='{cx:.0f}' cy='{cy - 20:.0f}' r='8' fill='{INK}'/><line x1='{cx - 42:.0f}' y1='{cy - 20:.0f}' x2='{cx - 42:.0f}' y2='{cy + 55:.0f}' {st}/>"
                f"<line x1='{cx + 42:.0f}' y1='{cy - 20:.0f}' x2='{cx + 42:.0f}' y2='{cy + 30:.0f}' {st}/>"
                f"<path d='M{cx - 80:.0f} {cy + 55:.0f} h76 v50 h-76 z' fill='#fff' {st}/><circle cx='{cx + 42:.0f}' cy='{cy + 50:.0f}' r='18' fill='#fff' {st}/>")
    if name == "inclined plane":
        return (f"<polygon points='{cx - 170:.0f},{cy + 80:.0f} {cx + 170:.0f},{cy + 80:.0f} {cx + 170:.0f},{cy - 70:.0f}' fill='#fff' {st}/>"
                f"<circle cx='{cx + 40:.0f}' cy='{cy - 4:.0f}' r='30' fill='#fff' {st}/>")
    if name == "wedge":
        return (f"<polygon points='{cx - 130:.0f},{cy + 70:.0f} {cx + 110:.0f},{cy + 70:.0f} {cx + 110:.0f},{cy - 10:.0f}' fill='#fff' {st}/>"
                f"<rect x='{cx - 60:.0f}' y='{cy + 70:.0f}' width='1' height='1' fill='none'/><line x1='{cx - 30:.0f}' y1='{cy + 35:.0f}' x2='{cx + 90:.0f}' y2='{cy + 35:.0f}' {st} stroke-dasharray='1 14'/>")
    return (f"<rect x='{cx - 40:.0f}' y='{cy - 100:.0f}' width='80' height='190' rx='10' fill='#fff' {st}/>"
            + "".join(f"<path d='M{cx - 40:.0f} {cy - 70 + k * 40:.0f} L{cx + 40:.0f} {cy - 50 + k * 40:.0f}' {st}/>" for k in range(4)) +
            f"<polygon points='{cx - 40:.0f},{cy + 90:.0f} {cx + 40:.0f},{cy + 90:.0f} {cx:.0f},{cy + 135:.0f}' fill='#fff' {st}/>")


MACHINES = [("lever", "a seesaw"), ("wheel and axle", "a wheel"), ("pulley", "lifts a bucket"), ("inclined plane", "a ramp"), ("wedge", "a doorstop"), ("screw", "a jar lid")]


def machines_page(n: int, seed: int, lang: str = "en") -> tuple[str, str]:
    out = []
    for k in range(3):
        name, like = MACHINES[(n * 3 + k) % len(MACHINES)]
        cy = 190 + k * 300
        out.append(f"<rect x='50' y='{cy - 130}' width='900' height='260' rx='24' fill='#fff' stroke='{INK}' stroke-width='5'/>")
        out.append(_machine(name, 250, cy))
        out.append(_dashed(name, 690, cy - 5, 100 if len(name) < 8 else 84 if len(name) < 10 else 62, 3 if len(name) > 10 else 4))
        out.append(f"<text x='690' y='{cy + 70}' font-size='44' text-anchor='middle' {FONT} fill='#777'>{like}</text>")
    return _wrap("".join(out)), "Simple machines: trace the name and color the picture!"


def shape_count_page(n: int, seed: int, lang: str = "en") -> tuple[str, str]:
    rng = random.Random(seed)
    names = ["circle", "square", "triangle", "star"]
    cells = [(c, r) for c in range(5) for r in range(3)]
    rng.shuffle(cells)
    counts = {k: 0 for k in names}
    out = []
    for c, r in cells[:rng.randint(11, 15)]:
        name = rng.choice(names)
        counts[name] += 1
        out.append(_shape(name, 130 + c * 185 + rng.randint(-14, 14), 150 + r * 185 + rng.randint(-14, 14), 52))
    for k, name in enumerate(names):
        x = 135 + k * 215
        out.append(_shape(name, x, 790, 45))
        out.append(f"<rect x='{x - 55}' y='850' width='110' height='90' rx='14' fill='#fff' stroke='{INK}' stroke-width='5' stroke-dasharray='8 8'/>")
    return _wrap("".join(out)), "Count each shape and write the number in the box!"


PAGES.update({"letterform": None, "handwords": None, "lined": None, "sight_trace": sight_trace_page, "sight_rainbow": sight_rainbow_page,
              "sight_fill": sight_fill_page, "sight_lookcover": sight_lookcover_page, "shapenames": shape_names_page, "solids": solids_page,
              "machines": machines_page, "shapecount": shape_count_page})
FOCUS.update({"handwriting": ["letterform"], "cursive": ["letterform"], "sightwords": ["sight_trace", "sight_fill", "sight_rainbow", "sight_lookcover"],
              "stem": ["shapenames", "solids", "shapecount", "machines", "patterns"]})
ENGLISH_ONLY = ("handwriting", "cursive", "sightwords", "stem")
