"""Extra wall-art scene backgrounds drawn from the palette: moon phases, sunset, pampas, monstera, Bauhaus, mid-century, mountains, constellation,
line-art botanicals, fluid lines, cacti, palm leaves and citrus. Each is a 1000 x 1000 SVG with a transparent background (no AI, no key)."""
from __future__ import annotations

import math
import random

from .design import Palette

SCENES = ["moonphases", "sunset", "pampas", "monstera", "bauhaus", "midcentury", "mountains", "constellation", "lineleaves", "fluid", "cacti", "palm", "citrus"]


def _cols(p: Palette, on_dark: bool) -> tuple[str, str, str, str, str]:
    if on_dark:
        return p.paper, p.soft, p.accent2, p.line, p.paper
    return p.accent, p.accent2, p.soft, p.line, p.ink


def scene_svg(kind: str, p: Palette, seed: int, on_dark: bool = False) -> str:
    rng = random.Random(seed * 7 + 3)
    a, b, c, d, ink = _cols(p, on_dark)
    o: list[str] = []
    if kind == "moonphases":
        for i in range(5):
            cx = 130 + i * 185
            o.append(f"<circle cx='{cx}' cy='500' r='80' fill='none' stroke='{ink}' stroke-width='6'/>")
            if i == 4:
                o.append(f"<circle cx='{cx}' cy='500' r='80' fill='{b}'/>")
            elif i == 1:
                o.append(f"<path d='M{cx} 420 A80 80 0 0 1 {cx} 580 A55 80 0 0 0 {cx} 420Z' fill='{b}'/>")
            elif i == 2:
                o.append(f"<path d='M{cx} 420 A80 80 0 0 1 {cx} 580Z' fill='{b}'/>")
            elif i == 3:
                o.append(f"<path d='M{cx} 420 A80 80 0 0 1 {cx} 580 A50 80 0 0 1 {cx} 420Z' fill='{b}'/><circle cx='{cx}' cy='500' r='80' fill='none'/>")
        for _ in range(16):
            x, y, s = rng.uniform(40, 960), rng.uniform(180, 820), rng.uniform(6, 14)
            if abs(y - 500) < 120:
                continue
            o.append(f"<path d='M{x:.0f} {y - s:.0f} L{x + s * .3:.0f} {y - s * .3:.0f} L{x + s:.0f} {y:.0f} L{x + s * .3:.0f} {y + s * .3:.0f} L{x:.0f} {y + s:.0f} L{x - s * .3:.0f} {y + s * .3:.0f} L{x - s:.0f} {y:.0f} L{x - s * .3:.0f} {y - s * .3:.0f}Z' fill='{a}'/>")
    elif kind == "sunset":
        o.append(f"<circle cx='500' cy='470' r='260' fill='{b}'/>")
        o.append(f"<rect x='150' y='470' width='700' height='300' fill='#fff' opacity='0'/>")
        for i in range(7):
            y = 490 + i * 52
            o.append(f"<rect x='{200 - i * 6}' y='{y}' width='{600 + i * 12}' height='{12 + i * 5}' fill='{a if i % 2 == 0 else b}'/>")
        o.append(f"<path d='M120 478 H880' stroke='{ink}' stroke-width='7' stroke-linecap='round'/>")
    elif kind == "pampas":
        for k in range(5):
            x0 = 330 + k * 85 + rng.uniform(-15, 15)
            tip = (x0 + rng.uniform(-170, 170), rng.uniform(170, 330))
            o.append(f"<path d='M{x0:.0f} 930 Q{x0 + (tip[0] - x0) * .2:.0f} 620 {tip[0]:.0f} {tip[1]:.0f}' fill='none' stroke='{ink}' stroke-width='5'/>")
            for j in range(26):
                t = .25 + j / 26 * .75
                px = x0 + (tip[0] - x0) * t * t + 0
                py = 930 + (tip[1] - 930) * t
                ang = rng.uniform(-70, 70) + (tip[0] - x0) * .1
                o.append(f"<ellipse cx='{px + rng.uniform(-18, 18):.0f}' cy='{py:.0f}' rx='6' ry='{rng.uniform(26, 46):.0f}' fill='{a if j % 3 else b}' opacity='.85' transform='rotate({ang:.0f} {px:.0f} {py:.0f})'/>")
    elif kind == "monstera":
        o.append(f"<path d='M500 930 C500 800 510 700 500 560' fill='none' stroke='{ink}' stroke-width='12' stroke-linecap='round'/>")
        for k, ang in enumerate((-160, -125, -90, -55, -20, 20, 55, 90, 125, 160)):
            r = math.radians(ang)
            if ang in (90, 125, 55):
                continue
            cx, cy = 500 + 170 * math.cos(r), 400 + 170 * math.sin(r)
            o.append(f"<ellipse cx='{cx:.0f}' cy='{cy:.0f}' rx='62' ry='128' fill='{a if k % 2 else b}' transform='rotate({ang + 90} {cx:.0f} {cy:.0f})'/>")
        o.append(f"<circle cx='500' cy='420' r='120' fill='{a}'/>")
        for ang in (-150, -100, -50, 0, 50, 100, 150):
            r = math.radians(ang)
            o.append(f"<line x1='500' y1='420' x2='{500 + 90 * math.cos(r):.0f}' y2='{420 + 90 * math.sin(r):.0f}' stroke='{ink}' stroke-width='5' stroke-linecap='round' opacity='.7'/>")
    elif kind == "bauhaus":
        o.append(f"<circle cx='360' cy='360' r='210' fill='{a}'/>")
        o.append(f"<rect x='500' y='500' width='380' height='380' fill='{b}'/>")
        o.append(f"<path d='M120 880 A220 220 0 0 1 560 880 Z' fill='{c}'/>")
        o.append(f"<polygon points='620,120 880,120 880,400' fill='{ink}'/>")
        o.append(f"<circle cx='700' cy='690' r='84' fill='{p.paper if not on_dark else a}' stroke='{ink}' stroke-width='8'/>")
        o.append(f"<line x1='120' y1='600' x2='480' y2='600' stroke='{ink}' stroke-width='14'/><line x1='120' y1='640' x2='480' y2='640' stroke='{ink}' stroke-width='6'/>")
    elif kind == "midcentury":
        for i in range(12):
            r = math.radians(i * 30)
            o.append(f"<line x1='{300 + 40 * math.cos(r):.0f}' y1='{300 + 40 * math.sin(r):.0f}' x2='{300 + 160 * math.cos(r):.0f}' y2='{300 + 160 * math.sin(r):.0f}' stroke='{ink}' stroke-width='8' stroke-linecap='round'/>")
            o.append(f"<circle cx='{300 + 195 * math.cos(r):.0f}' cy='{300 + 195 * math.sin(r):.0f}' r='{12 if i % 2 else 8}' fill='{a if i % 2 else b}'/>")
        o.append(f"<circle cx='300' cy='300' r='34' fill='{b}'/>")
        o.append(f"<path d='M520 640 C600 520 760 560 820 680 C760 640 640 660 520 760 Z' fill='{a}'/>")
        o.append(f"<ellipse cx='700' cy='300' rx='120' ry='60' fill='{c}' transform='rotate(-24 700 300)'/>")
        o.append(f"<circle cx='260' cy='760' r='90' fill='none' stroke='{ink}' stroke-width='10'/><circle cx='260' cy='760' r='40' fill='{b}'/>")
        for k in range(4):
            o.append(f"<circle cx='{540 + k * 70}' cy='{880}' r='{10 + k * 3}' fill='{ink}'/>")
    elif kind == "mountains":
        o.append(f"<circle cx='700' cy='290' r='95' fill='{b}'/>")
        o.append(f"<polygon points='30,800 330,340 610,800' fill='{a}'/><polygon points='330,340 400,440 330,420 290,470 260,430' fill='{p.paper if not on_dark else b}'/>")
        o.append(f"<polygon points='330,800 640,420 970,800' fill='{c}'/><polygon points='640,420 700,500 650,485 610,520 585,490' fill='{p.paper if not on_dark else a}'/>")
        o.append(f"<rect x='20' y='790' width='960' height='60' fill='{d}'/>")
        for x, y in ((190, 250), (250, 220), (440, 210)):
            o.append(f"<path d='M{x} {y} q15 -14 30 0 q15 -14 30 0' fill='none' stroke='{ink}' stroke-width='5' stroke-linecap='round'/>")
    elif kind == "constellation":
        pts = [(rng.uniform(140, 860), rng.uniform(160, 840)) for _ in range(9)]
        pts.sort(key=lambda q: q[0])
        o.append(f"<polyline points='{' '.join(f'{x:.0f},{y:.0f}' for x, y in pts)}' fill='none' stroke='{ink}' stroke-width='4' stroke-dasharray='2 14' stroke-linecap='round'/>")
        for i, (x, y) in enumerate(pts):
            s = rng.choice([16, 24, 34])
            o.append(f"<path d='M{x:.0f} {y - s:.0f} Q{x:.0f} {y:.0f} {x + s:.0f} {y:.0f} Q{x:.0f} {y:.0f} {x:.0f} {y + s:.0f} Q{x:.0f} {y:.0f} {x - s:.0f} {y:.0f} Q{x:.0f} {y:.0f} {x:.0f} {y - s:.0f}Z' fill='{a if i % 2 else b}'/>")
        for _ in range(30):
            o.append(f"<circle cx='{rng.uniform(40, 960):.0f}' cy='{rng.uniform(60, 940):.0f}' r='{rng.uniform(2, 5):.1f}' fill='{ink}' opacity='.6'/>")
    elif kind == "lineleaves":
        for k in range(3):
            x0 = 280 + k * 220
            o.append(f"<path d='M{x0} 940 C{x0 - 30} 700 {x0 + 40} 500 {x0 + rng.uniform(-60, 60):.0f} 150' fill='none' stroke='{ink}' stroke-width='6' stroke-linecap='round'/>")
            for j in range(7):
                t = j / 7
                y = 840 - j * 100
                xs = x0 - 10 + (j % 2) * 20
                sd = 1 if j % 2 else -1
                o.append(f"<path d='M{xs} {y} q{sd * 70} -50 {sd * 120} {-10 - j * 4} q{-sd * 40} 50 {-sd * 120} {10 + j * 4}Z' fill='none' stroke='{ink}' stroke-width='5' stroke-linejoin='round'/>")
    elif kind == "fluid":
        for i in range(9):
            y = 150 + i * 90
            o.append(f"<path d='M40 {y} C260 {y - 130 + rng.uniform(-30, 30):.0f} 400 {y + 150} 560 {y} S820 {y - 160} 960 {y + 30}' fill='none' stroke='{[a, b, c, d][i % 4]}' stroke-width='{14 + (i % 3) * 8}' stroke-linecap='round'/>")
    elif kind == "cacti":
        for x, h, col in ((250, 460, a), (520, 600, b), (770, 380, c)):
            o.append(f"<rect x='{x - 55}' y='{900 - h}' width='110' height='{h - 80}' rx='55' fill='{col}'/>")
            o.append(f"<path d='M{x - 55} {900 - h * .5} h-60 a40 40 0 0 1 -40 -40 v-90' fill='none' stroke='{col}' stroke-width='54' stroke-linecap='round'/>")
            o.append(f"<path d='M{x + 55} {900 - h * .62} h60 a40 40 0 0 0 40 -40 v-70' fill='none' stroke='{col}' stroke-width='54' stroke-linecap='round'/>")
            o.append(f"<path d='M{x - 55} 830 h110 l-14 90 h-82 Z' fill='{ink}'/>")
            for j in range(3):
                o.append(f"<path d='M{x} {900 - h + 40 + j * 70} v34' stroke='{p.paper if not on_dark else ink}' stroke-width='4'/>")
    elif kind == "palm":
        o.append(f"<path d='M500 960 C520 800 480 600 500 430' fill='none' stroke='{ink}' stroke-width='16' stroke-linecap='round'/>")
        for fi, (ex, ey, bend) in enumerate(((120, 380, -120), (190, 190, -60), (360, 90, -10), (640, 90, 10), (810, 190, 60), (880, 380, 120), (240, 540, -80), (760, 540, 80))):
            n = 11
            for j in range(1, n):
                t = j / n
                x = (1 - t) ** 2 * 500 + 2 * t * (1 - t) * ((500 + ex) / 2 + bend * .3) + t * t * ex
                y = (1 - t) ** 2 * 430 + 2 * t * (1 - t) * (min(430, ey) - 60) + t * t * ey
                ang = math.degrees(math.atan2(ey - 430, ex - 500))
                ln = 62 * (1 - abs(t - .45) * 1.2)
                col = (a, b, c)[fi % 3]
                for sd in (-1, 1):
                    o.append(f"<ellipse cx='{x:.0f}' cy='{y:.0f}' rx='10' ry='{ln:.0f}' fill='{col}' transform='rotate({ang + 90 + sd * 55:.0f} {x:.0f} {y:.0f})'/>")
            o.append(f"<path d='M500 430 Q{(500 + ex) / 2 + bend * .3:.0f} {min(430, ey) - 60} {ex} {ey}' fill='none' stroke='{ink}' stroke-width='5'/>")
    elif kind == "citrus":
        for cx, cy, r, col in ((330, 360, 210, b), (660, 620, 190, a), (730, 270, 110, c)):
            o.append(f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='{col}'/><circle cx='{cx}' cy='{cy}' r='{r * .86:.0f}' fill='{p.paper if not on_dark else d}'/><circle cx='{cx}' cy='{cy}' r='{r * .78:.0f}' fill='{col}' opacity='.8'/>")
            for k in range(8):
                ar = math.radians(k * 45)
                o.append(f"<line x1='{cx}' y1='{cy}' x2='{cx + r * .8 * math.cos(ar):.0f}' y2='{cy + r * .8 * math.sin(ar):.0f}' stroke='{p.paper if not on_dark else d}' stroke-width='9'/>")
            o.append(f"<circle cx='{cx}' cy='{cy}' r='{r * .1:.0f}' fill='{p.paper if not on_dark else d}'/>")
        o.append(f"<path d='M470 120 C520 60 640 70 640 70 C610 140 520 160 470 120Z' fill='{ink}'/>")
    else:
        return ""
    return f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 1000'>{''.join(x for x in o if x)}</svg>"
