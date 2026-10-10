"""More children's figures for kidsart.py: seasonal (Halloween, Christmas, Easter), farm and pet animals, forest friends, fantasy, and more vehicles.
Same rules as the core figures: simple shapes, white fills, seeded details; `register()` adds them to the library and the themes."""
from __future__ import annotations

import math

from . import kidsart
from .kidsart import Pen, _bow, _star_pts

K = "#222222"   # filled black patches (panda, bat eyes); the sticker engine recolours it with the palette's ink


def pumpkin(p: Pen) -> str:
    r = p.rng
    p.rect(455, 190, 90, 150, 28)
    p.e(700, 260, 120, 46, -28)
    p.e(320, 590, 185, 270)
    p.e(680, 590, 185, 270)
    p.e(500, 590, 215, 285)
    p.poly([(380, 520), (460, 520), (420, 440)])
    p.poly([(540, 520), (620, 520), (580, 440)])
    p.poly([(475, 590), (525, 590), (500, 540)])
    p.path("M350 680 L405 740 L450 690 L500 750 L550 690 L595 740 L650 680 Q500 840 350 680 Z")
    return p.svg()


def ghost(p: Pen) -> str:
    r = p.rng
    p.path("M230 880 L230 430 C230 130 770 130 770 430 L770 880 L685 790 L595 880 L500 790 L405 880 L315 790 Z")
    p.e(400, 420, 52, 72)
    p.e(600, 420, 52, 72)
    p.dot(410, 430, 24)
    p.dot(610, 430, 24)
    p.e(500, 600, 52, 70)
    p.e(190, 560, 60, 36, 24)
    p.e(810, 560, 60, 36, -24)
    if r.random() < .6:
        p.e(330, 540, 30, 18, 0)
        p.e(670, 540, 30, 18, 0)
    return p.svg()


def bat(p: Pen) -> str:
    r = p.rng
    for s in (-1, 1):
        x = lambda v: 500 + s * (v - 500)   # noqa: E731
        p.path(f"M{x(560)} 470 C{x(700)} 280 {x(880)} 290 {x(950)} 400 Q{x(870)} 420 {x(860)} 520 Q{x(790)} 470 {x(740)} 580 Q{x(690)} 520 {x(560)} 620 Z")
    p.poly([(430, 330), (400, 170), (490, 280)])
    p.poly([(570, 330), (600, 170), (510, 280)])
    p.e(500, 560, 100, 190)
    p.e(500, 380, 105, 95)
    p.eyes(465, 535, 370, 18)
    p.poly([(475, 430), (490, 475), (500, 430)])
    p.poly([(500, 430), (510, 475), (525, 430)])
    p.line("M470 410 Q500 440 530 410")
    return p.svg()


def witchhat(p: Pen) -> str:
    r = p.rng
    p.path("M330 700 C360 480 420 300 520 170 C560 110 650 130 700 190 C640 170 620 200 610 260 C640 420 700 580 710 700 Z")
    p.rect(300, 640, 420, 70, 8)
    p.rect(470, 625, 80, 100, 10)
    p.e(500, 740, 440, 100)
    p.poly(_star_pts(500, 420, 52, .45))
    p.poly(_star_pts(640, 520, 30, .45))
    return p.svg()


def xmastree(p: Pen) -> str:
    r = p.rng
    p.rect(440, 760, 120, 140, 10)
    p.poly([(180, 780), (820, 780), (500, 520)])
    p.poly([(230, 590), (770, 590), (500, 340)])
    p.poly([(290, 420), (710, 420), (500, 170)])
    p.poly(_star_pts(500, 130, 70, .45))
    cols = [(380, 700), (610, 720), (500, 640), (430, 520), (580, 500), (500, 380), (470, 270)]
    for x, y in cols:
        p.e(x, y, 28)
    p.line("M300 740 Q500 800 700 740")
    return p.svg()


def snowman(p: Pen) -> str:
    r = p.rng
    p.e(500, 760, 230)
    p.e(500, 480, 170)
    p.e(500, 260, 125)
    p.rect(390, 90, 220, 100, 6)
    p.rect(330, 170, 340, 40, 10)
    p.line("M380 360 Q500 410 620 360", 40)
    p.line("M380 360 Q500 410 620 360")
    p.poly([(500, 255), (640, 280), (500, 300)])
    p.eyes(450, 550, 220, 14)
    for k in range(3):
        p.dot(500, 470 + k * 90, 18)
    p.line("M340 470 L190 380 M190 380 L170 330 M190 380 L130 390")
    p.line("M660 470 L810 380 M810 380 L830 330 M810 380 L870 390")
    for x, y in ((130, 200), (860, 150), (100, 760), (900, 690)):
        p.line(f"M{x - 25} {y} L{x + 25} {y} M{x} {y - 25} L{x} {y + 25} M{x - 18} {y - 18} L{x + 18} {y + 18} M{x - 18} {y + 18} L{x + 18} {y - 18}", p.w * .7)
    return p.svg()


def gift(p: Pen) -> str:
    r = p.rng
    p.rect(190, 470, 620, 420, 12)
    p.rect(150, 360, 700, 130, 12)
    p.rect(450, 360, 100, 530)
    p.e(380, 270, 135, 85, -20)
    p.e(620, 270, 135, 85, 20)
    p.e(500, 330, 55, 45)
    p.line("M500 320 Q470 190 430 150")
    p.line("M500 320 Q530 190 570 150")
    if not p.simple:
        p.spots((220, 520, 420, 860), 3, 20, 30)
        p.spots((580, 520, 780, 860), 3, 20, 30)
    return p.svg()


def candycane(p: Pen) -> str:
    r = p.rng
    p.band("M360 910 L360 360 C360 130 700 130 700 360", 120)
    for y in range(420, 900, 85):
        p.line(f"M300 {y} L420 {y - 55}", p.w * 1.1)
    p.line("M470 190 L555 235", p.w * 1.1)
    p.line("M580 220 L650 300", p.w * 1.1)
    p.e(780, 780, 60, 24, -30)
    p.poly(_star_pts(180, 250, 50, .45))
    p.poly(_star_pts(840, 160, 36, .45))
    return p.svg()


def easteregg(p: Pen) -> str:
    r = p.rng
    p.e(500, 530, 270, 380)
    p.path("M235 470 L310 400 L385 470 L460 400 L540 470 L615 400 L690 470 L765 400 L765 560 L690 630 L615 560 L540 630 L460 560 L385 630 L310 560 L235 630 Z")
    for x in (330, 500, 670):
        p.e(x, 770, 34)
    for x in (400, 600):
        p.e(x, 260, 26)
    p.line("M290 700 Q500 780 710 700")
    return p.svg()


def chick(p: Pen) -> str:
    r = p.rng
    p.e(500, 640, 270, 250)
    p.e(500, 330, 175)
    p.path("M230 700 L290 640 L350 700 L410 640 L470 700 L530 640 L590 700 L650 640 L710 700 L770 640 L770 820 L230 820 Z")
    p.poly([(440, 340), (560, 340), (500, 410)])
    p.eyes(425, 575, 290, 18)
    p.e(260, 620, 70, 120, 20)
    p.e(740, 620, 70, 120, -20)
    for x in (430, 570):
        p.line(f"M{x} 880 L{x} 920 M{x - 30} 920 L{x + 30} 920")
    p.line("M470 160 Q480 100 520 90")
    p.line("M520 160 Q550 110 590 120")
    return p.svg()


def fox(p: Pen) -> str:
    r = p.rng
    p.poly([(215, 440), (190, 120), (440, 300)])
    p.poly([(785, 440), (810, 120), (560, 300)])
    p.poly([(255, 350), (250, 220), (360, 300)], "#ffffff")
    p.e(500, 560, 330, 260)
    p.poly([(170, 600), (350, 700), (240, 790)])
    p.poly([(830, 600), (650, 700), (760, 790)])
    p.e(500, 690, 160, 130)
    p.eyes(380, 620, 520, 18)
    p.e(500, 640, 38, 28)
    p.line("M500 668 L500 720 M500 720 Q460 770 420 740 M500 720 Q540 770 580 740")
    p.poly([(330, 400), (440, 440), (350, 470)])
    p.poly([(670, 400), (560, 440), (650, 470)])
    return p.svg()


def hedgehog(p: Pen) -> str:
    r = p.rng
    pts = " ".join(f"L{150 + i * 38} {(300 if i % 2 == 0 else 400) + 70 * math.sin(i / 3):.0f}" for i in range(1, 19))
    p.path(f"M120 700 C100 560 150 460 200 420 {pts} C820 440 900 560 880 700 Z")
    p.e(300, 760, 70, 36)
    p.e(670, 760, 70, 36)
    p.e(760, 600, 200, 150, -14)
    p.e(930, 660, 40, 34)
    p.dot(790, 560, 16)
    p.line("M820 650 Q780 690 740 660")
    p.e(430, 600, 40, 70, 0)
    if not p.simple:
        p.spots((220, 480, 560, 660), 3, 16, 26)
    return p.svg()


def cow(p: Pen) -> str:
    r = p.rng
    p.e(230, 420, 130, 62, 20)
    p.e(770, 420, 130, 62, -20)
    p.line("M360 280 Q330 170 270 150 M640 280 Q670 170 730 150")
    p.e(500, 480, 250, 280)
    p.e(500, 740, 195, 130)
    p.dot(430, 740, 20)
    p.dot(570, 740, 20)
    p.eyes(405, 595, 450, 22)
    if not p.simple:
        p.e(380, 360, 60, 42, 0, K)
    p.e(630, 580, 70, 60, 0, "#ffffff")
    p.line("M430 255 Q500 215 570 255")
    return p.svg()


def pig(p: Pen) -> str:
    r = p.rng
    p.poly([(250, 330), (330, 160), (440, 280)])
    p.poly([(750, 330), (670, 160), (560, 280)])
    p.e(500, 520, 285, 270)
    p.e(500, 620, 130, 95)
    p.dot(460, 620, 16)
    p.dot(540, 620, 16)
    p.eyes(380, 620, 450, 20)
    p.line("M430 735 Q500 770 570 735")
    if r.random() < .5:
        p.spots((620, 360, 760, 520), 2, 22, 34)
    return p.svg()


def sheep(p: Pen) -> str:
    r = p.rng
    for x in (330, 420, 590, 680):
        p.rect(x - 22, 700, 44, 190, 12)
    for cx, cy, rr in ((300, 520, 120), (400, 440, 130), (520, 410, 140), (640, 450, 130), (710, 560, 120), (590, 620, 130), (440, 620, 130), (320, 630, 100)):
        p.e(cx, cy, rr)
    p.e(830, 470, 105, 125, -10)
    p.e(760, 360, 50, 24, -30)
    p.dot(850, 440, 16)
    p.line("M810 540 Q840 570 870 540")
    return p.svg()


def dog(p: Pen) -> str:
    r = p.rng
    p.e(300, 470, 85, 195, 14)
    p.e(700, 470, 85, 195, -14)
    p.e(500, 480, 230, 215)
    p.e(500, 600, 120, 85)
    p.e(500, 560, 42, 30, 0, K)
    p.line("M500 590 L500 640")
    p.path("M460 660 Q500 760 540 660 Z", "#ffffff")
    p.eyes(410, 590, 440, 20)
    p.e(500, 800, 150, 40)
    p.dot(500, 800, 18)
    return p.svg()


def mouse(p: Pen) -> str:
    r = p.rng
    p.line("M690 800 Q860 800 840 640 Q830 560 900 540")
    p.e(320, 250, 120)
    p.e(680, 250, 120)
    p.e(320, 250, 66)
    p.e(680, 250, 66)
    p.e(500, 780, 220, 150)
    p.e(500, 470, 215, 195)
    p.eyes(420, 580, 430, 18)
    p.e(500, 540, 26, 20, 0, K)
    p.line("M500 560 Q480 600 450 585 M500 560 Q520 600 550 585")
    p.line("M330 540 L220 520 M330 565 L225 580 M670 540 L780 520 M670 565 L775 580")
    return p.svg()


def panda(p: Pen) -> str:
    r = p.rng
    p.e(310, 270, 90, 90, 0, K)
    p.e(690, 270, 90, 90, 0, K)
    p.e(500, 770, 230, 190)
    p.e(500, 790, 130, 120)
    p.e(290, 800, 80, 120, 20, K)
    p.e(710, 800, 80, 120, -20, K)
    p.e(500, 450, 215, 190)
    p.e(380, 430, 62, 85, -25, K)
    p.e(620, 430, 62, 85, 25, K)
    p.dot(385, 435, 20)
    p.dot(615, 435, 20)
    p.e(500, 540, 32, 24, 0, K)
    p.line("M500 565 Q480 600 450 585 M500 565 Q520 600 550 585")
    return p.svg()


def monkey(p: Pen) -> str:
    r = p.rng
    p.line("M690 800 Q890 840 870 640 Q860 540 800 560", p.w * 1.8)
    p.e(260, 440, 80, 80)
    p.e(740, 440, 80, 80)
    p.e(500, 780, 210, 170)
    p.e(500, 720, 110, 100)
    p.e(500, 440, 215, 205)
    p.path("M500 330 C390 290 330 400 360 490 C380 580 440 640 500 640 C560 640 620 580 640 490 C670 400 610 290 500 330 Z")
    p.eyes(440, 560, 440, 18)
    p.dot(470, 520, 9)
    p.dot(530, 520, 9)
    p.line("M440 575 Q500 625 560 575")
    return p.svg()


def koala(p: Pen) -> str:
    r = p.rng
    p.e(250, 330, 130)
    p.e(750, 330, 130)
    p.e(250, 330, 70)
    p.e(750, 330, 70)
    p.e(500, 790, 220, 170)
    p.e(500, 460, 235, 210)
    p.eyes(405, 595, 440, 20)
    p.e(500, 535, 70, 100, 0, K)
    p.line("M455 640 Q500 690 545 640")
    return p.svg()


def horse(p: Pen) -> str:
    r = p.rng
    p.band("M250 590 C140 610 90 710 130 820", 70)
    for x in (300, 380, 590, 670):
        p.rect(x, 700, 54, 210, 18)
    p.e(480, 640, 260, 160)
    p.band("M620 560 C650 450 680 370 700 300", 120)
    p.e(735, 255, 125, 85, 28)
    p.poly([(690, 190), (665, 105), (740, 160)])
    p.dot(765, 245, 15)
    for k in range(5):
        p.e(610 - k * 10 + (k % 2) * 25, 200 + k * 80, 36)
    p.line("M785 305 q-25 20 -45 4")
    return p.svg()


def seahorse(p: Pen) -> str:
    r = p.rng
    p.e(400, 340, 150, 110, -10)
    p.e(560, 330, 120, 36, -14)
    p.band("M470 420 C650 480 680 640 560 720 C470 780 420 860 500 900", 150)
    p.e(670, 520, 70, 40, 24)
    p.dot(395, 310, 17)
    p.line("M390 240 Q380 170 330 150 M430 240 Q440 170 480 150")
    for k in range(5):
        p.line(f"M{560 + k * 4} {470 + k * 80} q55 20 80 {-10}")
    p.poly(_star_pts(200, 700, 48, .45))
    return p.svg()


def starfish(p: Pen) -> str:
    r = p.rng
    p.poly(_star_pts(500, 520, 420, .45, 5))
    p.eyes(440, 560, 470, 17)
    p.smile(500, 520, 50)
    if not p.simple:
        for k in range(5):
            a = math.radians(-90 + k * 72)
            for d in (.55, .75):
                p.dot(500 + 420 * d * math.cos(a), 520 + 420 * d * math.sin(a), 9)
    return p.svg()


def jellyfish(p: Pen) -> str:
    r = p.rng
    for i, x in enumerate((310, 410, 500, 590, 690)):
        p.band(f"M{x} 520 C{x + 50} 620 {x - 50} 720 {x + 20} 840 S{x - 20} 920 {x} 930", 34)
    p.path("M150 520 C130 150 870 150 850 520 Q780 580 700 520 Q630 580 560 520 Q500 580 440 520 Q370 580 300 520 Q220 580 150 520 Z")
    p.eyes(400, 600, 390, 18)
    p.smile(500, 430, 55)
    p.spots((250, 250, 750, 340), 3, 18, 28)
    return p.svg()


def dragon(p: Pen) -> str:
    r = p.rng
    p.line("M250 800 Q80 800 120 650 Q140 590 90 560", p.w * 1.2)
    p.poly([(130, 560), (60, 540), (110, 620)])
    p.e(300, 380, 120, 190, -30)
    p.e(480, 640, 250, 190)
    for i in range(5):
        x = 330 + i * 70
        p.poly([(x - 26, 470 + abs(i - 2) * 16), (x, 395 + abs(i - 2) * 16), (x + 26, 470 + abs(i - 2) * 16)])
    p.e(480, 690, 120, 120, 0, "#ffffff")
    p.band("M660 560 C720 500 740 420 725 350", 120)
    p.e(780, 290, 140, 100, -6)
    p.poly([(720, 210), (700, 120), (770, 190)])
    p.dot(815, 260, 17)
    p.dot(850, 320, 9)
    p.line("M770 330 Q810 350 850 330")
    p.e(380, 840, 60, 50)
    p.e(590, 840, 60, 50)
    return p.svg()


def castle(p: Pen) -> str:
    r = p.rng
    def tower(x, w, top, base=900):
        p.rect(x, top, w, base - top)
        n = 3
        for i in range(n):
            p.rect(x + i * w / n + 4, top - 50, w / n - 8, 55)
    tower(120, 160, 360)
    tower(720, 160, 360)
    p.rect(300, 450, 400, 450)
    for i in range(5):
        p.rect(300 + i * 80 + 6, 400, 68, 55)
    p.path("M420 900 L420 740 A80 80 0 0 1 580 740 L580 900 Z")
    for x in (180, 780):
        p.rect(x, 520, 40, 80, 20)
    p.rect(335, 520, 60, 90, 28)
    p.rect(605, 520, 60, 90, 28)
    p.line("M200 310 L200 190 M200 190 L290 215 L200 240", p.w)
    p.line("M800 310 L800 190 M800 190 L890 215 L800 240", p.w)
    p.poly(_star_pts(500, 250, 55, .45))
    return p.svg()


def fairy(p: Pen) -> str:
    r = p.rng
    p.e(330, 470, 110, 230, 40)
    p.e(670, 470, 110, 230, -40)
    p.e(345, 650, 70, 130, 55)
    p.e(655, 650, 70, 130, -55)
    p.path("M390 420 L610 420 L700 760 L300 760 Z")
    p.e(500, 300, 100)
    p.path("M400 300 C390 170 610 170 600 300 C560 230 440 230 400 300 Z")
    p.eyes(465, 535, 310, 12)
    p.smile(500, 335, 28)
    p.line("M410 760 L400 890 M590 760 L600 890")
    p.line("M650 470 L810 330")
    p.poly(_star_pts(840, 300, 60, .45))
    return p.svg()


def mermaid(p: Pen) -> str:
    r = p.rng
    p.band("M500 590 C470 720 560 800 640 860", 150)
    p.e(700, 880, 95, 40, -35)
    p.e(640, 940, 100, 40, 25)
    p.e(500, 510, 118, 150)
    p.e(500, 300, 100)
    p.path("M400 300 C375 120 625 120 600 300 C560 215 440 215 400 300 Z")
    p.line("M402 300 Q320 430 350 560 M598 300 Q680 430 650 560")
    p.eyes(465, 535, 320, 12)
    p.smile(500, 350, 28)
    p.e(400, 480, 30, 20, 0)
    p.e(600, 480, 30, 20, 0)
    for k in range(3):
        p.line(f"M{500 + k * 24 - 20} {640 + k * 55} q15 20 30 0")
    p.poly(_star_pts(170, 250, 48, .45))
    p.poly(_star_pts(850, 300, 36, .45))
    return p.svg()

def bicycle(p: Pen) -> str:
    r = p.rng
    for cx in (270, 730):
        p.e(cx, 670, 190)
        p.e(cx, 670, 150, 150, 0, "none")
        for k in range(8):
            a = math.radians(k * 45)
            p.line(f"M{cx} 670 L{cx + 150 * math.cos(a):.0f} {670 + 150 * math.sin(a):.0f}", p.w * .6)
        p.dot(cx, 670, 18)
    p.line("M270 670 L450 440 L640 440 L730 670 M450 440 L520 670 L270 670 M520 670 L640 440", p.w * 1.3)
    p.line("M640 440 L610 330 M570 330 L670 330", p.w * 1.3)
    p.line("M450 440 L440 360", p.w * 1.3)
    p.e(430, 340, 70, 24)
    return p.svg()


def bus(p: Pen) -> str:
    r = p.rng
    p.rect(90, 290, 820, 440, 60)
    for k in range(4):
        p.rect(140 + k * 160, 350, 120, 130, 14)
    p.rect(790, 350, 90, 250, 14)
    p.line("M90 560 L910 560")
    p.e(800, 670, 34, 24)
    p.rect(110, 650, 40, 36, 8)
    for cx in (280, 690):
        p.e(cx, 740, 95)
        p.e(cx, 740, 38)
    p.poly([(330, 290), (670, 290), (640, 240), (360, 240)])
    return p.svg()


def firetruck(p: Pen) -> str:
    r = p.rng
    p.line("M180 360 L720 260 M180 330 L720 230", p.w * 1.6)
    for k in range(7):
        p.line(f"M{240 + k * 75} {350 - k * 12} L{240 + k * 75} {320 - k * 12}", p.w * 1.1)
    p.rect(110, 420, 530, 270, 18)
    p.rect(640, 380, 250, 310, 24)
    p.rect(690, 420, 130, 110, 14)
    p.e(230, 410, 40, 28)
    p.line("M110 560 L640 560")
    for cx in (260, 560, 790):
        p.e(cx, 720, 90)
        p.e(cx, 720, 34)
    p.e(780, 365, 30, 22)
    return p.svg()


def helicopter(p: Pen) -> str:
    r = p.rng
    p.line("M180 220 L820 220 M500 220 L500 300", p.w * 1.4)
    p.band("M170 440 L520 450", 60)
    p.line("M170 400 L120 330", p.w * 1.2)
    p.e(560, 480, 260, 170)
    p.e(640, 450, 100, 80)
    p.rect(450, 270, 120, 50, 10)
    p.line("M320 700 L750 700 M400 640 L400 700 M650 640 L650 700", p.w * 1.3)
    p.e(330, 510, 50, 40)
    for x, y in ((130, 140), (860, 600), (150, 760)):
        p.poly(_star_pts(x, y, 40, .45))
    return p.svg()


def tractor(p: Pen) -> str:
    r = p.rng
    p.rect(560, 150, 40, 150, 10)
    p.rect(260, 330, 260, 130, 10)
    p.rect(440, 190, 280, 280, 18)
    p.rect(490, 230, 180, 150, 12)
    p.rect(560, 420, 360, 130, 24)
    p.e(330, 640, 190)
    p.e(330, 640, 70)
    p.e(790, 700, 100)
    p.e(790, 700, 38)
    for k in range(10):
        a = math.radians(k * 36)
        p.line(f"M{330 + 190 * math.cos(a):.0f} {640 + 190 * math.sin(a):.0f} L{330 + 160 * math.cos(a):.0f} {640 + 160 * math.sin(a):.0f}")
    return p.svg()


def hotairballoon(p: Pen) -> str:
    r = p.rng
    p.path("M500 120 C860 120 880 520 640 640 L360 640 C120 520 140 120 500 120 Z")
    p.line("M500 120 C400 260 400 520 450 640 M500 120 C600 260 600 520 550 640", p.w)
    p.line("M180 330 Q500 400 820 330 M230 470 Q500 540 770 470", p.w)
    p.rect(420, 770, 160, 120, 14)
    p.line("M390 640 L430 770 M610 640 L570 770 M500 640 L500 770")
    p.path("M110 240 a40 40 0 0 1 20 -75 a60 60 0 0 1 110 -20 a45 45 0 0 1 60 95 Z")
    return p.svg()


def rainbowcloud(p: Pen) -> str:
    r = p.rng
    for k in range(5):
        rr = 410 - k * 60
        p.path(f"M{500 - rr} 700 A{rr} {rr} 0 0 1 {500 + rr} 700 L{500 + rr - 60} 700 A{rr - 60} {rr - 60} 0 0 0 {500 - rr + 60} 700 Z")
    p.path("M60 760 a90 90 0 0 1 60 -170 a110 110 0 0 1 200 -10 a85 85 0 0 1 90 180 Z")
    p.path("M610 760 a90 90 0 0 1 60 -170 a110 110 0 0 1 200 -10 a85 85 0 0 1 90 180 Z")
    p.eyes(200, 270, 700, 12)
    p.eyes(750, 820, 700, 12)
    return p.svg()


def umbrella(p: Pen) -> str:
    r = p.rng
    p.path("M110 480 C110 220 890 220 890 480 Q820 410 750 480 Q680 410 610 480 Q555 410 500 480 Q445 410 390 480 Q320 410 250 480 Q180 410 110 480 Z")
    p.line("M500 280 L500 800 M500 800 Q500 900 400 880", p.w * 1.4)
    p.line("M500 280 L250 480 M500 280 L750 480 M500 280 L390 480 M500 280 L610 480", p.w)
    for x, y in ((220, 640), (350, 720), (700, 600), (790, 720), (620, 800), (160, 800)):
        p.path(f"M{x} {y - 40} Q{x + 34} {y + 10} {x} {y + 30} Q{x - 34} {y + 10} {x} {y - 40} Z")
    return p.svg()


def snowflake(p: Pen) -> str:
    r = p.rng
    for k in range(6):
        a = math.radians(k * 60 - 90)
        ca, sa = math.cos(a), math.sin(a)
        p.line(f"M500 500 L{500 + 400 * ca:.0f} {500 + 400 * sa:.0f}", p.w * 1.3)
        for d, w in ((.45, 110), (.7, 80)):
            bx, by = 500 + 400 * d * ca, 500 + 400 * d * sa
            for s in (-1, 1):
                b = a + s * math.radians(45)
                p.line(f"M{bx:.0f} {by:.0f} L{bx + w * math.cos(b):.0f} {by + w * math.sin(b):.0f}", p.w)
        p.e(500 + 405 * ca, 500 + 405 * sa, 22)
    p.e(500, 500, 70)
    return p.svg()


def sunface(p: Pen) -> str:
    r = p.rng
    n = 12
    for k in range(n):
        a = math.radians(k * 360 / n)
        c, s = math.cos(a), math.sin(a)
        p.poly([(500 + 250 * c - 60 * s, 500 + 250 * s + 60 * c), (500 + 440 * c, 500 + 440 * s), (500 + 250 * c + 60 * s, 500 + 250 * s - 60 * c)])
    p.e(500, 500, 270)
    p.eyes(410, 590, 460, 22)
    p.smile(500, 540, 90)
    p.e(340, 560, 36, 22)
    p.e(660, 560, 36, 22)
    return p.svg()


def moonface(p: Pen) -> str:
    r = p.rng
    p.path("M600 90 C230 130 130 330 130 500 C130 680 240 880 600 910 C380 800 340 620 340 500 C340 380 400 200 600 90 Z")
    p.dot(250, 480, 8)
    p.line("M215 520 Q255 560 300 520", p.w)
    p.poly(_star_pts(780, 250, 70, .45))
    p.poly(_star_pts(850, 600, 45, .45))
    p.poly(_star_pts(720, 810, 36, .45))
    return p.svg()


def kite(p: Pen) -> str:
    r = p.rng
    p.poly([(500, 90), (790, 400), (500, 720), (210, 400)])
    p.line("M500 90 L500 720 M210 400 L790 400", p.w)
    p.line("M500 720 C440 780 560 830 480 890 C420 940 540 950 470 990", p.w)
    for x, y in ((460, 810), (505, 880)):
        _bow(p, x, y, .45)
    return p.svg()


def tree(p: Pen) -> str:
    r = p.rng
    p.path("M430 900 L450 560 L550 560 L570 900 Z")
    p.line("M500 640 L400 540 M500 600 L620 500", p.w * 1.2)
    for cx, cy, rr in ((500, 300, 200), (330, 430, 150), (670, 430, 150), (500, 470, 150)):
        p.e(cx, cy, rr)
    for x, y in ((420, 330), (580, 280), (350, 450), (650, 470), (500, 460)):
        p.e(x, y, 30)
    p.line("M130 900 L870 900")
    return p.svg()


def heartface(p: Pen) -> str:
    r = p.rng
    p.path("M500 880 C120 640 80 330 270 250 C380 205 470 260 500 340 C530 260 620 205 730 250 C920 330 880 640 500 880 Z")
    p.eyes(400, 600, 480, 22)
    p.smile(500, 540, 70)
    p.e(335, 560, 40, 24)
    p.e(665, 560, 40, 24)
    for x, y, s in ((120, 150, 50), (880, 130, 40), (840, 880, 36)):
        p.path(f"M{x} {y + s * .55:.0f} C{x - s * 1.15:.0f} {y - s * .25:.0f} {x - s * .55:.0f} {y - s * .95:.0f} {x} {y - s * .4:.0f} C{x + s * .55:.0f} {y - s * .95:.0f} {x + s * 1.15:.0f} {y - s * .25:.0f} {x} {y + s * .55:.0f} Z")
    return p.svg()


NEW = {
    "pumpkin": ("pumpkin", pumpkin), "ghost": ("ghost", ghost), "bat": ("bat", bat), "witchhat": ("witch hat", witchhat), "xmastree": ("Christmas tree", xmastree),
    "snowman": ("snowman", snowman), "gift": ("present", gift), "candycane": ("candy cane", candycane), "easteregg": ("Easter egg", easteregg), "chick": ("chick", chick),
    "fox": ("fox", fox), "hedgehog": ("hedgehog", hedgehog), "cow": ("cow", cow), "pig": ("pig", pig), "sheep": ("sheep", sheep), "dog": ("dog", dog),
    "mouse": ("mouse", mouse), "panda": ("panda", panda), "monkey": ("monkey", monkey), "koala": ("koala", koala), "horse": ("horse", horse), "seahorse": ("seahorse", seahorse),
    "starfish": ("starfish", starfish), "jellyfish": ("jellyfish", jellyfish), "dragon": ("dragon", dragon), "castle": ("castle", castle), "fairy": ("fairy", fairy),
    "mermaid": ("mermaid", mermaid), "bicycle": ("bicycle", bicycle), "bus": ("bus", bus), "firetruck": ("fire truck", firetruck), "helicopter": ("helicopter", helicopter),
    "tractor": ("tractor", tractor), "hotairballoon": ("hot air balloon", hotairballoon), "rainbowcloud": ("rainbow", rainbowcloud), "umbrella": ("umbrella", umbrella),
    "snowflake": ("snowflake", snowflake), "sunface": ("sun", sunface), "moonface": ("moon", moonface), "kite": ("kite", kite), "tree": ("tree", tree), "heartface": ("heart", heartface),
}
PLURALS = {"fox": "foxes", "sheep": "sheep", "mouse": "mice", "ghost": "ghosts", "bus": "buses", "gift": "presents", "tree": "trees", "snowman": "snowmen",
           "dragon": "dragons", "pumpkin": "pumpkins", "umbrella": "umbrellas"}
THEMES = {
    "halloween": ("Spooky Halloween", ["pumpkin", "ghost", "bat", "witchhat", "pumpkin", "ghost", "mushroom", "owl"]),
    "christmas": ("Merry Christmas", ["xmastree", "snowman", "gift", "candycane", "snowflake", "xmastree", "penguin", "bear"]),
    "easter": ("Happy Easter", ["easteregg", "chick", "bunny", "flower", "butterfly", "easteregg", "sheep", "duck"]),
    "valentine": ("Love & Hearts", ["heartface", "bunny", "bear", "gift", "butterfly", "cupcake", "heartface", "cat"]),
    "farm2": ("Barnyard Buddies", ["cow", "pig", "sheep", "horse", "dog", "chick", "tractor", "duck"]),
    "pets": ("Pet Pals", ["dog", "cat", "bunny", "mouse", "fish", "turtle", "owl", "hedgehog"]),
    "forest": ("Forest Friends", ["fox", "hedgehog", "owl", "bear", "mushroom", "tree", "bunny", "butterfly"]),
    "safari2": ("Wild Animals", ["panda", "koala", "monkey", "lion", "elephant", "giraffe", "frog", "penguin"]),
    "sea2": ("Ocean Explorers", ["seahorse", "starfish", "jellyfish", "crab", "shark", "whale", "octopus", "mermaid"]),
    "fantasy": ("Dragons & Castles", ["dragon", "castle", "fairy", "unicorn", "mermaid", "mushroom", "witchhat", "kite"]),
    "wheels": ("Wheels & Wings", ["bicycle", "bus", "firetruck", "helicopter", "tractor", "hotairballoon", "airplane", "train"]),
    "weather": ("Sunshine & Rain", ["sunface", "moonface", "rainbowcloud", "umbrella", "snowflake", "kite", "tree", "flower"]),
    "birthday": ("Birthday Party", ["cupcake", "balloons", "gift", "icecream", "pizza", "unicorn", "kite", "hotairballoon"]),
}


def register() -> None:
    for key, (name, fn) in NEW.items():
        if key not in kidsart._FIGURES:
            kidsart._FIGURES[key] = fn
            kidsart.KINDS.append(key)
            kidsart.NAMES[key] = name
    kidsart.PLURALS.update(PLURALS)
    for k, v in THEMES.items():
        kidsart.THEMES.setdefault(k, (v[0], [x for x in v[1] if x in kidsart._FIGURES]))


register()
