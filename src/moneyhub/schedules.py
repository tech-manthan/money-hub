"""Flat, calm pictograms for visual schedules: daily routine steps and feelings faces, drawn from simple shapes with soft colours on a
1000 x 1000 box. Fixed drawings (no random variation) so a card always means the same thing."""
from __future__ import annotations

import math
import random

from .kidsart import Pen

SUN, BLUE, GREEN, RED = "#F7D86A", "#A9CCE8", "#B3D9A8", "#EA9A8E"
SKIN, WHITE, BROWN, PINK = "#F4CFB0", "#FFFFFF", "#CDAA82", "#F5BFD0"
GREY, PURPLE = "#DCDCDC", "#CBBDE8"


def _pen() -> Pen:
    return Pen(random.Random(0), 16, False)


def _rot_rect(p: Pen, cx: float, cy: float, w: float, h: float, deg: float, fill: str = WHITE) -> None:
    a = math.radians(deg)
    pts = []
    for x, y in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        pts.append((cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)))
    p.poly(pts, fill)


def _star(p: Pen, cx: float, cy: float, r: float, fill: str = SUN) -> None:
    pts = [(cx + (r if i % 2 == 0 else r * .45) * math.cos(math.radians(-90 + i * 36)), cy + (r if i % 2 == 0 else r * .45) * math.sin(math.radians(-90 + i * 36))) for i in range(10)]
    p.poly(pts, fill)


def wake_up(p):
    for i in range(10):
        a = math.radians(i * 36)
        p.line(f"M{500 + 260 * math.cos(a):.0f} {470 + 260 * math.sin(a):.0f} L{500 + 370 * math.cos(a):.0f} {470 + 370 * math.sin(a):.0f}")
    p.e(500, 470, 215, fill=SUN)
    p.eyes(420, 580, 440, 15)
    p.smile(500, 520, 70)


def brush_teeth(p):
    p.path("M250 280 C250 170 390 150 440 215 C490 150 630 170 630 280 C630 430 600 560 575 790 C565 850 500 850 490 770 C480 680 400 680 390 770 C380 850 315 850 305 790 C280 560 250 430 250 280 Z")
    p.line("M330 270 C335 230 370 215 400 230")
    _rot_rect(p, 770, 560, 90, 420, 28, BLUE)
    _rot_rect(p, 650, 300, 100, 150, 28, WHITE)
    p.line("M620 245 L660 330")
    p.line("M650 230 L690 315")


def wash_hands(p):
    p.band("M250 520 L250 230 Q250 150 340 150 L580 150 L580 270", 80)
    p.rect(520, 255, 120, 60, 20, GREY)
    for x, y in ((580, 390), (500, 460), (660, 480)):
        p.path(f"M{x} {y} C{x - 45} {y + 70} {x - 40} {y + 115} {x} {y + 115} C{x + 40} {y + 115} {x + 45} {y + 70} {x} {y} Z", BLUE)
    p.e(500, 800, 340, 110, fill=GREY)
    for x, y, r in ((330, 700, 55), (440, 650, 40), (600, 690, 60), (700, 640, 36)):
        p.e(x, y, r)


def get_dressed(p):
    p.path("M330 190 L430 160 Q500 235 570 160 L670 190 L810 340 L705 430 L665 380 L665 830 L335 830 L335 380 L295 430 L190 340 Z", BLUE)
    p.line("M430 160 Q500 235 570 160", 12)
    _star(p, 500, 560, 85, SUN)


def breakfast(p):
    for x in (390, 500, 610):
        p.line(f"M{x} 150 C{x - 40} 210 {x + 40} 250 {x} 320", 14)
    p.path("M170 450 L830 450 C830 700 680 830 500 830 C320 830 170 700 170 450 Z", PINK)
    p.e(500, 450, 330, 52, fill=WHITE)
    p.band("M840 250 L760 560", 40)
    p.e(865, 215, 60, 80, rot=12, fill=GREY)


def school(p):
    p.band("M380 260 C380 130 620 130 620 260", 40)
    p.rect(250, 230, 500, 620, 130, RED)
    p.rect(320, 520, 360, 260, 60, PINK)
    p.line("M320 400 L680 400")
    p.dot(500, 650, 20)


def play(p):
    p.e(380, 610, 210, fill=RED)
    p.line("M180 560 C300 640 460 640 580 560")
    p.line("M380 400 C330 520 330 700 380 820")
    p.rect(590, 560, 270, 270, 24, BLUE)
    p.rect(640, 320, 180, 180, 20, SUN)
    p.line("M700 410 L760 410")


def read(p):
    p.path("M500 300 C400 240 270 240 160 290 L160 790 C270 740 400 740 500 810 Z", WHITE)
    p.path("M500 300 C600 240 730 240 840 290 L840 790 C730 740 600 740 500 810 Z", WHITE)
    for y in (380, 460, 540, 620):
        p.line(f"M230 {y} L430 {y + 10}")
        p.line(f"M570 {y + 10} L770 {y}")
    p.line("M500 300 L500 810")
    p.poly([(640, 160), (700, 160), (700, 280), (670, 250), (640, 280)], RED)


def snack(p):
    p.line("M500 280 C500 220 530 170 580 140")
    p.path("M590 190 C650 120 760 130 790 180 C720 240 640 240 590 190 Z", GREEN)
    p.e(380, 560, 230, 250, fill=RED)
    p.e(620, 560, 230, 250, fill=RED)
    p.line("M330 440 C320 400 350 360 390 350", 12)


def lunch(p):
    p.e(500, 520, 330, 330, fill=WHITE)
    p.e(500, 520, 230, 230, fill=WHITE)
    p.poly([(340, 600), (660, 600), (500, 380)], SUN)
    p.line("M395 540 L605 540", 12)
    p.band("M130 360 L130 800", 36)
    p.band("M880 360 L880 800", 36)


def bath(p):
    p.path("M130 470 L870 470 C870 710 770 800 640 800 L360 800 C230 800 130 710 130 470 Z", BLUE)
    p.e(500, 470, 370, 50, fill=WHITE)
    p.rect(230, 800, 90, 60, 14, GREY)
    p.rect(680, 800, 90, 60, 14, GREY)
    for x, y, r in ((300, 320, 70), (430, 230, 45), (560, 310, 80), (690, 210, 50), (770, 350, 40)):
        p.e(x, y, r)


def bed(p):
    p.rect(120, 380, 80, 420, 24, PURPLE)
    p.rect(120, 560, 760, 150, 30, PURPLE)
    p.e(320, 520, 120, 60, fill=WHITE)
    p.rect(400, 500, 480, 170, 50, BLUE)
    p.rect(800, 710, 80, 110, 20, GREY)
    p.rect(120, 710, 80, 110, 20, GREY)


def sleep(p):
    p.path("M640 150 C430 170 300 340 340 550 C380 770 570 860 770 790 C580 750 490 580 530 420 C550 320 610 230 640 150 Z", SUN)
    _star(p, 790, 300, 70)
    _star(p, 860, 520, 45)
    _star(p, 250, 250, 50)
    p.line("M395 540 C430 560 460 560 490 540", 12)


def outside(p):
    p.rect(430, 500, 140, 340, 20, BROWN)
    p.e(500, 380, 270, 240, fill=GREEN)
    p.e(780, 150, 85, fill=SUN)
    p.line("M160 850 L840 850")


def toilet(p):
    p.rect(560, 130, 250, 320, 34, WHITE)
    p.e(780, 120, 30, 24, fill=GREY)
    p.path("M190 470 L770 470 C770 660 650 760 480 760 C310 760 190 660 190 470 Z", WHITE)
    p.e(480, 470, 300, 50, fill=GREY)
    p.rect(390, 760, 180, 100, 20, GREY)


def tidy(p):
    _star(p, 350, 350, 110, SUN)
    p.e(570, 360, 90, fill=RED)
    p.rect(660, 290, 130, 130, 14, BLUE)
    p.rect(160, 470, 680, 360, 36, BROWN)
    p.rect(120, 430, 760, 90, 30, BROWN)


def calm(p):
    p.path("M500 790 C130 540 200 210 390 240 C455 250 485 295 500 340 C515 295 545 250 610 240 C800 210 870 540 500 790 Z", PINK)
    p.line("M420 480 C460 520 540 520 580 480", 14)
    p.line("M380 410 C400 395 425 395 445 410", 12)
    p.line("M555 410 C575 395 600 395 620 410", 12)


def ride(p):
    p.rect(110, 280, 780, 400, 70, SUN)
    for x in (190, 380, 570):
        p.rect(x, 340, 150, 130, 18, BLUE)
    p.rect(750, 340, 90, 200, 18, BLUE)
    p.line("M110 570 L890 570")
    p.e(300, 690, 85, fill=GREY)
    p.e(700, 690, 85, fill=GREY)


def circle_time(p):
    p.e(500, 520, 380, 280, fill=BLUE)
    for i in range(6):
        a = math.radians(i * 60 - 90)
        x, y = 500 + 255 * math.cos(a), 520 + 175 * math.sin(a)
        p.e(x, y, 62, fill=SKIN)
        p.dot(x - 20, y - 8, 8)
        p.dot(x + 20, y - 8, 8)


def draw(p):
    p.rect(180, 330, 520, 480, 20, WHITE)
    _rot_rect(p, 740, 400, 90, 520, 28, SUN)
    p.poly([(620, 640), (680, 660), (610, 760)], SKIN)
    p.line("M260 460 C330 400 390 520 460 460 S580 460 620 480", 14)


def music(p):
    p.e(310, 700, 120, 85, rot=-20, fill=PURPLE)
    p.e(690, 620, 120, 85, rot=-20, fill=PURPLE)
    p.line("M400 670 L400 230 L780 130 L780 590", 24)
    p.line("M400 340 L780 240", 24)


def wait(p):
    p.e(500, 500, 350, fill=WHITE)
    for i in range(12):
        a = math.radians(i * 30)
        p.line(f"M{500 + 290 * math.cos(a):.0f} {500 + 290 * math.sin(a):.0f} L{500 + 330 * math.cos(a):.0f} {500 + 330 * math.sin(a):.0f}", 14)
    p.line("M500 500 L500 280", 24)
    p.line("M500 500 L650 590", 24)
    p.dot(500, 500, 28)


def drink(p):
    p.path("M290 230 L710 230 L650 800 C645 840 610 860 570 860 L430 860 C390 860 355 840 350 800 Z", WHITE)
    p.path("M312 420 L688 420 L650 800 C645 840 610 860 570 860 L430 860 C390 860 355 840 350 800 Z", BLUE)
    p.line("M690 330 C830 330 830 560 690 560", 40)
    p.line("M560 230 L620 90", 22)


def shoes(p):
    p.path("M180 360 C180 300 280 280 330 330 C380 420 500 450 640 470 C780 490 860 540 860 640 L860 720 L180 720 Z", RED)
    p.rect(180, 720, 680, 70, 24, WHITE)
    for x in (330, 400, 470):
        p.line(f"M{x} 380 L{x + 40} 420", 14)
    p.line("M200 560 L860 600", 12)


ROUTINE = {
    "wake_up": ("Wake up", wake_up), "brush_teeth": ("Brush teeth", brush_teeth), "wash_hands": ("Wash hands", wash_hands),
    "get_dressed": ("Get dressed", get_dressed), "breakfast": ("Breakfast", breakfast), "school": ("Go to school", school),
    "play": ("Play", play), "read": ("Read", read), "snack": ("Snack", snack), "lunch": ("Lunch", lunch), "bath": ("Bath", bath),
    "bed": ("Bed", bed), "sleep": ("Sleep", sleep), "outside": ("Go outside", outside), "toilet": ("Toilet", toilet),
    "tidy": ("Tidy up", tidy), "calm": ("Calm down", calm), "ride": ("Ride", ride), "circle_time": ("Circle time", circle_time),
    "draw": ("Draw", draw), "music": ("Music", music), "wait": ("Wait", wait), "drink": ("Drink", drink), "shoes": ("Shoes on", shoes),
}


# --------------------------------------------------------------------------- feelings faces
def _face(p: Pen, fill: str, eyes: str, brows: str, mouth: str, extra: str = "") -> None:
    p.e(500, 500, 380, fill=fill)
    E = {"dots": lambda: p.eyes(380, 620, 440, 22),
         "wide": lambda: [p.e(380, 430, 55, fill=WHITE), p.e(620, 430, 55, fill=WHITE), p.dot(380, 430, 18), p.dot(620, 430, 18)],
         "closed": lambda: [p.line("M320 440 Q380 500 440 440", 16), p.line("M560 440 Q620 500 680 440", 16)],
         "happyclosed": lambda: [p.line("M320 470 Q380 400 440 470", 16), p.line("M560 470 Q620 400 680 470", 16)],
         "side": lambda: [p.dot(340, 470, 20), p.dot(580, 470, 20)],
         "uneven": lambda: [p.e(380, 430, 40, fill=WHITE), p.dot(380, 430, 14), p.dot(620, 440, 22)]}
    E[eyes]()
    B = {"none": lambda: None,
         "sad": lambda: [p.line("M320 350 L440 320", 16), p.line("M680 350 L560 320", 16)],
         "angry": lambda: [p.line("M310 320 L440 370", 18), p.line("M690 320 L560 370", 18)],
         "up": lambda: [p.line("M320 320 Q380 270 440 320", 14), p.line("M560 320 Q620 270 680 320", 14)],
         "worried": lambda: [p.line("M320 330 L440 300", 14), p.line("M680 330 L560 300", 14)]}
    B[brows]()
    M = {"smile": lambda: p.smile(500, 640, 140),
         "grin": lambda: p.path("M340 620 Q500 800 660 620 Z", WHITE),
         "frown": lambda: p.line("M360 740 Q500 620 640 740", 18),
         "flat": lambda: p.line("M380 700 L620 700", 18),
         "small": lambda: p.line("M430 700 Q500 730 570 700", 16),
         "o": lambda: p.e(500, 700, 55, 70, fill=WHITE),
         "wavy": lambda: p.line("M370 700 q32 -36 65 0 t65 0 t65 0", 16),
         "tongue": lambda: [p.smile(500, 640, 140), p.e(560, 740, 45, 60, fill=RED)],
         "scared": lambda: p.e(500, 710, 70, 50, fill=WHITE)}
    M[mouth]()
    if extra == "tear":
        p.path("M360 520 C330 580 330 620 360 620 C390 620 390 580 360 520 Z", BLUE)
    elif extra == "blush":
        p.e(300, 580, 45, 28, fill=PINK)
        p.e(700, 580, 45, 28, fill=PINK)
    elif extra == "z":
        p.line("M760 140 L840 140 L760 220 L840 220", 14)


FEELINGS = {
    "happy": ("Happy", SUN, "dots", "none", "smile", ""), "sad": ("Sad", BLUE, "dots", "sad", "frown", "tear"),
    "angry": ("Angry", RED, "dots", "angry", "flat", ""), "scared": ("Scared", PURPLE, "wide", "up", "scared", ""),
    "tired": ("Tired", GREY, "closed", "none", "small", "z"), "excited": ("Excited", SUN, "wide", "up", "grin", ""),
    "calm": ("Calm", GREEN, "happyclosed", "none", "smile", ""), "worried": ("Worried", PURPLE, "dots", "worried", "wavy", ""),
    "surprised": ("Surprised", SUN, "wide", "up", "o", ""), "silly": ("Silly", PINK, "uneven", "none", "tongue", ""),
    "proud": ("Proud", GREEN, "happyclosed", "none", "grin", "blush"), "shy": ("Shy", PINK, "side", "none", "small", "blush"),
}


def _wrap(shapes: str) -> str:
    return f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 1000'>{shapes}</svg>"


def routine_card(key: str) -> tuple[str, str]:
    """(label, svg) for one routine step."""
    label, fn = ROUTINE[key]
    p = _pen()
    fn(p)
    return label, _wrap(p.svg())


def feeling_card(key: str) -> tuple[str, str]:
    label, fill, eyes, brows, mouth, extra = FEELINGS[key]
    p = _pen()
    _face(p, fill, eyes, brows, mouth, extra)
    return label, _wrap(p.svg())
