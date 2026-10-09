"""Artwork for tarot-style and oracle cards: a symbol (sun, moon, key, lotus...) drawn from simple shapes in the palette's colours, inside an arched
window with a starry sky. Every card is seeded, so the sky and small details differ from deck to deck. Cards are 600 x 760 SVGs."""
from __future__ import annotations

import math
import random

from .design import Palette

SYMBOLS = ["sun", "moon", "star", "eye", "key", "lotus", "infinity", "hourglass", "mountain", "wave", "flame", "tree", "feather", "heart", "scales", "lantern",
           "tower", "chalice", "crown", "door", "compass", "butterfly", "sprout", "rainbow", "wheel", "lovers", "world", "path"]


def mix(a: str, b: str, t: float) -> str:
    ra, rb = [int(a.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)], [int(b.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ra, rb))


class _P:
    def __init__(self, pal: Palette, rng: random.Random):
        self.pal, self.rng, self.o = pal, rng, []
        self.A, self.B, self.C = pal.accent, pal.accent2, mix(pal.paper, "#ffffff", .5)
        self.D, self.E = mix(pal.accent, "#ffffff", .5), mix(pal.accent2, "#ffffff", .45)
        self.ink = pal.ink

    def _st(self, fill, w=7):
        return f"fill='{fill}' stroke='{self.ink}' stroke-width='{w}' stroke-linejoin='round' stroke-linecap='round'"

    def c(self, cx, cy, r, fill=None, w=7):
        self.o.append(f"<circle cx='{cx:.1f}' cy='{cy:.1f}' r='{r:.1f}' {self._st(fill or self.C, w)}/>")

    def e(self, cx, cy, rx, ry, fill=None, rot=0, w=7):
        t = f" transform='rotate({rot} {cx:.0f} {cy:.0f})'" if rot else ""
        self.o.append(f"<ellipse cx='{cx:.1f}' cy='{cy:.1f}' rx='{rx:.1f}' ry='{ry:.1f}' {self._st(fill or self.C, w)}{t}/>")

    def p(self, d, fill=None, w=7):
        self.o.append(f"<path d='{d}' {self._st(fill or self.C, w)}/>")

    def l(self, d, w=7):
        self.o.append(f"<path d='{d}' fill='none' stroke='{self.ink}' stroke-width='{w}' stroke-linecap='round' stroke-linejoin='round'/>")

    def poly(self, pts, fill=None, w=7):
        self.o.append(f"<polygon points='{' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)}' {self._st(fill or self.C, w)}/>")

    def r(self, x, y, w, h, fill=None, rx=0, sw=7):
        self.o.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{w:.1f}' height='{h:.1f}' rx='{rx}' {self._st(fill or self.C, sw)}/>")

    def svg(self):
        return "".join(self.o)


def _star_pts(cx, cy, r, inner, n):
    return [(cx + (r if i % 2 == 0 else r * inner) * math.cos(math.radians(-90 + i * 180 / n)), cy + (r if i % 2 == 0 else r * inner) * math.sin(math.radians(-90 + i * 180 / n))) for i in range(n * 2)]


def _draw(kind: str, p: _P) -> str:
    A, B, C, D, E = p.A, p.B, p.C, p.D, p.E
    if kind == "sun":
        p.poly(_star_pts(300, 300, 215, .72, 12), B)
        p.c(300, 300, 125, A)
        p.c(300, 300, 85, D)
        p.l("M262 330 Q300 370 338 330")
        p.c(268, 285, 8, p.ink, 1)
        p.c(332, 285, 8, p.ink, 1)
    elif kind == "moon":
        p.p("M360 90 A215 215 0 1 0 360 510 A170 170 0 1 1 360 90 Z", B)
        p.c(430, 200, 16, D)
        p.poly(_star_pts(450, 380, 34, .45, 4), A)
        p.poly(_star_pts(215, 120, 24, .45, 4), D)
    elif kind == "star":
        p.poly(_star_pts(300, 300, 225, .42, 8), B)
        p.poly(_star_pts(300, 300, 135, .42, 8), A)
        p.c(300, 300, 34, C)
    elif kind == "eye":
        for k in range(9):
            a = math.radians(-160 + k * 20)
            p.l(f"M{300 + 175 * math.cos(a):.0f} {300 + 175 * math.sin(a):.0f} L{300 + 235 * math.cos(a):.0f} {300 + 235 * math.sin(a):.0f}")
        p.p("M60 300 Q300 90 540 300 Q300 510 60 300 Z", C)
        p.c(300, 300, 100, B)
        p.c(300, 300, 52, p.ink, 1)
        p.c(268, 270, 17, C, 1)
    elif kind == "key":
        p.c(300, 190, 105, B)
        p.c(300, 190, 50, C)
        p.r(272, 290, 56, 270, A, 14)
        for k, w in enumerate((100, 70)):
            p.r(328, 440 + k * 70, w, 38, A, 8)
    elif kind == "lotus":
        for ang, f in ((-64, D), (64, D), (-34, B), (34, B), (0, A)):
            t = math.radians(ang)
            p.e(300 + 150 * math.sin(t), 500 - 150 * math.cos(t), 62, 150, f, ang)
        p.l("M70 520 Q185 480 300 520 Q415 560 530 520")
        p.l("M120 568 Q210 535 300 568 Q390 600 480 568")
    elif kind == "infinity":
        p.l("M300 300 C215 175 70 175 70 300 C70 425 215 425 300 300 C385 175 530 175 530 300 C530 425 385 425 300 300 Z", 26)
        p.c(300, 300, 22, A)
        p.c(300, 130, 36, B)
        p.c(300, 470, 26, D)
    elif kind == "hourglass":
        p.r(120, 70, 360, 36, A, 10)
        p.r(120, 494, 360, 36, A, 10)
        p.poly([(150, 106), (450, 106), (320, 300), (450, 494), (150, 494), (280, 300)], C)
        p.poly([(190, 134), (410, 134), (312, 270), (288, 270)], B)
        p.poly([(180, 480), (420, 480), (350, 400), (250, 400)], B)
        p.l("M300 300 L300 400")
    elif kind == "mountain":
        p.c(430, 150, 62, B)
        p.poly([(40, 510), (230, 190), (420, 510)], A)
        p.poly([(250, 510), (400, 270), (560, 510)], D)
        p.poly([(230, 190), (194, 250), (230, 232), (262, 260)], C)
        p.poly([(400, 270), (372, 318), (402, 304), (428, 322)], C)
        p.r(20, 500, 560, 40, B, 8)
    elif kind == "wave":
        for k in range(4):
            y = 130 + k * 110
            p.p(f"M30 {y + 60} Q105 {y - 40} 180 {y + 60} T330 {y + 60} T480 {y + 60} T570 {y + 40} L570 {y + 130} L30 {y + 130} Z", [A, D, B, E][k])
        p.c(450, 110, 46, B)
    elif kind == "flame":
        p.p("M300 50 C380 170 500 240 480 380 C465 490 390 550 300 550 C210 550 135 490 120 380 C105 270 215 200 300 50 Z", B)
        p.p("M300 220 C350 290 420 330 405 410 C395 480 345 510 300 510 C255 510 205 480 195 410 C182 340 255 300 300 220 Z", A)
        p.p("M300 380 C325 410 355 430 348 465 C342 495 320 505 300 505 C280 505 258 495 252 465 C245 430 275 410 300 380 Z", C)
    elif kind == "tree":
        p.p("M270 540 L286 330 L314 330 L330 540 Z", mix(p.pal.accent2, "#000000", .35))
        for cx, cy, r, f in ((300, 200, 135, A), (190, 280, 100, D), (410, 280, 100, D), (300, 300, 95, B)):
            p.c(cx, cy, r, f)
        p.l("M120 548 L480 548")
    elif kind == "feather":
        p.p("M130 520 C60 330 190 120 440 70 C470 250 380 440 130 520 Z", B)
        p.l("M130 520 L430 90")
        for k in range(6):
            t = .15 + k * .13
            x, y = 130 + 300 * t, 520 - 430 * t
            p.l(f"M{x:.0f} {y:.0f} l-{70 - k * 6:.0f} -{5 + k * 3:.0f}")
            p.l(f"M{x:.0f} {y:.0f} l{25 + k * 6:.0f} {42 - k * 2:.0f}")
    elif kind == "heart":
        p.p("M300 530 C80 390 70 210 190 170 C250 150 290 190 300 230 C310 190 350 150 410 170 C530 210 520 390 300 530 Z", A)
        p.p("M300 440 C190 360 190 260 240 245 C270 237 292 258 300 290 C308 258 330 237 360 245 C410 260 410 360 300 440 Z", D)
    elif kind == "scales":
        p.l("M300 80 L300 520", 14)
        p.r(190, 510, 220, 36, A, 10)
        p.l("M150 170 L450 170", 12)
        for x in (150, 450):
            p.l(f"M{x} 170 L{x - 60} 330 M{x} 170 L{x + 60} 330")
            p.p(f"M{x - 85} 330 L{x + 85} 330 Q{x + 75} 405 {x} 405 Q{x - 75} 405 {x - 85} 330 Z", B)
        p.c(300, 100, 36, A)
    elif kind == "lantern":
        for k in range(8):
            a = math.radians(k * 45)
            p.l(f"M{300 + 175 * math.cos(a):.0f} {330 + 175 * math.sin(a):.0f} L{300 + 235 * math.cos(a):.0f} {330 + 235 * math.sin(a):.0f}")
        p.p("M240 130 Q300 40 360 130", "none", 10)
        p.r(250, 130, 100, 36, A, 8)
        p.r(220, 166, 160, 270, B, 30)
        p.e(300, 305, 46, 78, C)
        p.r(250, 436, 100, 36, A, 8)
    elif kind == "tower":
        p.r(210, 190, 180, 360, B, 6)
        for x in (210, 262, 314):
            p.r(x, 130, 56, 60, A, 4)
        for y in (260, 360):
            p.r(268, y, 64, 72, C, 30)
        p.poly([(110, 90), (160, 90), (130, 190), (176, 190), (100, 330), (112, 220), (72, 220)], D)
        p.r(150, 548, 300, 28, A, 8)
    elif kind == "chalice":
        p.p("M130 120 L470 120 C470 300 400 360 300 360 C200 360 130 300 130 120 Z", B)
        p.p("M150 160 L450 160 C440 190 440 190 430 220 L170 220 C160 190 160 190 150 160 Z", D, 4)
        p.r(278, 360, 44, 130, A, 10)
        p.e(300, 520, 120, 32, A)
        p.poly(_star_pts(300, 60, 34, .45, 4), A)
    elif kind == "crown":
        p.poly([(120, 470), (100, 190), (200, 310), (300, 120), (400, 310), (500, 190), (480, 470)], B)
        p.r(115, 470, 370, 70, A, 14)
        for cx, cy in ((100, 180), (300, 110), (500, 180)):
            p.c(cx, cy, 30, C)
        for x in (200, 300, 400):
            p.c(x, 505, 18, C, 5)
    elif kind == "door":
        p.p("M120 560 L120 260 A180 180 0 0 1 480 260 L480 560 Z", B)
        p.p("M170 560 L170 270 A130 130 0 0 1 430 270 L430 560 Z", C)
        p.p("M215 560 L215 280 A85 85 0 0 1 385 280 L385 560 Z", D)
        p.c(360, 430, 14, A)
        p.poly(_star_pts(300, 190, 36, .45, 4), A)
    elif kind == "compass":
        p.c(300, 300, 225, C)
        p.c(300, 300, 190, B)
        for k in range(16):
            a = math.radians(k * 22.5)
            r1, r2 = (190, 150) if k % 2 == 0 else (190, 170)
            p.l(f"M{300 + r1 * math.cos(a):.0f} {300 + r1 * math.sin(a):.0f} L{300 + r2 * math.cos(a):.0f} {300 + r2 * math.sin(a):.0f}", 5)
        p.poly([(300, 110), (345, 300), (300, 490), (255, 300)], A)
        p.poly([(110, 300), (300, 255), (490, 300), (300, 345)], D)
        p.c(300, 300, 28, C)
    elif kind == "butterfly":
        p.e(190, 230, 125, 165, A, -28)
        p.e(410, 230, 125, 165, A, 28)
        p.e(215, 400, 90, 115, B, 24)
        p.e(385, 400, 90, 115, B, -24)
        for x in (160, 440):
            p.c(x, 215, 34, C)
        p.e(300, 310, 28, 175, p.ink, 0, 5)
        p.l("M290 140 Q250 70 205 60")
        p.l("M310 140 Q350 70 395 60")
    elif kind == "sprout":
        p.p("M60 540 Q300 440 540 540 L540 580 L60 580 Z", mix(p.pal.accent2, "#000000", .35))
        p.l("M300 500 C300 400 300 330 300 250", 14)
        p.p("M300 330 C180 340 110 270 100 170 C220 160 290 220 300 330 Z", B)
        p.p("M300 270 C400 280 470 210 480 110 C370 105 310 165 300 270 Z", A)
    elif kind == "rainbow":
        for k, f in enumerate((A, B, D, E, C)):
            r = 250 - k * 42
            p.p(f"M{300 - r} 520 A{r} {r} 0 0 1 {300 + r} 520 L{300 + r - 42} 520 A{r - 42} {r - 42} 0 0 0 {300 - r + 42} 520 Z", f, 5)
        p.e(100, 540, 76, 36, C)
        p.e(500, 540, 76, 36, C)
    elif kind == "wheel":
        p.c(300, 300, 220, B)
        p.c(300, 300, 172, C)
        for k in range(8):
            a = math.radians(k * 45)
            p.l(f"M300 300 L{300 + 172 * math.cos(a):.0f} {300 + 172 * math.sin(a):.0f}", 9)
        p.c(300, 300, 48, A)
        for k in range(8):
            a = math.radians(k * 45 + 22.5)
            p.c(300 + 196 * math.cos(a), 300 + 196 * math.sin(a), 13, A, 5)
    elif kind == "lovers":
        p.c(220, 300, 170, B)
        p.c(380, 300, 170, A)
        p.p("M300 150 A170 170 0 0 1 300 450 A170 170 0 0 1 300 150 Z", D)
        p.poly(_star_pts(300, 300, 40, .45, 4), C)
    elif kind == "world":
        p.e(300, 300, 270, 100, "none", -24, 8)
        p.c(300, 300, 150, B)
        p.p("M215 250 Q260 190 330 215 Q300 275 245 310 Q200 300 215 250 Z", A, 5)
        p.p("M330 340 Q400 320 420 380 Q380 440 330 410 Z", A, 5)
        for x, y in ((90, 440), (500, 160), (520, 430), (80, 170)):
            p.c(x, y, 16, D)
    else:   # path
        p.c(430, 140, 54, B)
        p.p("M20 560 L580 560 L580 380 Q440 330 330 360 Q180 400 20 330 Z", D)
        p.p("M240 560 C200 470 380 430 300 360 C260 330 330 320 360 330 C400 370 270 430 350 470 C400 495 420 530 440 560 Z", C)
        p.poly(_star_pts(120, 120, 36, .45, 4), A)
    return p.svg()


def card_art(kind: str, pal: Palette, seed: int) -> str:
    """The picture on a card: an arched window, a starry sky and the symbol. 600 x 760 viewBox."""
    rng = random.Random(seed)
    sky = mix(pal.soft, pal.accent2, .12 + .18 * rng.random())
    stars = []
    for _ in range(22):
        x, y = rng.uniform(70, 530), rng.uniform(110, 690)
        if 150 < x < 450 and 200 < y < 640:   # keep the middle clear for the symbol
            continue
        s = rng.choice([5, 7, 9, 13])
        stars.append(f"<polygon points='{' '.join(f'{px:.0f},{py:.0f}' for px, py in _star_pts(x, y, s, .4, 4))}' fill='{pal.accent}' opacity='.8'/>")
    arch = "M40 730 L40 300 A260 260 0 0 1 560 300 L560 730 Z"
    ring = "M64 730 L64 300 A236 236 0 0 1 536 300 L536 730 Z"
    p = _P(pal, rng)
    sym = _draw(kind, p)
    return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 760'><path d='{arch}' fill='{sky}' stroke='{pal.accent}' stroke-width='8'/>"
            f"<path d='{ring}' fill='none' stroke='{pal.accent2}' stroke-width='3' opacity='.8'/>{''.join(stars)}"
            f"<clipPath id='arch'><path d='{arch}'/></clipPath><g clip-path='url(#arch)'><g transform='translate(0 120) scale(1)'>{sym}</g></g><path d='{arch}' fill='none' stroke='{pal.accent}' stroke-width='8'/></svg>")


def card_back(pal: Palette, seed: int, ratio: float = 760 / 600) -> str:
    """A matching card back: concentric star-and-ring pattern, drawn to the card's own shape (ratio = height / width)."""
    rng = random.Random(seed)
    h = round(600 * ratio)
    cy = h / 2
    o = [f"<rect width='600' height='{h}' fill='{pal.accent}'/>", f"<rect x='28' y='28' width='544' height='{h - 56}' rx='18' fill='none' stroke='{pal.paper}' stroke-width='5'/>"]
    for k in range(5):
        o.append(f"<circle cx='300' cy='{cy:.0f}' r='{60 + k * 48}' fill='none' stroke='{pal.paper if k % 2 == 0 else pal.accent2}' stroke-width='{4 if k % 2 == 0 else 8}' opacity='.9'/>")
    o.append(f"<polygon points='{' '.join(f'{x:.0f},{y:.0f}' for x, y in _star_pts(300, cy, 150, .38, 8))}' fill='{pal.paper}' stroke='{pal.accent2}' stroke-width='5'/>")
    o.append(f"<circle cx='300' cy='{cy:.0f}' r='34' fill='{pal.accent2}'/>")
    for _ in range(40):
        x, y = rng.uniform(55, 545), rng.uniform(55, h - 55)
        if math.hypot(x - 300, y - cy) < 270:
            continue
        o.append(f"<polygon points='{' '.join(f'{px:.0f},{py:.0f}' for px, py in _star_pts(x, y, rng.choice([7, 10, 14]), .4, 4))}' fill='{pal.paper}' opacity='.85'/>")
    return f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 600 {h}'>{''.join(o)}</svg>"
