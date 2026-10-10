"""Activity pages for children's books: mazes (always solvable, with a solution), dot-to-dot, letter and number tracing, and odd-one-out.
Everything is a 1000 x 1000 SVG in the same bold black line style as kidsart.py."""
from __future__ import annotations

import math
import random

from . import cutfiles, kidsart

INK = kidsart.INK
FONT = "font-family='Helvetica, Arial, sans-serif' font-weight='800'"
LEVELS = {"toddler": dict(maze=(5, 6), dots=12, stroke=14, count=5, letters=6), "kids": dict(maze=(9, 11), dots=22, stroke=10, count=9, letters=10),
          "big": dict(maze=(15, 19), dots=38, stroke=7, count=12, letters=26)}
LETTER_PICS = {"A": "apple", "B": "bear", "C": "cat", "D": "dino", "E": "elephant", "F": "fish", "G": "giraffe", "H": "house", "I": "icecream", "J": "jellyfish",
               "K": "kite", "L": "lion", "M": "mushroom", "O": "owl", "P": "pizza", "R": "rocket", "S": "snail", "T": "turtle", "U": "umbrella", "W": "whale"}
LETTER_WORDS = {"apple": "apple", "bear": "bear", "cat": "cat", "dino": "dinosaur", "elephant": "elephant", "fish": "fish", "giraffe": "giraffe", "house": "house",
                "icecream": "ice cream", "jellyfish": "jellyfish", "kite": "kite", "lion": "lion", "mushroom": "mushroom", "owl": "owl", "pizza": "pizza", "rocket": "rocket",
                "snail": "snail", "turtle": "turtle", "umbrella": "umbrella", "whale": "whale"}


def _wrap(inner: str) -> str:
    return f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 1000' preserveAspectRatio='xMidYMid meet'>{inner}</svg>"


# --------------------------------------------------------------------------- mazes
def maze_cells(cols: int, rows: int, seed: int) -> tuple[set[tuple[int, int, int, int]], list[tuple[int, int]]]:
    """(open passages as (x1, y1, x2, y2), solution path from the top-left to the bottom-right cell). Depth-first carving makes a perfect maze."""
    rng = random.Random(seed)
    seen = {(0, 0)}
    stack = [(0, 0)]
    passages: set[tuple[int, int, int, int]] = set()
    while stack:
        x, y = stack[-1]
        nb = [(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= x + dx < cols and 0 <= y + dy < rows and (x + dx, y + dy) not in seen]
        if not nb:
            stack.pop()
            continue
        nx, ny = rng.choice(nb)
        passages.add((x, y, nx, ny))
        seen.add((nx, ny))
        stack.append((nx, ny))
    adj: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for a, b, c, d in passages:
        adj.setdefault((a, b), []).append((c, d))
        adj.setdefault((c, d), []).append((a, b))
    prev = {(0, 0): None}
    queue = [(0, 0)]
    for cur in queue:
        for n in adj.get(cur, []):
            if n not in prev:
                prev[n] = cur
                queue.append(n)
    path, cur = [], (cols - 1, rows - 1)
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    return passages, path[::-1]


def maze_svg(level: str, seed: int, solution: bool = False, box: tuple[int, int, int, int] = (50, 50, 900, 900)) -> str:
    cols, rows = LEVELS[level]["maze"]
    w = LEVELS[level]["stroke"] * (1 if not solution else .6)
    x0, y0, bw, bh = box
    cell = min(bw / cols, bh / rows)
    ox, oy = x0 + (bw - cell * cols) / 2, y0 + (bh - cell * rows) / 2
    passages, path = maze_cells(cols, rows, seed)
    open_ = {frozenset(((a, b), (c, d))) for a, b, c, d in passages}
    seg = []
    for x in range(cols + 1):
        for y in range(rows):
            if x in (0, cols) or frozenset(((x - 1, y), (x, y))) not in open_:
                if x == 0 and y == 0:   # entrance
                    continue
                if x == cols and y == rows - 1:   # exit
                    continue
                seg.append(f"M{ox + x * cell:.1f} {oy + y * cell:.1f} V{oy + (y + 1) * cell:.1f}")
    for y in range(rows + 1):
        for x in range(cols):
            if y in (0, rows) or frozenset(((x, y - 1), (x, y))) not in open_:
                seg.append(f"M{ox + x * cell:.1f} {oy + y * cell:.1f} H{ox + (x + 1) * cell:.1f}")
    out = [f"<path d='{' '.join(seg)}' fill='none' stroke='{INK}' stroke-width='{w}' stroke-linecap='round'/>"]
    if solution:
        pts = " ".join(f"{ox + (cx + .5) * cell:.1f},{oy + (cy + .5) * cell:.1f}" for cx, cy in path)
        out.append(f"<polyline points='{pts}' fill='none' stroke='{INK}' stroke-width='{max(w * 2.2, 5)}' stroke-linecap='round' stroke-linejoin='round' stroke-dasharray='1 {max(w * 3, 9)}'/>")
    else:
        fs = max(cell * .7, 40)
        out.append(f"<text x='{ox - 8:.0f}' y='{oy + cell * .5 + fs * .3:.0f}' text-anchor='end' font-size='{fs * .75:.0f}' {FONT} fill='{INK}'>START</text>" if ox > 150 else "")
        out.append(f"<text x='{ox + cols * cell + 8:.0f}' y='{oy + (rows - .5) * cell + fs * .3:.0f}' font-size='{fs * .75:.0f}' {FONT} fill='{INK}'>END</text>" if ox + cols * cell < 850 else "")
    return "".join(out)


def maze_page(level: str, seed: int) -> str:
    cols, rows = LEVELS[level]["maze"]
    inner = maze_svg(level, seed, box=(150, 90, 700, 820))
    return _wrap(inner + f"<text x='140' y='985' font-size='44' {FONT} fill='{INK}'>START</text><text x='700' y='985' font-size='44' {FONT} fill='{INK}'>FINISH</text>")


def maze_answers(level: str, seeds: list[int]) -> str:
    """Up to four solved mazes on one page."""
    boxes = [(30, 30, 440, 440), (530, 30, 440, 440), (30, 530, 440, 440), (530, 530, 440, 440)]
    return _wrap("".join(maze_svg(level, s, solution=True, box=b) for s, b in zip(seeds, boxes)))


# --------------------------------------------------------------------------- dot to dot
def _spiky(ring) -> bool:
    """True for outlines that are not near-circles (a ring of dots round a circle is a dull picture)."""
    r = [math.hypot(x - 500, y - 500) for x, y in ring]
    return (max(r) - min(r)) / (sum(r) / len(r)) > .12


def dot_page(level: str, seed: int) -> str:
    n = LEVELS[level]["dots"]
    designs = [d for d in cutfiles.make_designs(40, seed + 3) if len(d.rings[0]) > 20 and _spiky(d.rings[0])]
    d = designs[seed % len(designs)]
    ring = d.rings[0]
    pts = ring + [ring[0]]
    seglen = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(seglen)
    marks, acc, i = [], 0.0, 0
    for k in range(n):
        target = total * k / n
        while i < len(seglen) - 1 and acc + seglen[i] < target:
            acc += seglen[i]
            i += 1
        t = (target - acc) / (seglen[i] or 1)
        marks.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t))
    fs = 44 if n <= 24 else 34
    out = []
    for k, (x, y) in enumerate(marks, 1):
        cx, cy = 500 + (x - 500) * .9, 500 + (y - 500) * .9
        dx, dy = (x - 500), (y - 500)
        norm = math.hypot(dx, dy) or 1
        out.append(f"<circle cx='{cx:.0f}' cy='{cy:.0f}' r='{9 if n > 24 else 12}' fill='{INK}'/>")
        out.append(f"<text x='{cx + dx / norm * (fs * .95):.0f}' y='{cy + dy / norm * (fs * .95) + fs * .35:.0f}' font-size='{fs}' text-anchor='middle' {FONT} fill='{INK}'>{k}</text>")
    return _wrap("".join(out))


# --------------------------------------------------------------------------- tracing
def _dashed(text: str, x: float, y: float, size: float, w: float = 5, anchor: str = "middle") -> str:
    return (f"<text x='{x:.0f}' y='{y:.0f}' font-size='{size:.0f}' text-anchor='{anchor}' {FONT} fill='none' stroke='{INK}' stroke-width='{w}' "
            f"stroke-dasharray='2 {w * 2.4:.0f}' stroke-linejoin='round' stroke-linecap='round'>{text}</text>")


def letter_page(letter: str, seed: int, level: str) -> tuple[str, str]:
    pic = LETTER_PICS.get(letter)
    big = _dashed(letter, 330, 470, 470, 7) + _dashed(letter.lower(), 700, 470, 470, 7)
    rows = "".join(_dashed((letter + letter.lower()) * 2, 500, 665 + k * 130, 125, 4) + f"<line x1='80' y1='{655 + k * 130}' x2='920' y2='{655 + k * 130}' stroke='{INK}' stroke-width='3'/>" for k in range(3))
    out = big + rows
    if pic:
        out += f"<g transform='translate(20 10) scale(.22)'>{kidsart.figure(pic, seed, 16, True)}</g>"
        cap = f"{letter} is for {LETTER_WORDS[pic]}!"
    else:
        cap = f"Trace the letter {letter}!"
    return _wrap(out), cap


def number_page(n: int, seed: int, level: str) -> tuple[str, str]:
    kinds = kidsart.THEMES["mixed"][1]
    kind = kinds[(seed + n) % len(kinds)]
    out = _dashed(str(n), 500, 480, 520, 8)
    s = .2
    cols = 5
    rows = -(-max(n, 1) // cols)
    for i in range(n):
        cx = 500 + (i % cols - (min(n, cols) - 1) / 2) * 190
        cy = 640 + (i // cols) * 190 - (rows - 1) * 60
        out += f"<g transform='translate({cx - 500 * s:.0f} {cy - 500 * s:.0f}) scale({s})'>{kidsart.figure(kind, seed * 7 + i, 18, True)}</g>"
    return _wrap(out), f"Trace {n}, then color {n}!" if n else "Trace 0: none to color!"


# --------------------------------------------------------------------------- odd one out
def odd_page(seed: int, theme: str = "mixed") -> str:
    rng = random.Random(seed)
    pool = list(kidsart.THEMES.get(theme, kidsart.THEMES["mixed"])[1])
    out = []
    for r in range(4):
        a, b = rng.sample(pool, 2)
        odd = rng.randrange(4)
        for c in range(4):
            kind = b if c == odd else a
            s = .22
            x, y = 130 + c * 250, 120 + r * 240
            out.append(f"<g transform='translate({x - 500 * s:.0f} {y - 500 * s:.0f}) scale({s})'>{kidsart.figure(kind, seed * 11 + r * 4 + c, 22, True)}</g>")
        out.append(f"<line x1='20' y1='{228 + r * 240}' x2='980' y2='{228 + r * 240}' stroke='{INK}' stroke-width='3' stroke-dasharray='6 10'/>")
    return _wrap("".join(out))


def page_plan(i: int) -> str:
    return ["maze", "dots", "letter", "odd", "maze", "dots", "number", "letter", "dots", "odd"][i % 10]


def page_art(i: int, seed: int, level: str = "kids", theme: str = "mixed") -> tuple[str, str, str]:
    """(kind, svg, caption) for activity page i. Letters and numbers walk through the alphabet / 0-9 in order."""
    kind = page_plan(i)
    k = sum(1 for j in range(i) if page_plan(j) == kind)
    s = seed * 1009 + i * 31
    if kind == "maze":
        return kind, maze_page(level, s), "Help find the way out!"
    if kind == "dots":
        return kind, dot_page(level, s), "Connect the dots in order!"
    if kind == "letter":
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        svg, cap = letter_page(letters[k % 26], s, level)
        return kind, svg, cap
    if kind == "number":
        svg, cap = number_page(k % 10, s, level)
        return kind, svg, cap
    return kind, odd_page(s, theme), "Which one is different? Circle it!"
