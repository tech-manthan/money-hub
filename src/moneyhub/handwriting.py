"""Handwriting practice pages: print capitals and lower case with numbered start dots and arrows, joined cursive lower case, and word
tracing on three-line paper. Letters are stroke paths (not a font), so the start point and direction of every stroke can be shown.
Coordinates: x from 0, cap line y=20, x-height line y=50, baseline y=95, descenders to y=125."""
from __future__ import annotations

import math
import re

from .activities import FONT, INK, _wrap

CAP, XH, BASE, DESC = 20, 50, 95, 125

# print capitals: list of strokes (SVG path data), in writing order
UPPER = {
    "A": ["M30 20 L8 95", "M30 20 L52 95", "M16 68 H44"],
    "B": ["M12 20 V95", "M12 20 C54 16 54 58 12 57", "M12 57 C60 55 60 97 12 95"],
    "C": ["M52 36 C40 14 10 20 8 58 C8 94 40 100 52 78"],
    "D": ["M12 20 V95", "M12 20 C64 20 64 95 12 95"],
    "E": ["M12 20 V95", "M12 20 H50", "M12 57 H42", "M12 95 H50"],
    "F": ["M12 20 V95", "M12 20 H50", "M12 57 H42"],
    "G": ["M52 36 C40 14 10 20 8 58 C8 96 46 102 52 72 H32"],
    "H": ["M12 20 V95", "M48 20 V95", "M12 57 H48"],
    "I": ["M30 20 V95", "M18 20 H42", "M18 95 H42"],
    "J": ["M40 20 V74 C40 102 12 102 10 78", "M28 20 H52"],
    "K": ["M12 20 V95", "M50 20 L12 62", "M26 50 L52 95"],
    "L": ["M14 20 V95 H50"],
    "M": ["M10 20 V95", "M10 20 L30 70", "M30 70 L50 20", "M50 20 V95"],
    "N": ["M12 20 V95", "M12 20 L48 95", "M48 95 V20"],
    "O": ["M30 20 C4 20 4 95 30 95 C56 95 56 20 30 20 Z"],
    "P": ["M12 20 V95", "M12 20 C56 16 56 62 12 60"],
    "Q": ["M30 20 C4 20 4 95 30 95 C56 95 56 20 30 20 Z", "M34 72 L54 102"],
    "R": ["M12 20 V95", "M12 20 C56 16 56 58 12 58", "M28 58 L52 95"],
    "S": ["M50 32 C40 14 12 18 14 40 C16 62 50 54 50 78 C50 102 18 102 8 80"],
    "T": ["M30 20 V95", "M8 20 H52"],
    "U": ["M12 20 V70 C12 106 48 106 48 70 V20"],
    "V": ["M8 20 L30 95", "M30 95 L52 20"],
    "W": ["M4 20 L16 95", "M16 95 L30 40", "M30 40 L44 95", "M44 95 L56 20"],
    "X": ["M10 20 L50 95", "M50 20 L10 95"],
    "Y": ["M8 20 L30 58", "M52 20 L30 58", "M30 58 V95"],
    "Z": ["M10 20 H50 L10 95 H52"],
}
_BOWL = "M40 62 C30 48 8 54 8 74 C8 96 30 98 40 86"
LOWER = {
    "a": [_BOWL, "M42 50 V95"],
    "b": ["M12 20 V95", "M12 62 C22 48 46 54 46 74 C46 96 22 100 12 86"],
    "c": ["M42 60 C30 48 8 54 8 74 C8 96 30 98 42 88"],
    "d": [_BOWL, "M42 20 V95"],
    "e": ["M8 74 H44 C44 52 8 46 8 74 C8 98 34 100 44 88"],
    "f": ["M40 28 C30 14 16 20 18 40 V95", "M6 52 H34"],
    "g": [_BOWL, "M42 50 V108 C42 128 18 128 10 116"],
    "h": ["M12 20 V95", "M12 62 C16 50 42 48 42 66 V95"],
    "i": ["M25 50 V95", "M25 31 V33"],
    "j": ["M25 50 V110 C25 128 12 128 6 118", "M25 31 V33"],
    "k": ["M12 20 V95", "M42 50 L12 76", "M22 68 L44 95"],
    "l": ["M25 20 V95"],
    "m": ["M10 50 V95", "M10 64 C14 48 28 48 28 66 V95", "M28 64 C32 48 46 48 46 66 V95"],
    "n": ["M12 50 V95", "M12 64 C16 48 42 48 42 66 V95"],
    "o": ["M26 50 C6 50 6 96 26 96 C46 96 46 50 26 50 Z"],
    "p": ["M12 50 V125", "M12 62 C22 48 46 54 46 74 C46 96 22 100 12 86"],
    "q": [_BOWL, "M42 50 V125"],
    "r": ["M12 50 V95", "M12 66 C16 50 34 48 42 54"],
    "s": ["M40 58 C30 46 12 52 14 64 C16 78 40 74 40 88 C40 102 16 100 8 88"],
    "t": ["M22 28 V86 C22 96 32 98 40 92", "M8 52 H36"],
    "u": ["M12 50 V76 C12 100 40 100 42 76", "M42 50 V95"],
    "v": ["M8 50 L26 95", "M26 95 L44 50"],
    "w": ["M4 50 L14 95", "M14 95 L26 60", "M26 60 L38 95", "M38 95 L48 50"],
    "x": ["M10 50 L42 95", "M42 50 L10 95"],
    "y": ["M8 50 L26 95", "M44 50 L24 100 C16 120 8 124 2 120"],
    "z": ["M10 50 H42 L10 95 H44"],
}
# joined cursive lower case: one path from the entry (0, 95) to the exit (W, exit_y); extras are crossbars and dots
CURSIVE = {
    "a": ("M0 95 C8 80 16 56 28 52 C14 50 7 62 7 74 C7 88 16 96 28 96 C38 96 42 84 42 70 L42 52 C42 76 42 92 46 94 C50 96 54 95 58 95", 58, 95, []),
    "b": ("M0 95 C10 70 20 34 24 22 C28 12 18 12 20 40 C22 80 22 95 28 90 C38 62 56 64 54 82 C52 98 34 98 30 92 C38 96 52 96 58 95", 58, 95, []),
    "c": ("M0 95 C8 80 16 56 28 52 C14 50 7 62 7 74 C7 88 16 96 28 96 C36 96 40 92 44 88 C46 92 48 95 52 95", 52, 95, []),
    "d": ("M0 95 C8 80 16 56 28 52 C14 50 7 62 7 74 C7 88 16 96 28 96 C38 96 42 84 42 70 L44 20 L42 70 C42 84 42 92 46 94 C50 96 54 95 58 95", 58, 95, []),
    "e": ("M0 95 C10 84 22 70 30 60 C40 48 44 56 36 64 C28 70 16 70 12 72 C8 84 16 96 28 96 C38 96 44 94 50 95", 50, 95, []),
    "f": ("M0 95 C10 70 28 34 28 22 C28 10 18 14 20 38 L24 100 C24 128 6 126 8 112 C10 100 30 96 42 95", 42, 95, []),
    "g": ("M0 95 C8 80 16 56 28 52 C14 50 7 62 7 74 C7 88 16 96 28 96 C38 96 42 84 42 70 L42 52 L42 108 C42 128 20 130 14 116 C22 112 40 100 56 95", 56, 95, []),
    "h": ("M0 95 C10 70 20 34 24 22 C28 12 18 12 20 40 L22 80 C24 60 36 48 44 56 C50 62 38 78 40 90 C42 96 48 96 56 95", 56, 95, []),
    "i": ("M0 95 C8 80 14 62 18 52 C20 70 22 90 30 95 C36 95 40 95 44 95", 44, 95, ["M18 35 V37"]),
    "j": ("M0 95 C8 80 14 62 18 52 L22 110 C24 130 4 128 4 116 C14 112 30 100 40 95", 40, 95, ["M18 35 V37"]),
    "k": ("M0 95 C10 70 20 34 24 22 C28 12 18 12 20 40 L22 80 C22 60 36 50 40 56 C42 66 24 74 22 76 C34 80 40 92 52 95", 52, 95, []),
    "l": ("M0 95 C10 70 20 34 24 22 C28 12 16 12 18 40 L20 85 C24 100 36 96 44 95", 44, 95, []),
    "m": ("M0 95 C6 80 10 60 12 52 C10 70 12 94 16 92 C16 70 20 52 30 54 C34 56 26 80 30 92 C32 70 36 52 48 54 C52 56 44 80 48 92 C52 96 58 96 64 95", 64, 95, []),
    "n": ("M0 95 C6 80 10 60 12 52 C10 70 12 94 16 92 C16 70 20 52 30 54 C34 56 26 80 30 92 C34 96 40 96 46 95", 46, 95, []),
    "o": ("M0 95 C8 80 16 56 26 52 C14 50 7 62 7 74 C7 88 16 96 26 96 C36 96 42 84 42 72 C42 62 40 56 38 54 C42 54 46 53 50 52", 50, 52, []),
    "p": ("M0 95 C8 80 14 62 18 52 L20 125 L20 72 C22 54 40 50 48 64 C54 80 40 98 26 94 C22 92 22 90 22 88 C30 96 44 96 54 95", 54, 95, []),
    "q": ("M0 95 C8 80 16 56 28 52 C14 50 7 62 7 74 C7 88 16 96 28 96 C38 96 42 84 42 70 L42 52 L42 110 C42 128 62 130 62 114 C62 104 60 98 60 95", 60, 95, []),
    "r": ("M0 95 C8 80 14 62 18 52 L21 66 C25 58 31 52 40 52 L44 56 C42 70 44 86 50 92 C52 95 56 95 60 95", 60, 95, []),
    "s": ("M0 95 C8 84 14 66 20 52 C26 62 34 72 34 84 C34 98 18 98 18 90 C18 88 22 88 26 90 C34 94 44 95 52 95", 52, 95, []),
    "t": ("M0 95 C8 70 14 40 16 22 L20 78 C22 92 32 98 46 92", 46, 92, ["M4 52 H32"]),
    "u": ("M0 95 C6 80 10 60 12 52 C10 70 12 92 20 94 C32 96 34 66 36 52 C36 70 38 90 52 95", 52, 95, []),
    "v": ("M0 95 C6 80 10 60 12 52 C12 70 16 92 24 94 C34 90 40 60 46 52", 46, 52, []),
    "w": ("M0 95 C6 80 10 60 12 52 C12 70 16 92 24 94 C32 90 34 70 34 60 C34 74 38 92 46 94 C56 90 60 60 62 52", 62, 52, []),
    "x": ("M0 95 C8 80 12 60 14 52 C20 66 40 88 50 95", 50, 95, ["M44 52 C32 70 22 90 14 100"]),
    "y": ("M0 95 C6 80 10 60 12 52 C12 70 16 92 24 94 C32 90 34 70 36 52 L36 110 C36 130 14 128 14 116 C28 108 40 98 52 95", 52, 95, []),
    "z": ("M0 95 C8 80 14 62 18 52 L40 52 L16 90 C22 86 36 88 38 102 C40 118 18 124 14 110 C24 104 40 96 54 95", 54, 95, []),
}
WORDS = {"a": "am", "b": "bed", "c": "cat", "d": "dad", "e": "egg", "f": "fun", "g": "go", "h": "hat", "i": "it", "j": "jam", "k": "kid", "l": "log", "m": "mom",
         "n": "no", "o": "on", "p": "pig", "q": "quit", "r": "run", "s": "sun", "t": "top", "u": "up", "v": "van", "w": "win", "x": "box", "y": "yes", "z": "zoo"}
LETTERS = "abcdefghijklmnopqrstuvwxyz"
PRACTICE_WORDS = ["cat", "dog", "sun", "map", "red", "big", "hop", "pen", "bus", "fox", "cup", "bed", "mom", "dad", "hat", "pig", "jam", "van", "zip", "box",
                  "fun", "run", "sit", "yes", "top", "log"]


def _start_dir(d: str) -> tuple[tuple[float, float], float]:
    """First point of a path and the angle (degrees) it heads off in, for the stroke arrow."""
    m = re.match(r"\s*M\s*(-?[\d.]+)[ ,]+(-?[\d.]+)\s*(.*)", d)
    x0, y0 = float(m.group(1)), float(m.group(2))
    rest = m.group(3)
    t = re.match(r"([LHVCZ])\s*(.*)", rest)
    tx, ty = x0, y0 + 1
    if t:
        cmd, nums = t.group(1), [float(n) for n in re.findall(r"-?[\d.]+", t.group(2))]
        if cmd == "L" and len(nums) >= 2:
            tx, ty = nums[0], nums[1]
        elif cmd == "H" and nums:
            tx, ty = nums[0], y0
        elif cmd == "V" and nums:
            tx, ty = x0, nums[0]
        elif cmd == "C" and len(nums) >= 6:
            tx, ty = (nums[0], nums[1]) if (nums[0], nums[1]) != (x0, y0) else (nums[2], nums[3])
    return (x0, y0), math.degrees(math.atan2(ty - y0, tx - x0))


def glyph(strokes: list[str], x: float, y: float, s: float, mode: str = "guide", width: float = 5) -> str:
    """One letter at (x, y) = its top-left (cap line) corner, scaled by s. mode 'guide' = dashed strokes with numbered start dots and arrows,
    'trace' = dashed strokes only, 'solid' = a solid dark outline."""
    g = [f"<g transform='translate({x:.1f} {y - CAP * s:.1f}) scale({s:.3f})'>"]
    for i, d in enumerate(strokes):
        if mode == "solid":
            g.append(f"<path d='{d}' fill='none' stroke='{INK}' stroke-width='{width:.1f}' stroke-linecap='round' stroke-linejoin='round'/>")
        else:
            g.append(f"<path d='{d}' fill='none' stroke='#555' stroke-width='{width:.1f}' stroke-linecap='round' stroke-linejoin='round' stroke-dasharray='1 {width * 2.2:.1f}'/>")
    if mode == "guide":
        for i, d in enumerate(strokes):
            (px, py), ang = _start_dir(d)
            g.append(f"<g transform='translate({px:.1f} {py:.1f}) rotate({ang:.0f})'><path d='M-4 -9 L12 0 L-4 9 Z' fill='#d94b3d'/></g>")
            if len(strokes) > 1:
                g.append(f"<circle cx='{px - 9:.1f}' cy='{py - 9:.1f}' r='7' fill='#fff' stroke='#d94b3d' stroke-width='2'/>"
                         f"<text x='{px - 9:.1f}' y='{py - 5:.1f}' font-size='10' text-anchor='middle' {FONT} fill='#d94b3d'>{i + 1}</text>")
    g.append("</g>")
    return "".join(g)


def _lines(x1: float, x2: float, top: float, s: float, tall: bool = True) -> str:
    """Three-line writing guide: cap line, dashed mid line, baseline."""
    ys = {"top": top, "mid": top + (XH - CAP) * s, "base": top + (BASE - CAP) * s}
    out = [f"<line x1='{x1}' y1='{ys['top']:.0f}' x2='{x2}' y2='{ys['top']:.0f}' stroke='#9a9a9a' stroke-width='2'/>",
           f"<line x1='{x1}' y1='{ys['mid']:.0f}' x2='{x2}' y2='{ys['mid']:.0f}' stroke='#9a9a9a' stroke-width='2' stroke-dasharray='10 8'/>",
           f"<line x1='{x1}' y1='{ys['base']:.0f}' x2='{x2}' y2='{ys['base']:.0f}' stroke='{INK}' stroke-width='3'/>"]
    return "".join(out)


def cursive_width(word: str) -> float:
    return sum(CURSIVE[c][1] for c in word) + 8 * (len(word) - 1)


def cursive_word(word: str, x: float, y: float, s: float, mode: str = "trace", width: float = 5) -> str:
    """A joined cursive word: letters side by side with a small connecting stroke from each exit to the next entry."""
    g = [f"<g transform='translate({x:.1f} {y - CAP * s:.1f}) scale({s:.3f})'>"]
    cx = 0.0
    dash = "" if mode == "solid" else f" stroke-dasharray='1 {width * 2.2:.1f}'"
    col = INK if mode == "solid" else "#555"
    for k, ch in enumerate(word):
        d, w, ey, extras = CURSIVE[ch]
        g.append(f"<g transform='translate({cx:.1f} 0)'><path d='{d}' fill='none' stroke='{col}' stroke-width='{width}' stroke-linecap='round' stroke-linejoin='round'{dash}/>")
        for e in extras:
            g.append(f"<path d='{e}' fill='none' stroke='{col}' stroke-width='{width}' stroke-linecap='round'{dash}/>")
        if mode == "guide" and k == 0:
            g.append(f"<g transform='translate(0 95)'><path d='M-6 -9 L10 0 L-6 9 Z' fill='#d94b3d' transform='rotate(-70)'/></g>")
        g.append("</g>")
        if k < len(word) - 1:
            nx = cx + w + 8
            g.append(f"<path d='M{cx + w:.1f} {ey} C{cx + w + 4:.1f} {ey} {nx - 4:.1f} 95 {nx:.1f} 95' fill='none' stroke='{col}' stroke-width='{width}' stroke-linecap='round'{dash}/>")
        cx += w + 8
    g.append("</g>")
    return "".join(g)


# --------------------------------------------------------------------------- pages
def letter_page(n: int, seed: int, style: str = "print") -> tuple[str, str]:
    ch = LETTERS[n % 26]
    out = []
    w = WORDS[ch]
    if style == "print":
        up = ch.upper()
        big = 3.6
        out.append(_lines(60, 940, 60, big))
        out.append(glyph(UPPER[up], 150, 60, big, "guide", 4.4))
        out.append(glyph(LOWER[ch], 620, 60, big, "guide", 4.4))
        for top, strokes, step in ((470, UPPER[up], 66), (650, LOWER[ch], 56)):
            out.append(_lines(60, 940, top, 1.6))
            for k in range(3):
                out.append(glyph(strokes, 80 + k * (step * 1.6 + 36), top, 1.6, "trace", 3.4))
        out.append(_lines(60, 940, 830, 1.6))
        x = 80
        for c in w:
            out.append(glyph(LOWER[c], x, 830, 1.6, "trace", 3.4))
            x += 62 * 1.6
        cap = f"Trace the letter {up}{ch}. Follow the arrows and numbers, then write it yourself!"
    else:
        out.append(_lines(60, 940, 60, 3.6))
        out.append(cursive_word(ch, 190, 60, 3.6, "guide", 4.4))
        for top, txt in ((450, ch * 3), (640, w), (830, "")):
            out.append(_lines(60, 940, top, 1.75))
            if txt:
                out.append(cursive_word(txt, 90, top, 1.75, "trace", 3.4))
        cap = f"Trace the cursive letter {ch}, then the joined word {w}!"
    return _wrap("".join(out)), cap


def words_page(n: int, seed: int, style: str = "print") -> tuple[str, str]:
    words = [PRACTICE_WORDS[(n * 3 + k) % len(PRACTICE_WORDS)] for k in range(3)]
    out = []
    s = 1.3
    for k, w in enumerate(words):
        top = 40 + k * 330
        for row in range(2):
            out.append(_lines(50, 950, top + row * 160, s))
        if style == "print":
            x = 70
            for c in w:
                out.append(glyph(LOWER[c], x, top, s, "trace", 3.2))
                x += 62 * s
        else:
            out.append(cursive_word(w, 70, top, s, "trace", 3.2))
    return _wrap("".join(out)), "Trace each word, then write it again on the line below!"


def lined_page(n: int, seed: int, style: str = "print") -> tuple[str, str]:
    out = []
    for k in range(5):
        out.append(_lines(50, 950, 70 + k * 190, 1.45))
    return _wrap("".join(out)), "Practice writing: your own words and sentences!"
