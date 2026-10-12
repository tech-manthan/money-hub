"""Optional decoration for printable pages: three independent layers, all OFF by default.

  corner      faint line art in a corner of every page (a watermark / flourish)
  header      a small row of themed pictures in the title bar
  background  a pale pattern or watercolour wash behind the page

Each layer has a style (`themed` uses pictures that suit the audience: a stethoscope and heart for nurses, a sprout for gardeners ...)
and all share one strength (light, medium, bold). Everything is drawn as SVG from the product's own palette, so it matches the colours,
and the strengths are capped so that text stays easy to read (tests check the contrast of the ink on the strongest tint of every palette).

The pictures are original simple line drawings made for this module (no third-party art, nothing to attribute)."""
from __future__ import annotations

import base64
import math
import random
import re
from dataclasses import dataclass

from . import patterns
from .design import Palette, Style, _mix, contrast

NONE = "none"
STRENGTHS = ("light", "medium", "bold")
CORNER_AT = ("bottom-right", "top-right", "bottom-left", "top-left", "opposite")
CORNER_STYLES = ("themed", "botanical", "floral", "waves", "sparkles", "geometric")
HEADER_STYLES = ("themed", "botanical", "floral", "sparkles", "hearts", "waves")
BACKGROUND_STYLES = ("themed", "watercolor", "dots", "leaves", "daisies", "waves", "sparkles", "diamonds", "terrazzo", "hearts", "stars", "confetti",
                     "solid", "gradient", "grid", "stripes", "frame", "paper", "floral")
PAPER_TONES = ("#f1e2bd", "#f4ead9", "#ead9c0", "#f2dcd4", "#e3ecd6", "#dde8ee", "#e8dff0", "#f3efc9")   # cream, ivory, sand, blush, mint, sky, lilac, butter
AUTO_MAX = 1000
PIC_OPACITY = {"light": .11, "medium": .17, "bold": .23}   # a picture background is thin lines over the page, so it can be stronger than a tint
FLORAL_OPACITY = {"light": .12, "medium": .18, "bold": .23}   # big filled blooms in the corners: stronger than a tint, but only near the page edges
PIC_PREFIX = "pic:"   # `pic:stethoscope`: one picture from the library repeated all over the page     # `auto:N` (1..1000): a numbered, repeatable background made from the pattern library and the whole-page fills
# whole-page backgrounds drawn with plain CSS (a colour, a fade, lines or a border) instead of a picture tile
FILLS = ("solid", "gradient", "grid", "stripes", "frame", "paper")
# opacity of each layer by strength. The background one is the strongest tint the page can get; see `tint` and the contrast test.
OPACITY = {"corner": {"light": .14, "medium": .22, "bold": .32},
           "header": {"light": .32, "medium": .48, "bold": .66},
           "background": {"light": .04, "medium": .065, "bold": .09}}

# --------------------------------------------------------------------------------------------------------------- pictures (24 x 24, strokes only)
M: dict[str, str] = {
    "heart": "<path d='M12 20.5s-7.5-4.7-9.4-9.4A5.3 5.3 0 0 1 12 6.4a5.3 5.3 0 0 1 9.4 4.7C19.5 15.8 12 20.5 12 20.5z'/>",
    "leaf": "<path d='M5 19C5 10.5 10.5 4.5 20 4.5c0 9.5-6 14.5-15 14.5z'/><path d='M5 19L13 11'/>",
    "star": "<path d='M12 3.2l2.6 5.6 6.1.7-4.5 4.2 1.2 6-5.4-3-5.4 3 1.2-6-4.5-4.2 6.1-.7z'/>",
    "sparkle": "<path d='M12 2.5l2 7.5 7.5 2-7.5 2-2 7.5-2-7.5-7.5-2 7.5-2z'/>",
    "dot": "<circle cx='12' cy='12' r='2.6'/>",
    "ring": "<circle cx='12' cy='15' r='6'/><path d='M9 7.2l3-4 3 4-3 2.6z'/>",
    "flower": ("<circle cx='12' cy='12' r='2.4'/>" + "".join(f"<ellipse cx='12' cy='5.6' rx='2.6' ry='4' transform='rotate({a} 12 12)'/>" for a in range(0, 360, 72))),
    "daisy": ("<circle cx='12' cy='12' r='2'/>" + "".join(f"<ellipse cx='12' cy='5.4' rx='1.7' ry='4.2' transform='rotate({a} 12 12)'/>" for a in range(0, 360, 45))),
    "wave": "<path d='M2 12c2.5-5 5-5 7.5 0s5 5 7.5 0 3-3 5-2'/><path d='M2 17c2.5-5 5-5 7.5 0s5 5 7.5 0 3-3 5-2'/>",
    "stethoscope": "<path d='M6 3.5v6a4 4 0 0 0 8 0v-6M6 3.5H4.2M14 3.5h1.8M10 13.5v2.3a4.6 4.6 0 0 0 9.2 0V14'/><circle cx='19.2' cy='12' r='2'/>",
    "cross": "<path d='M12 3.5v17M7 8.5h10'/>",
    "pulse": "<path d='M2.5 12.5h4.5l2-6 3.5 12 2.5-8 1.5 2h5'/>",
    "pill": "<rect x='3.5' y='8.5' width='17' height='7' rx='3.5' transform='rotate(-35 12 12)'/><path d='M9.4 9.6l5.2 4.8' transform='rotate(0 12 12)'/>",
    "book": "<path d='M4 5.5A2 2 0 0 1 6 3.5h13v16H6.5A2.5 2.5 0 0 0 4 22z'/><path d='M8 7.5h7'/>",
    "pencil": "<path d='M4 20.5l1-4.5L16.5 4.5l3 3L8 19z'/><path d='M14 7l3 3'/>",
    "apple": "<path d='M12 7.5C10 5.4 5.8 6.4 5.8 11.4c0 4.8 3 9 6.2 9s6.2-4.2 6.2-9c0-5-4.2-6-6.2-3.9z'/><path d='M12 7.5c0-2 1.2-3.4 3.2-3.8'/>",
    "bulb": "<path d='M9 18.2h6M10 21h4M12 3a6 6 0 0 0-3.6 10.8c.9.8 1.1 1.7 1.1 2.4h5c0-.7.2-1.6 1.1-2.4A6 6 0 0 0 12 3z'/>",
    "coin": "<circle cx='12' cy='12' r='8.5'/><path d='M12 7.2v9.6M14.6 9.6c-.5-1-1.6-1.5-2.7-1.4-1.6.1-2.4 1.9-.9 2.8 1.3.8 3.4.8 3.6 2.4.1 1.5-1.8 2.3-3.3 1.9-.9-.2-1.5-.8-1.8-1.5'/>",
    "chart": "<path d='M4 4v16h16M8 16v-4M12 16V8M16 16v-6'/>",
    "dumbbell": "<path d='M6.5 7.5v9M3.5 10v4M17.5 7.5v9M20.5 10v4M6.5 12h11'/>",
    "lotus": "<path d='M12 20c-3.2-2-5.2-5-5.2-8.4 2 0 4 1 5.2 3 1.2-2 3.2-3 5.2-3 0 3.4-2 6.4-5.2 8.4z'/><path d='M12 15C10.8 11.8 10.8 8.2 12 5c1.2 3.2 1.2 6.8 0 10z'/><path d='M3 20h18'/>",
    "moon": "<path d='M19.5 14.5A8 8 0 1 1 9.5 4.5a6.2 6.2 0 0 0 10 10z'/>",
    "bottle": "<path d='M10 3h4v3l2 3v10.5a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V9l2-3z'/><path d='M8 13h8'/>",
    "paw": ("<circle cx='6.8' cy='10.4' r='1.7'/><circle cx='10.2' cy='6.2' r='1.7'/><circle cx='13.8' cy='6.2' r='1.7'/><circle cx='17.2' cy='10.4' r='1.7'/>"
            "<path d='M12 11.6c-3 0-5.3 3-4.2 5.2.7 1.3 2 1.6 4.2 1.6s3.5-.3 4.2-1.6C17.3 14.6 15 11.6 12 11.6z'/>"),
    "house": "<path d='M3.8 11.2L12 4l8.2 7.2M6 10v10h12V10M10 20v-5.2h4V20'/>",
    "sprout": "<path d='M12 21v-9M12 12C12 8 9 5.8 4.8 5.8c0 4 3 6.2 7.2 6.2zM12 14.5c0-3 2-5 6.2-5 0 3-2 5-6.2 5z'/>",
    "fork": "<path d='M7 3v6.5a2.2 2.2 0 0 0 4.4 0V3M9.2 3v18M17.4 3c-2.4 2-2.8 7.4 0 9.2V21'/>",
    "check": "<path d='M4 12.5l5 5L20 6'/>",
    "list": "<path d='M9 6.5h11M9 12h11M9 17.5h11M3.8 6.5l1 1 1.8-2M3.8 12l1 1 1.8-2M3.8 17.5l1 1 1.8-2'/>",
    "clock": "<circle cx='12' cy='12' r='8.5'/><path d='M12 7v5l3.2 2'/>",
    "dove": "<path d='M20.5 7c-2 .2-3.4 1-4.3 2.4C15.2 7 13 5.5 10.4 6 7.8 6.5 6 8.6 6 11.4c0 3.8 3 6.6 7 6.6 3.4 0 6.5-2 7.5-5.5M6 11.4L2.8 9.6M13 18l-1.5 3'/>",
    "branch": "<path d='M4 20C10 14 14 10 20 4'/><path d='M9 15c-1-3-3.2-4.4-5.4-4.4.2 2.8 2 4.4 5.4 4.4zM13 11c0-3 1.6-5 5-5.4 0 3-1.6 5-5 5.4z'/>",
}

# theme -> pictures used for the header row, the corner and the background tile (first three are the stars of the show)
THEMES: dict[str, tuple[str, ...]] = {
    "medical": ("stethoscope", "heart", "pulse", "cross", "pill"),
    "school": ("book", "pencil", "apple", "bulb", "star"),
    "money": ("coin", "chart", "leaf", "list", "star"),
    "wedding": ("ring", "heart", "flower", "dove", "sparkle"),
    "fitness": ("dumbbell", "heart", "clock", "pulse", "star"),
    "calm": ("lotus", "moon", "leaf", "heart", "sparkle"),
    "family": ("bottle", "heart", "moon", "star", "flower"),
    "pets": ("paw", "heart", "star", "leaf", "dot"),
    "garden": ("sprout", "flower", "leaf", "branch", "daisy"),
    "faith": ("cross", "dove", "book", "heart", "sparkle"),
    "home": ("house", "heart", "check", "list", "sparkle"),
    "food": ("fork", "leaf", "apple", "heart", "clock"),
    "focus": ("bulb", "check", "list", "clock", "sparkle"),
    "business": ("chart", "coin", "bulb", "check", "star"),
    "general": ("leaf", "heart", "star", "sparkle", "flower"),
}
NICHE_THEME = {"adhd": "focus", "teacher": "school", "personal_finance": "money", "wedding": "wedding", "student": "school", "nurse": "medical",
               "small_business": "business", "fitness": "fitness", "mindfulness": "calm", "new_mom": "family", "pet_owner": "pets", "gardening": "garden",
               "faith": "faith", "home": "home", "meal_planning": "food"}
_WORDS = [("pets", r"\bpets?\b|\bdogs?\b|\bcats?\b|puppy|puppies|kitten|horse"), ("medical", r"nurs|medic|health|doctor|care|hospital|therap|dental|pharm"), ("school", r"teach|school|class|educat|tutor|homeschool|librar"),
          ("money", r"money|budget|financ|debt|saving|invest|tax"), ("wedding", r"wedding|bride|bridal|engag|marriage"),
          ("fitness", r"fitness|\bgym|\brun(ning|ner|ners)?\b|workout|yoga|health coach|sport|personal train"), ("calm", r"mind|calm|medit|gratitude|selfcare|self-care|journal|wellness|relax"),
          ("family", r"mom|mum|parent|baby|toddler|family|mother"),
          ("garden", r"garden|plant|grow|flower|farm|allotment"), ("faith", r"faith|pray|church|bible|christ|devotion|scripture"),
          ("home", r"home|house|clean|declutter|organi[sz]|chore"), ("food", r"meal|food|recipe|cook|bake|kitchen|nutrition|diet"),
          ("focus", r"adhd|focus|productiv|habit|routine"), ("business", r"business|shop|seller|etsy|freelanc|entrepreneur|brand|marketing")]


def theme_for(niche_key: str = "", niche_text: str = "") -> str:
    """The picture theme for an audience: built-in audiences by key, anything else by the words in its description."""
    if niche_key in NICHE_THEME:
        return NICHE_THEME[niche_key]
    text = f"{niche_key} {niche_text}".lower()
    return next((t for t, pat in _WORDS if re.search(pat, text)), "general")


# --------------------------------------------------------------------------------------------------------------- settings
@dataclass(frozen=True)
class Decor:
    corner: str = NONE
    header: str = NONE
    background: str = NONE
    strength: str = "light"
    corner_at: str = "bottom-right"
    theme: str = "general"

    @property
    def active(self) -> bool:
        return any(v != NONE for v in (self.corner, self.header, self.background))

    def as_dict(self) -> dict:
        return {"corner": self.corner, "header": self.header, "background": self.background, "strength": self.strength,
                "corner_at": self.corner_at, "theme": self.theme}


def auto_number(value: str) -> int | None:
    """N of an `auto:N` background, or None for any other value."""
    if value.startswith("auto:") and value[5:].isdigit() and 1 <= int(value[5:]) <= AUTO_MAX:
        return int(value[5:])
    return None


def auto_recipe(n: int) -> dict:
    """What background number `n` is. The 36 patterns and 6 whole-page fills take turns; each lap changes the colours, the size of the repeat,
    the direction of lines and the arrangement (the pattern seed), so no two numbers look alike."""
    bases = [(k, False) for k in patterns.KINDS] + [(k, True) for k in FILLS]
    (base, fill), lap = bases[(n - 1) % len(bases)], (n - 1) // len(bases)
    r = {"n": n, "kind": base, "fill": fill, "index": lap % 4, "size": (9, 12, 15)[(lap // 4) % 3], "seed": n}
    if fill:
        r.update(angle=(0, 90, 45, 135)[lap % 4], space=(.9, 1.3, 1.8)[(lap // 4) % 3], src=("accent", "accent2", "soft")[(lap // 12) % 3],
                 fade=(180, 90, 135, 45)[lap % 4])
        if base == "solid":   # a single colour: vary how far it leans towards the accent so the lap still looks different
            r["lean"] = (1.0, .75, .55, .4)[lap % 4]
    return r


def background_pictures() -> tuple[str, ...]:
    """The pictures that can be repeated as a background (every picture an audience theme uses), e.g. stethoscope, heart, sprout."""
    return tuple(sorted({p for pics in THEMES.values() for p in pics}))


def choices() -> dict[str, tuple[str, ...]]:
    return {"corner": CORNER_STYLES, "header": HEADER_STYLES, "background": BACKGROUND_STYLES + tuple(PIC_PREFIX + p for p in background_pictures()), "strength": STRENGTHS, "corner_at": CORNER_AT, "theme": tuple(THEMES)}


def make(corner: str = "", header: str = "", background: str = "", strength: str = "", corner_at: str = "", theme: str = "",
         niche_key: str = "", niche_text: str = "", defaults: dict | None = None) -> Decor:
    """Validated settings. Empty values fall back to `defaults` (the `decor:` section of moneyhub.yaml), then to off / light / bottom-right.
    A theme is chosen from the audience unless one is given. Raises ValueError with the allowed values for a wrong one."""
    d = defaults or {}

    def pick(name: str, given: str, allowed: tuple[str, ...], default: str) -> str:
        v = (given or str(d.get(name) or "") or default).strip().lower()
        if name == "background" and v.startswith(PIC_PREFIX):
            if v[len(PIC_PREFIX):] not in background_pictures():
                raise ValueError(f"unknown background picture '{v[len(PIC_PREFIX):]}'. Choose from: {', '.join(background_pictures())}")
            return v
        if name == "background" and (v == "auto" or auto_number(v)):
            return v if v != "auto" else f"auto:{random.randint(1, AUTO_MAX)}"
        ok = (NONE, *allowed) if name in ("corner", "header", "background") else allowed     # a layer can be switched off
        if v not in ok:
            raise ValueError(f"unknown decoration {name} '{v}'. Choose from: {', '.join(ok)}" + (f", auto, auto:<1-{AUTO_MAX}>" if name == "background" else ""))
        return v
    return Decor(corner=pick("corner", corner, CORNER_STYLES, NONE), header=pick("header", header, HEADER_STYLES, NONE),
                 background=pick("background", background, BACKGROUND_STYLES, NONE), strength=pick("strength", strength, STRENGTHS, "light"),
                 corner_at=pick("corner_at", corner_at, CORNER_AT, "bottom-right"),
                 theme=pick("theme", theme, tuple(THEMES), theme_for(niche_key, niche_text)))


def from_options(options: dict, niche_key: str = "", niche_text: str = "", defaults: dict | None = None) -> Decor:
    return make(options.get("decor_corner", ""), options.get("decor_header", ""), options.get("decor_background", ""), options.get("decor_strength", ""),
                options.get("decor_corner_at", ""), options.get("decor_theme", ""), niche_key, niche_text, defaults)


def of(style: Style) -> Decor | None:
    """The decoration stored on a look, or None when the look has none."""
    d = (style.extra or {}).get("decor")
    return Decor(**d) if d and any(d.get(k, NONE) != NONE for k in ("corner", "header", "background")) else None


# --------------------------------------------------------------------------------------------------------------- drawing
def _uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def _icon(name: str, x: float, y: float, size: float, rot: float = 0, stroke: float = 1.5) -> str:
    s = size / 24
    return (f"<g transform='translate({x:.1f} {y:.1f}) rotate({rot:.1f} {size / 2:.1f} {size / 2:.1f}) scale({s:.4f})' stroke-width='{stroke / s:.2f}'>{M[name]}</g>")


def _svg(w: float, h: float, body: str, colour: str, opacity: float, extra: str = "") -> str:
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}' {extra}>"
            f"<g fill='none' stroke='{colour}' stroke-linecap='round' stroke-linejoin='round' opacity='{opacity}'>{body}</g></svg>")


def header_art(d: Decor, ink: str) -> str:
    """Small row of pictures for the title bar (SVG, 150 x 28)."""
    o = OPACITY["header"][d.strength]
    if d.header == "themed":
        pics = list(THEMES[d.theme][:3])
        body = "".join(_icon(n, 6 + i * 48, 2, 24, (-6, 4, -3)[i]) for i, n in enumerate(pics))
    elif d.header == "botanical":
        body = _icon("leaf", 8, 2, 24, -20) + _icon("sprout", 56, 2, 24) + _icon("leaf", 104, 2, 24, 20)
    elif d.header == "floral":
        body = _icon("daisy", 8, 3, 22) + _icon("flower", 54, 1, 26, 12) + _icon("daisy", 106, 3, 22, 30)
    elif d.header == "sparkles":
        body = _icon("sparkle", 10, 3, 22) + _icon("dot", 62, 8, 12) + _icon("sparkle", 96, 0, 28, 10) + _icon("dot", 134, 16, 8)
    elif d.header == "hearts":
        body = _icon("heart", 8, 4, 20, -8) + _icon("heart", 54, 1, 26, 4) + _icon("heart", 108, 5, 18, 10)
    else:   # waves
        body = _icon("wave", 0, 0, 28) + _icon("wave", 52, 0, 28) + _icon("wave", 104, 0, 28)
    return _svg(150, 28, body, ink, o)


def _branch() -> str:
    """A curved stem from the bottom-right corner of a 300 box, with a pair of leaves at intervals."""
    p = [(300, 300), (250, 250), (190, 190), (120, 60)]

    def at(t: float) -> tuple[float, float]:
        u = 1 - t
        return tuple(u ** 3 * p[0][k] + 3 * u * u * t * p[1][k] + 3 * u * t * t * p[2][k] + t ** 3 * p[3][k] for k in (0, 1))
    out = ["<path d='M300 300C250 250 190 190 120 60'/>"]
    n = 9
    for i in range(1, n + 1):
        t = i / (n + 1)
        (x, y), (x2, y2) = at(t), at(t + .01)
        heading = math.degrees(math.atan2(y2 - y, x2 - x))
        r = 26 - i * 1.5
        for side in (-1, 1):
            out.append(f"<ellipse cx='{x:.1f}' cy='{y:.1f}' rx='{r * .36:.1f}' ry='{r:.1f}' transform='translate({x:.1f} {y:.1f}) rotate({heading + 90 + side * 52:.1f}) "
                       f"translate({-x:.1f} {-y - r:.1f})'/>")
    return "".join(out)


def corner_art(d: Decor, ink: str, seed: int = 1) -> str:
    """SVG (300 x 300) of the corner flourish, drawn for the bottom-right corner and flipped for the others by `corner_css`."""
    rng = random.Random(seed)
    o = OPACITY["corner"][d.strength]
    s = d.corner
    if s == "botanical":
        body = _branch() + _icon("leaf", 196, 232, 40, -30, 3) + _icon("leaf", 246, 190, 34, 20, 3)
    elif s == "floral":
        body = (_icon("flower", 214, 214, 74, 0, 3) + _icon("daisy", 140, 236, 56, 25, 3) + _icon("daisy", 236, 134, 50, -15, 3) + _icon("flower", 118, 168, 40, 12, 3)
                + _icon("leaf", 168, 130, 34, -40, 3) + _icon("leaf", 90, 226, 34, 70, 3) + "<path d='M300 300C280 250 250 220 190 200' stroke-dasharray='1 9'/>")
    elif s == "waves":
        body = "".join(f"<circle cx='300' cy='300' r='{r}' {'stroke-dasharray=\"2 9\"' if i % 2 else ''}/>" for i, r in enumerate((60, 100, 140, 180, 220, 260)))
    elif s == "sparkles":
        pts = [(262, 258, 64), (190, 284, 34), (280, 176, 44), (140, 250, 28), (246, 100, 32), (186, 190, 46), (96, 280, 24), (286, 46, 20)]
        body = "".join(_icon("sparkle", x - sz / 2, y - sz / 2, sz, rng.uniform(-15, 15), 2.2) for x, y, sz in pts) + "".join(
            f"<circle cx='{x}' cy='{y}' r='3'/>" for x, y in ((228, 240), (276, 160), (150, 300), (300, 120)))
    elif s == "geometric":
        body = ("".join(f"<path d='M{300 - r} 300A{r} {r} 0 0 1 300 {300 - r}'/>" for r in (50, 90, 130, 170)) +
                "".join(f"<path d='M300 300L{300 - 230 * math.cos(math.radians(a)):.1f} {300 - 230 * math.sin(math.radians(a)):.1f}' stroke-dasharray='3 8'/>" for a in (15, 40, 65, 90 - 15)) +
                "".join(f"<circle cx='{300 - 215 * math.cos(math.radians(a)):.1f}' cy='{300 - 215 * math.sin(math.radians(a)):.1f}' r='4'/>" for a in range(8, 90, 12)))
    else:   # themed: the audience's pictures, large, along the diagonal
        pics = THEMES[d.theme]
        spots = [(206, 206, 84, -8), (120, 232, 58, 10), (232, 118, 58, -14), (62, 262, 36, 12), (262, 56, 36, 8)]
        body = "".join(_icon(pics[i % len(pics)], x, y, sz, rot, 3) for i, (x, y, sz, rot) in enumerate(spots)) + "".join(
            f"<circle cx='{x}' cy='{y}' r='3.2'/>" for x, y in ((170, 170), (120, 160), (170, 120), (90, 218)))
    return _svg(300, 300, body, ink, o)


def _bg_tile(d: Decor, pal: Palette, seed: int) -> str:
    """SVG for the page background: a repeating tile (patterns), a watercolour wash, or the audience's pictures scattered."""
    o = OPACITY["background"][d.strength]
    rec = _recipe(d)
    if rec:
        tile = patterns.pattern_tile(rec["kind"], pal, rec["seed"], rec["index"])
        return f"<svg xmlns='http://www.w3.org/2000/svg' width='1000' height='1000' viewBox='0 0 1000 1000'><g opacity='{o * 2.2:.3f}'>{tile}</g></svg>"
    if d.background == "watercolor":
        cols = [pal.accent, pal.accent2, pal.soft, pal.accent]
        rng = random.Random(seed)
        blobs = "".join(f"<ellipse cx='{cx}' cy='{cy}' rx='{rx}' ry='{ry}' fill='{c}' opacity='{a}' transform='rotate({rot} {cx} {cy})'/>"
                        for (cx, cy, rx, ry, a), c, rot in zip(((90, 110, 330, 250, 1), (780, 190, 300, 210, .8), (140, 940, 360, 260, .9), (800, 1010, 340, 240, 1),
                                                                (470, 560, 240, 160, .45), (700, 520, 180, 130, .35)), cols * 2, (rng.randint(-30, 30) for _ in range(6))))
        return f"<svg xmlns='http://www.w3.org/2000/svg' width='850' height='1100' viewBox='0 0 850 1100' preserveAspectRatio='none'><g opacity='{o * .8:.3f}'>{blobs}</g></svg>"
    if d.background.startswith(PIC_PREFIX):   # big thin-line pictures, drawn over the page like the corner art (see css)
        pic = d.background[len(PIC_PREFIX):]
        rng = random.Random(seed)
        spots = [(10, 20, 150), (215, 215, 160), (230, 15, 110), (20, 240, 120)]   # big and small ones, spaced so none touch
        body = "".join(_icon(pic, x, y, sz, rng.uniform(-22, 22), 1.3) for x, y, sz in spots)
        return _svg(400, 400, body, pal.accent, PIC_OPACITY[d.strength])
    if d.background == "themed":
        pics = THEMES[d.theme]
        rng = random.Random(seed)
        spots = [(40, 40), (200, 90), (110, 190), (300, 230), (60, 330), (250, 340)]
        body = "".join(_icon(pics[i % len(pics)], x, y, 38, rng.uniform(-25, 25), 2) for i, (x, y) in enumerate(spots))
        return _svg(400, 400, body, pal.accent, o * 2.4)
    kind = {"dots": "dots", "leaves": "leaves", "daisies": "daisies", "waves": "waves", "sparkles": "sparkles", "diamonds": "diamonds",
            "terrazzo": "terrazzo", "hearts": "hearts", "stars": "stars", "confetti": "confetti"}[d.background]
    tile = patterns.pattern_tile(kind, pal, seed, 0)
    return f"<svg xmlns='http://www.w3.org/2000/svg' width='1000' height='1000' viewBox='0 0 1000 1000'><g opacity='{o * 2.2:.3f}'>{tile}</g></svg>"


def _recipe(d: Decor) -> dict | None:
    n = auto_number(d.background)
    return auto_recipe(n) if n else None


def _kind(d: Decor) -> str:
    r = _recipe(d)
    return (r["kind"] if r["fill"] else "tile") if r else d.background


def _fill_colour(pal: Palette, d: Decor) -> str:
    """The colour of a whole-page background: the accent diluted to the chosen strength, or warm cream for `paper`."""
    r = _recipe(d)
    if _kind(d) == "paper":
        tone = PAPER_TONES[(r["n"] // 42) % len(PAPER_TONES)] if r else PAPER_TONES[0]
        return _mix(pal.paper, tone, {"light": .45, "medium": .6, "bold": .75}[d.strength])
    src = getattr(pal, r["src"]) if r and "src" in r else pal.accent
    return _mix(pal.paper, src, min(1.0, OPACITY["background"][d.strength] * 2.4 * (r or {}).get("lean", 1.0)))


def tint(pal: Palette, d: Decor) -> str:
    """The darkest colour the background layer can make the page (accent at the full opacity of the chosen strength). Used by the contrast check."""
    if d.background.startswith(PIC_PREFIX):
        return _mix(pal.paper, pal.accent, PIC_OPACITY[d.strength])
    if d.background == "floral":
        return _mix(pal.paper, pal.accent, FLORAL_OPACITY[d.strength])
    return _fill_colour(pal, d)


def _fill_css(pal: Palette, d: Decor) -> str:
    """The `.page::before` declarations of a whole-page background (WeasyPrint draws gradients and borders, but not filters or box-shadows)."""
    c, paper, kind = _fill_colour(pal, d), pal.paper, _kind(d)
    r = _recipe(d) or {}
    sp = r.get("space", 1.0)
    if kind in ("solid", "paper"):
        return f"background:{c};"
    if kind == "gradient":
        return f"background:linear-gradient({r.get('fade', 180)}deg,{c} 0%,{_mix(paper, c, .5)} 45%,{paper} 100%);"
    if kind == "grid":
        a = r.get("angle", 0)
        return (f"background-color:{paper};background-image:linear-gradient({a}deg,{c} 1px,transparent 1px),linear-gradient({a + 90}deg,{c} 1px,transparent 1px);"
                f"background-size:{1.1 * sp:.2f}em {1.1 * sp:.2f}em;")
    if kind == "stripes":
        w = 1.6 * sp
        return f"background:repeating-linear-gradient({r.get('angle', 90)}deg,{paper} 0,{paper} {w:.2f}em,{c} {w:.2f}em,{c} {2 * w:.2f}em);"
    return f"background:{paper};border:{1.3 * sp:.2f}em solid {c};box-sizing:border-box;"   # frame


def _corner_pos(at: str) -> list[tuple[str, str]]:
    """(css position, flip) for each corner art: the art is drawn for the bottom-right corner, so the other corners are flips of it."""
    return {"bottom-right": [("right bottom", "")], "top-right": [("right top", "y")], "bottom-left": [("left bottom", "x")], "top-left": [("left top", "xy")],
            "opposite": [("right bottom", ""), ("left top", "xy")]}[at]


def floral_art(pal: Palette, seed: int, strength: str, flip: str = "") -> str:
    """A bouquet for the top-left corner of a 300 x 300 square (flip 'x', 'y' or 'xy' for the others): big filled blooms, buds and leaves."""
    rng = random.Random(seed)
    petal = [pal.accent2, pal.accent, _mix(pal.accent2, pal.paper, .45), _mix(pal.accent, pal.paper, .5)]
    leaf = [pal.accent, _mix(pal.accent, pal.accent2, .5)]
    out: list[str] = []

    def bloom(cx, cy, r, n, k):
        rot = rng.uniform(0, 360)
        for ring, (scale, col) in enumerate(((1.0, petal[k % 4]), (.62, petal[(k + 2) % 4]))):
            for i in range(n):
                a = rot + ring * 180 / n + i * 360 / n
                out.append(f"<ellipse cx='{cx:.1f}' cy='{cy - r * .55 * scale:.1f}' rx='{r * .34 * scale:.1f}' ry='{r * .56 * scale:.1f}' fill='{col}' "
                           f"stroke='{pal.paper}' stroke-width='1.6' transform='rotate({a:.1f} {cx:.1f} {cy:.1f})'/>")
        out.append(f"<circle cx='{cx:.1f}' cy='{cy:.1f}' r='{r * .2:.1f}' fill='{pal.paper}' stroke='{leaf[0]}' stroke-width='2'/>")
        for i in range(7):
            a = i * 51.4 + rot
            out.append(f"<circle cx='{cx + r * .09 * math.cos(math.radians(a)):.1f}' cy='{cy + r * .09 * math.sin(math.radians(a)):.1f}' r='{r * .028:.1f}' fill='{leaf[0]}'/>")

    def sprig(x, y, length, ang, k):
        out.append(f"<g transform='translate({x:.1f} {y:.1f}) rotate({ang:.1f})'><path d='M0 0 Q{length * .5:.1f} {-length * .09:.1f} {length:.1f} 0' fill='none' stroke='{leaf[0]}' stroke-width='2.4'/>")
        for i in range(4):
            lx = length * (.2 + i * .2)
            for side in (-1, 1):
                out.append(f"<path d='M{lx:.1f} 0 q{length * .09:.1f} {side * length * .1:.1f} {length * .2:.1f} {side * length * .06:.1f} q{-length * .07:.1f} {-side * length * .02:.1f} {-length * .2:.1f} {-side * length * .06:.1f}z' fill='{leaf[(i + k) % 2]}' stroke='{pal.paper}' stroke-width='1'/>")
        out.append("</g>")

    sprig(8, 130, 150, rng.uniform(-6, 6) + 12, 0)
    sprig(130, 8, 150, rng.uniform(-6, 6) + 78, 1)
    sprig(10, 10, 170, 45, 0)
    for k, (cx, cy, r, n) in enumerate(((86, 92, 66, 7), (172, 48, 40, 6), (46, 188, 42, 6), (146, 150, 30, 5), (212, 108, 22, 5), (96, 236, 20, 5))):
        bloom(cx + rng.uniform(-6, 6), cy + rng.uniform(-6, 6), r, n, k)
    sx, sy = (-1 if "x" in flip else 1), (-1 if "y" in flip else 1)
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300' viewBox='0 0 300 300'><g opacity='{FLORAL_OPACITY[strength]}' "
            f"transform='translate({300 if sx < 0 else 0} {300 if sy < 0 else 0}) scale({sx} {sy})'>{''.join(out)}</g></svg>")


def _flip(svg: str, how: str) -> str:
    if not how:
        return svg
    sx, sy = (-1 if "x" in how else 1), (-1 if "y" in how else 1)
    return svg.replace("<g fill=", f"<g transform='translate({300 if sx < 0 else 0} {300 if sy < 0 else 0}) scale({sx} {sy})' fill=", 1)


def css(style: Style, page=None) -> str:
    """The stylesheet that draws the layers behind every page and in every title bar. Empty when the look has no decoration."""
    d = of(style)
    if not d:
        return ""
    pal = style.palette
    out = []
    if d.corner != NONE:    # on top of the page (cards would hide it), but only a faint line drawing, so it never gets in the way of writing or reading
        imgs = [f"url('{_uri(_flip(corner_art(d, pal.accent, style.seed), how))}')" for _, how in _corner_pos(d.corner_at)]
        out.append(".page{z-index:0;}\n.page::after{content:'';position:absolute;top:0;left:0;right:0;bottom:0;z-index:2;"
                   f"background-image:{','.join(imgs)};background-position:{','.join(p for p, _ in _corner_pos(d.corner_at))};"
                   f"background-size:{','.join(['24em 24em'] * len(imgs))};background-repeat:no-repeat;}}")
    rec = _recipe(d)
    if d.background == "floral":   # bouquets in the corners, over the page so the white writing boxes do not hide them; light enough to write on
        corners = [("left top", "", 21), ("right bottom", "xy", 32), ("right top", "x", 15), ("left bottom", "y", 24)]
        imgs = [f"url('{_uri(floral_art(pal, style.seed + k, d.strength, how))}')" for k, (_, how, _) in enumerate(corners)]
        out.append(".page{z-index:0;}\n.page::before{content:'';position:absolute;top:0;left:0;right:0;bottom:0;z-index:2;"
                   f"background-image:{','.join(imgs)};background-position:{','.join(c[0] for c in corners)};"
                   f"background-size:{','.join(f'{c[2]}em {c[2]}em' for c in corners)};background-repeat:no-repeat;}}")
    elif _kind(d) in FILLS:   # behind everything; cards keep their own white, so writing areas stay clean
        out.append(".page{z-index:0;}\n.page::before{content:'';position:absolute;top:0;left:0;right:0;bottom:0;z-index:-1;" + _fill_css(pal, d) + "}")
    elif d.background != NONE:
        if d.background == "watercolor":
            size, rep = "100% 100%", "no-repeat"
        elif d.background == "themed":
            size, rep = "9em 9em", "repeat"
        elif d.background.startswith(PIC_PREFIX):
            size, rep = "22em 22em", "repeat"
        else:
            size, rep = f"{rec['size'] if rec else 12}em {rec['size'] if rec else 12}em", "repeat"
        out.append(".page{z-index:0;}\n.page::before{content:'';position:absolute;top:0;left:0;right:0;bottom:0;"
                   f"z-index:{2 if d.background.startswith(PIC_PREFIX) else -1};"
                   f"background-image:url('{_uri(_bg_tile(d, pal, style.seed))}');background-position:0 0;background-size:{size};background-repeat:{rep};}}")
    if d.header != NONE:
        band = style.header == "band"
        art = header_art(d, pal.accent_ink if band else pal.accent)
        out.append(f".hdr .hdr-art{{flex:1 1 auto;align-self:stretch;min-width:7em;max-width:15em;margin:0 1.2em;background:url('{_uri(art)}') center center / contain no-repeat;}}")
    return "\n".join(out)


def ink_note(d: Decor | None) -> str:
    """One sentence for the listing and the Start-Here page when the background uses extra ink (empty when it does not)."""
    if not d or d.background == NONE:
        return ""
    return ("This design has a decorative background, which uses more ink than plain pages. To save ink, print in grayscale or draft/economy mode, "
            "or ask your print shop for a light-coverage setting.")


def describe(d: Decor) -> str:
    """One plain sentence for the feature list: what decoration the pages have."""
    bits = []
    if d.corner != NONE:
        bits.append(f"faint {d.corner} corner art" if d.corner != "themed" else "faint themed corner art")
    if d.header != NONE:
        bits.append("small pictures in the title bar" if d.header != "themed" else "small themed pictures in the title bar")
    if d.background != NONE:
        bits.append({"watercolor": "a pale watercolour background", "solid": "a soft colour background", "gradient": "a soft colour fade background",
                     "grid": "a graph-paper grid background", "stripes": "a soft striped background", "frame": "a coloured page border",
                     "paper": "a cream paper background", "floral": "large flower bouquets in the page corners"}.get(_kind(d), f"a pale background of repeated {d.background[len(PIC_PREFIX):]} pictures" if d.background.startswith(PIC_PREFIX) else "a pale decorative background"))
    return "Decorated pages: " + ", ".join(bits) if bits else ""
