"""Line art for children's coloring books: bold, friendly figures (animals, sea life, vehicles, treats...) drawn from simple shapes, with
details that change every time (spots, bows, stripes, faces, how many petals), plus learning pages: shape faces, count-and-colour and
trace-the-shape. Everything is a 1000 x 1000 SVG with white-filled outlines, ready to colour at any page size."""
from __future__ import annotations

import math
import random

INK = "#222222"
KINDS = ["cat", "fish", "butterfly", "turtle", "owl", "snail", "ladybug", "whale", "octopus", "rocket", "car", "robot", "dino", "flower", "house", "icecream",
         "frog", "bunny", "bear", "penguin", "duck", "elephant", "giraffe", "lion", "bee", "crab", "shark", "airplane", "sailboat", "train", "cupcake",
         "mushroom", "unicorn", "pizza", "apple", "ufo", "planet", "balloons"]
NAMES = {"cat": "cat", "fish": "fish", "butterfly": "butterfly", "turtle": "turtle", "owl": "owl", "snail": "snail", "ladybug": "ladybug", "whale": "whale",
         "octopus": "octopus", "rocket": "rocket", "car": "car", "robot": "robot", "dino": "dinosaur", "flower": "flower", "house": "house", "icecream": "ice cream",
         "frog": "frog", "bunny": "bunny", "bear": "bear", "penguin": "penguin", "duck": "duck", "elephant": "elephant", "giraffe": "giraffe", "lion": "lion",
         "bee": "bee", "crab": "crab", "shark": "shark", "airplane": "airplane", "sailboat": "sailboat", "train": "train", "cupcake": "cupcake",
         "mushroom": "mushroom", "unicorn": "unicorn", "pizza": "pizza", "apple": "apple", "ufo": "flying saucer", "planet": "planet", "balloons": "balloons"}
PLURALS = {"bunny": "bunnies", "balloons": "balloons", "ufo": "flying saucers", "butterfly": "butterflies", "fish": "fish", "icecream": "ice creams", "dino": "dinosaurs", "ladybug": "ladybugs", "octopus": "octopuses"}
THEMES = {
    "mixed": ("Animal & Friends", KINDS),
    "animals": ("Cute Animal", ["cat", "owl", "butterfly", "turtle", "snail", "ladybug", "dino", "fish"]),
    "ocean": ("Under the Sea", ["fish", "whale", "octopus", "turtle", "fish", "octopus"]),
    "garden": ("Garden Bugs & Flowers", ["butterfly", "ladybug", "snail", "flower", "house", "owl"]),
    "vehicles": ("Rockets, Cars & Robots", ["rocket", "car", "robot", "rocket", "car", "robot"]),
    "dinosaurs": ("Friendly Dinosaur", ["dino", "dino", "turtle", "flower", "dino", "butterfly"]),
    "treats": ("Sweet Treats & Fun", ["icecream", "cupcake", "apple", "pizza", "balloons", "butterfly"]),
    "farm": ("Farm Friends", ["duck", "bunny", "house", "flower", "bee", "snail", "mushroom"]),
    "jungle": ("Jungle Safari", ["lion", "elephant", "giraffe", "frog", "butterfly", "turtle"]),
    "space": ("Space Adventure", ["rocket", "ufo", "planet", "robot", "rocket", "ufo"]),
    "arctic": ("Arctic Friends", ["penguin", "bear", "shark", "whale", "octopus", "fish"]),
    "transport": ("Things That Go", ["airplane", "sailboat", "train", "car", "rocket", "airplane"]),
    "fairytale": ("Fairytale Magic", ["unicorn", "butterfly", "house", "flower", "mushroom", "dino"]),
}
AGES = {"toddler": 15, "kids": 10}   # stroke width: toddlers get thicker, simpler lines
SHAPES = ["circle", "square", "triangle", "star", "heart", "oval", "diamond", "hexagon"]


class Pen:
    """Collects outlined shapes. Every closed shape is filled white so shapes in front hide the lines behind them."""

    def __init__(self, rng: random.Random, width: float = 10, simple: bool = False):
        self.rng, self.w, self.simple, self.parts = rng, width, simple, []

    def _attrs(self, fill: str = "#ffffff") -> str:
        return f"fill='{fill}' stroke='{INK}' stroke-width='{self.w}' stroke-linejoin='round' stroke-linecap='round'"

    def e(self, cx, cy, rx, ry=None, rot=0, fill="#ffffff"):
        ry = rx if ry is None else ry
        t = f" transform='rotate({rot} {cx:.0f} {cy:.0f})'" if rot else ""
        self.parts.append(f"<ellipse cx='{cx:.1f}' cy='{cy:.1f}' rx='{rx:.1f}' ry='{ry:.1f}' {self._attrs(fill)}{t}/>")

    def poly(self, pts, fill="#ffffff"):
        self.parts.append(f"<polygon points='{' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)}' {self._attrs(fill)}/>")

    def path(self, d, fill="#ffffff"):
        self.parts.append(f"<path d='{d}' {self._attrs(fill)}/>")

    def line(self, d, w=None):
        self.parts.append(f"<path d='{d}' fill='none' stroke='{INK}' stroke-width='{w or self.w}' stroke-linecap='round' stroke-linejoin='round'/>")

    def dot(self, cx, cy, r=None):
        self.parts.append(f"<circle cx='{cx:.1f}' cy='{cy:.1f}' r='{r or self.w * 1.6:.1f}' fill='{INK}'/>")

    def rect(self, x, y, w, h, r=0, fill="#ffffff"):
        self.parts.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{w:.1f}' height='{h:.1f}' rx='{r}' {self._attrs(fill)}/>")

    def band(self, d, width):
        """A thick curved limb: an ink outline with a white core."""
        self.parts.append(f"<path d='{d}' fill='none' stroke='{INK}' stroke-width='{width + 2 * self.w}' stroke-linecap='round'/>"
                          f"<path d='{d}' fill='none' stroke='#ffffff' stroke-width='{width}' stroke-linecap='round'/>")

    def smile(self, cx, cy, w=70):
        self.line(f"M{cx - w:.0f} {cy:.0f} Q{cx:.0f} {cy + w * .8:.0f} {cx + w:.0f} {cy:.0f}")

    def eyes(self, lx, rx, y, r=None):
        self.dot(lx, y, r)
        self.dot(rx, y, r)

    def spots(self, area, n, rmin, rmax):
        """Random non-overlapping circles inside (x0, y0, x1, y1)."""
        x0, y0, x1, y1 = area
        placed: list[tuple[float, float, float]] = []
        for _ in range(n * 25):
            if len(placed) >= n:
                break
            r = self.rng.uniform(rmin, rmax)
            x, y = self.rng.uniform(x0 + r, x1 - r), self.rng.uniform(y0 + r, y1 - r)
            if all(math.hypot(x - px, y - py) > r + pr + self.w * 2 for px, py, pr in placed):
                placed.append((x, y, r))
        for x, y, r in placed:
            self.e(x, y, r)

    def svg(self) -> str:
        return "".join(self.parts)


def _star_pts(cx, cy, r, inner=.45, n=5, rot=-90):
    return [(cx + (r if i % 2 == 0 else r * inner) * math.cos(math.radians(rot + i * 180 / n)), cy + (r if i % 2 == 0 else r * inner) * math.sin(math.radians(rot + i * 180 / n))) for i in range(n * 2)]


def _bow(p: Pen, cx, cy, s=1.0):
    p.poly([(cx, cy), (cx - 85 * s, cy - 50 * s), (cx - 85 * s, cy + 50 * s)])
    p.poly([(cx, cy), (cx + 85 * s, cy - 50 * s), (cx + 85 * s, cy + 50 * s)])
    p.e(cx, cy, 26 * s)


# --------------------------------------------------------------------------- figures (each returns its shapes in a 1000 box)
def cat(p: Pen) -> str:
    r = p.rng
    p.line(f"M690 770 C{r.randint(820, 900)} 780 {r.randint(860, 920)} 600 {r.randint(780, 830)} 520")   # tail
    p.e(500, 720, 220, 190)
    p.poly([(330, 330), (315, 150), (460, 265)])
    p.poly([(670, 330), (685, 150), (540, 265)])
    p.e(500, 440, 200, 165)
    p.poly([(350, 290), (345, 215), (410, 262)])
    p.poly([(650, 290), (655, 215), (590, 262)])
    p.eyes(425, 575, 420, 20)
    p.poly([(478, 468), (522, 468), (500, 498)])
    p.line("M500 498 Q470 540 435 520")
    p.line("M500 498 Q530 540 565 520")
    for dy, dx in ((0, 0), (28, 8)):   # whiskers
        p.line(f"M{330 - dx} {480 + dy} L{250 - dx} {470 + dy * 2}")
        p.line(f"M{670 + dx} {480 + dy} L{750 + dx} {470 + dy * 2}")
    for k in range(r.choice([0, 2, 3])):   # forehead stripes
        p.line(f"M{500 + (k - 1) * 45} 290 L{500 + (k - 1) * 45} {335 if k == 1 else 325}")
    if r.random() < .6:
        _bow(p, 500, 610, .8)
    if not p.simple:
        p.e(410, 890, 62, 38)
        p.e(590, 890, 62, 38)
        p.line("M500 640 Q500 760 500 860")
    return p.svg()


def fish(p: Pen) -> str:
    r = p.rng
    p.poly([(740, 500), (930, 340), (930, 660)])
    p.path("M390 320 Q500 190 640 330 Z")
    p.path("M420 690 Q500 780 600 690 Z")
    p.e(480, 500, 300, 190)
    p.e(330, 450, 48)
    p.dot(335, 452, 22)
    p.smile(255, 560, 40)
    if not p.simple:
        for row in range(3):
            for k in range(3 - row % 2):
                x = 470 + k * 90 + (45 if row % 2 else 0) - 45
                p.line(f"M{x} {430 + row * 70} a42 42 0 0 0 84 0")
    for _ in range(3):   # bubbles
        p.e(r.randint(120, 230), r.randint(150, 330), r.randint(18, 38))
    return p.svg()


def butterfly(p: Pen) -> str:
    r = p.rng
    p.e(335, 390, 175, 225, -30)
    p.e(665, 390, 175, 225, 30)
    p.e(385, 650, 125, 160, 28)
    p.e(615, 650, 125, 160, -28)
    for side in (-1, 1):
        cx = 500 + side * 170
        p.spots((cx - 90, 260, cx + 90, 500), 2 if p.simple else 3, 25, 55)
        p.spots((500 + side * 180 - 55, 560, 500 + side * 180 + 55, 720), 1 if p.simple else 2, 20, 38)
    p.e(500, 520, 42, 215)
    p.e(500, 270, 52)
    p.line(f"M480 230 Q{440 - r.randint(0, 40)} 130 400 110")
    p.line(f"M520 230 Q{560 + r.randint(0, 40)} 130 600 110")
    p.e(400, 105, 18)
    p.e(600, 105, 18)
    p.eyes(485, 515, 265, 11)
    return p.svg()


def turtle(p: Pen) -> str:
    for x in (300, 700):
        p.e(x, 735, 75, 90)
    p.e(150, 650, 62, 34, -15)
    p.e(815, 560, 105, 90)
    p.dot(855, 535, 15)
    p.smile(830, 590, 36)
    p.path("M170 650 C170 300 830 300 830 650 Z")
    p.line("M170 650 L830 650")
    hexes = [(500, 480, 85)] + ([] if p.simple else [(335, 545, 58), (665, 545, 58)])
    for cx, cy, rr in hexes:
        p.poly([(cx + rr * math.cos(math.radians(60 * i + 30)), cy + rr * math.sin(math.radians(60 * i + 30))) for i in range(6)])
    p.line("M500 395 L500 345")
    p.line("M425 520 L385 535")
    p.line("M575 520 L615 535")
    return p.svg()


def owl(p: Pen) -> str:
    r = p.rng
    p.line("M120 840 L880 840")
    p.poly([(320, 250), (300, 110), (430, 200)])
    p.poly([(680, 250), (700, 110), (570, 200)])
    p.e(500, 530, 260, 320)
    p.e(255, 600, 75, 170, 14)
    p.e(745, 600, 75, 170, -14)
    p.e(400, 440, 92)
    p.e(600, 440, 92)
    p.e(400, 440, 42)
    p.e(600, 440, 42)
    p.dot(405, 445, 22)
    p.dot(605, 445, 22)
    p.poly([(465, 520), (535, 520), (500, 595)])
    if not p.simple:
        for row in range(3):
            for k in range(3):
                x = 400 + k * 100 - (50 if row % 2 else 0) + (50 if row % 2 else 0)
                p.line(f"M{x - 38} {660 + row * 52} q38 38 76 0")
    p.e(420, 835, 52, 30)
    p.e(580, 835, 52, 30)
    if r.random() < .5:
        p.e(800, 810, 45, 22, -30)
        p.line("M770 835 L720 840")
    return p.svg()


def snail(p: Pen) -> str:
    r = p.rng
    p.e(520, 820, 380, 70)
    p.band("M780 790 C860 760 870 640 860 560", 110)
    p.e(865, 540, 75)
    p.line("M845 470 Q820 390 790 350")
    p.line("M890 470 Q925 390 950 350")
    p.e(790, 335, 24)
    p.e(950, 335, 24)
    p.dot(855, 530, 15)
    p.smile(880, 575, 28)
    p.e(480, 520, 245)
    p.line("M480 520 a38 38 0 1 1 76 0 a76 76 0 1 1 -152 0 a114 114 0 1 1 228 0 a152 152 0 1 1 -304 0")
    if r.random() < .6:
        for k in range(3):
            p.e(150 + k * 60, 235 + (k % 2) * 40, 22)
    return p.svg()


def ladybug(p: Pen) -> str:
    r = p.rng
    for s in (-1, 1):
        p.line(f"M{500 + s * 300} 520 L{500 + s * 400} 450")
        p.line(f"M{500 + s * 290} 640 L{500 + s * 405} 650")
        p.line(f"M{500 + s * 250} 760 L{500 + s * 350} 840")
        p.line(f"M{500 + s * 70} 160 Q{500 + s * 100} 70 {500 + s * 190} 70")
    p.e(500, 255, 160, 115)
    p.e(500, 570, 310, 300)
    p.line("M500 275 L500 870")
    p.eyes(440, 560, 235, 14)
    p.smile(500, 275, 40)
    for side in (-1, 1):
        p.spots((500 + (30 if side > 0 else -300), 330, 500 + (300 if side > 0 else -30), 840), 2 if p.simple else r.randint(3, 4), 35, 60)
    return p.svg()


def whale(p: Pen) -> str:
    p.e(870, 395, 65, 135, 32)
    p.e(880, 575, 65, 135, -32)
    p.e(450, 590, 345, 230)
    p.e(330, 555, 24)
    p.dot(335, 557, 15)
    p.smile(310, 650, 70)
    p.e(540, 790, 70, 38, -10)
    if not p.simple:
        for k in range(3):
            p.line(f"M{400 + k * 70} 700 q40 40 80 0")
    p.line("M470 360 L470 270")
    p.line("M470 270 Q420 220 390 230")
    p.line("M470 270 Q520 220 550 230")
    p.e(380, 215, 20)
    p.e(560, 215, 20)
    p.e(470, 180, 16)
    return p.svg()


def octopus(p: Pen) -> str:
    r = p.rng
    for i, x in enumerate((230, 330, 430, 570, 670, 770)):
        sway = 70 if i % 2 else -70
        p.band(f"M{x} 520 C{x + sway} 640 {x - sway} 760 {x + sway * .6:.0f} 880", 60)
    p.e(500, 340, 235, 265)
    p.eyes(405, 595, 330, 20)
    p.e(405, 330, 45)
    p.e(595, 330, 45)
    p.dot(410, 335, 22)
    p.dot(600, 335, 22)
    p.smile(500, 450, 70)
    p.spots((300, 130, 700, 260), 3, 18, 34)
    return p.svg()


def rocket(p: Pen) -> str:
    r = p.rng
    p.poly([(365, 500), (230, 740), (370, 680)])
    p.poly([(635, 500), (770, 740), (630, 680)])
    p.path("M500 70 C660 210 680 420 650 650 L350 650 C320 420 340 210 500 70 Z")
    p.e(500, 360, 85)
    p.e(500, 360, 45)
    p.line("M352 540 L648 540")
    p.poly([(400, 650), (600, 650), (570, 710), (430, 710)])
    p.path("M440 720 C430 810 500 900 500 900 C500 900 570 810 560 720 Z")
    for x, y in ([] if p.simple else r.sample([(150, 170), (850, 200), (130, 500), (870, 520), (800, 860), (190, 850)], 4)):
        p.poly(_star_pts(x + r.randint(-20, 20), y + r.randint(-20, 20), r.randint(45, 65)))
    return p.svg()


def car(p: Pen) -> str:
    r = p.rng
    p.path("M290 480 L380 320 Q395 295 430 295 L620 295 Q655 295 675 325 L760 480 Z")
    p.poly([(405, 340), (490, 340), (490, 465), (350, 465)])
    p.poly([(530, 340), (625, 340), (690, 465), (530, 465)])
    p.rect(110, 460, 780, 200, 55)
    p.e(840, 540, 30)
    p.e(165, 540, 24)
    p.line("M400 560 L600 560")
    for x in (300, 700):
        p.e(x, 680, 105)
        p.e(x, 680, 45)
    if r.random() < .6:
        p.line("M420 298 L420 250 L480 250")
        p.e(500, 250, 22)
    return p.svg()


def robot(p: Pen) -> str:
    r = p.rng
    p.line("M500 140 L500 80")
    p.e(500, 65, 28)
    p.rect(335, 140, 330, 250, 50)
    p.rect(385, 210, 90, 80, 14)
    p.rect(525, 210, 90, 80, 14)
    p.dot(430, 250, 18)
    p.dot(570, 250, 18)
    p.rect(420, 320, 160, 40, 12)
    if not p.simple:
        p.line("M460 320 L460 360")
        p.line("M500 320 L500 360")
        p.line("M540 320 L540 360")
    p.rect(450, 390, 100, 40)
    p.band("M310 470 Q220 540 250 640", 55)
    p.band("M690 470 Q780 540 750 640", 55)
    p.rect(300, 430, 400, 300, 40)
    p.e(380, 540, 38)
    p.e(500, 540, 38)
    p.e(620, 540, 38)
    p.line("M360 650 L640 650")
    p.rect(365, 730, 90, 150, 14)
    p.rect(545, 730, 90, 150, 14)
    p.e(235, 665, 42)
    p.e(765, 665, 42)
    if r.random() < .5:
        p.poly(_star_pts(500, 650, 20))
    return p.svg()


def dino(p: Pen) -> str:
    r = p.rng
    p.poly([(240, 610), (60, 740), (270, 520)])
    for i in range(5):   # back plates
        x = 300 + i * 85
        y = 470 - abs(i - 2) * 22 + 20
        p.poly([(x - 40, y), (x, y - 95), (x + 40, y)])
    p.e(480, 620, 270, 210)
    p.band("M640 520 C720 470 740 400 735 330", 130)
    p.e(760, 260, 140, 105, -8)
    p.dot(815, 235, 18)
    p.smile(790, 300, 42)
    p.e(405, 815, 62, 90)
    p.e(590, 815, 62, 90)
    if not p.simple:
        p.spots((300, 540, 640, 760), 3, 20, 38)
    return p.svg()


def flower(p: Pen) -> str:
    r = p.rng
    petals = 5 if p.simple else r.randint(5, 8)
    p.band("M500 520 C480 650 530 760 500 900", 34)
    p.e(380, 730, 95, 40, -28)
    p.e(630, 650, 95, 40, 28)
    for i in range(petals):
        a = 2 * math.pi * i / petals - math.pi / 2
        p.e(500 + 170 * math.cos(a), 360 + 170 * math.sin(a), 105, 62, math.degrees(a))
    p.e(500, 360, 105)
    if r.random() < .7:
        p.eyes(465, 535, 345, 12)
        p.smile(500, 375, 38)
    return p.svg()


def house(p: Pen) -> str:
    r = p.rng
    p.rect(630, 150, 70, 160)
    p.rect(250, 430, 500, 390)
    p.poly([(190, 440), (500, 190), (810, 440)])
    p.rect(430, 600, 140, 220, 8)
    p.dot(540, 715, 12)
    for x in (300, 600):
        p.rect(x, 500, 100, 100)
        p.line(f"M{x + 50} 500 L{x + 50} 600")
        p.line(f"M{x} 550 L{x + 100} 550")
    p.e(500, 335, 38)
    p.line("M470 820 Q440 900 340 925")
    p.line("M530 820 Q560 900 660 925")
    if r.random() < .6:
        p.e(120, 780, 55)
        p.line("M120 835 L120 910")
    return p.svg()


def icecream(p: Pen) -> str:
    r = p.rng
    p.poly([(330, 520), (670, 520), (500, 930)])
    if not p.simple:   # waffle crosshatch: lines from one edge of the cone to the other
        L = lambda t: (330 + 170 * t, 520 + 410 * t)   # noqa: E731
        R = lambda t: (670 - 170 * t, 520 + 410 * t)   # noqa: E731
        for t in (.0, .22, .44, .66):
            (x1, y1), (x2, y2) = L(t), R(t + .3)
            (x3, y3), (x4, y4) = R(t), L(t + .3)
            p.line(f"M{x1:.0f} {y1:.0f} L{x2:.0f} {y2:.0f}")
            p.line(f"M{x3:.0f} {y3:.0f} L{x4:.0f} {y4:.0f}")
    p.e(500, 400, 185)
    for k in range(5):
        p.e(335 + k * 82, 530, 45)
    if not p.simple:
        p.e(500, 250, 135)
    cy = 105 if not p.simple else 215
    p.e(500, cy, 40)
    p.line(f"M500 {cy - 30} Q530 {cy - 90} 600 {cy - 100}")
    for _ in range(0 if p.simple else 8):
        x, y = r.uniform(380, 620), r.uniform(330, 470)
        a = r.uniform(0, math.pi)
        p.line(f"M{x:.0f} {y:.0f} l{20 * math.cos(a):.0f} {20 * math.sin(a):.0f}")
    return p.svg()


def frog(p: Pen) -> str:
    r = p.rng
    p.e(250, 800, 90, 45, -10)
    p.e(750, 800, 90, 45, 10)
    p.e(500, 650, 270, 200)
    p.e(260, 640, 70, 120, 24)
    p.e(740, 640, 70, 120, -24)
    p.e(500, 450, 240, 165)
    for x in (360, 640):
        p.e(x, 290, 75)
        p.e(x, 290, 36)
        p.dot(x + 4, 292, 17)
    p.dot(450, 410, 10)
    p.dot(550, 410, 10)
    p.line("M330 500 Q500 640 670 500")
    if not p.simple:
        p.spots((380, 580, 640, 760), r.randint(2, 4), 18, 32)
    return p.svg()


def bunny(p: Pen) -> str:
    r = p.rng
    tilt = r.choice([-10, 0, 12])
    p.e(385, 215, 62, 175, -8 + tilt)
    p.e(615, 215, 62, 175, 8 + tilt)
    p.e(385, 225, 28, 125, -8 + tilt)
    p.e(615, 225, 28, 125, 8 + tilt)
    p.e(500, 770, 220, 190)
    p.e(380, 905, 85, 38)
    p.e(620, 905, 85, 38)
    p.e(500, 470, 190, 165)
    p.eyes(425, 575, 440, 20)
    p.poly([(478, 500), (522, 500), (500, 530)])
    p.line("M500 530 L500 560")
    p.line("M500 560 Q470 595 440 570")
    p.line("M500 560 Q530 595 560 570")
    p.line("M330 520 L240 505")
    p.line("M670 520 L760 505")
    if r.random() < .6:
        _bow(p, 500, 650, .7)
    if not p.simple:
        p.e(500, 790, 105, 100)
    return p.svg()


def bear(p: Pen) -> str:
    r = p.rng
    for x in (320, 680):
        p.e(x, 270, 75)
        p.e(x, 275, 36)
    p.e(500, 760, 230, 190)
    if not p.simple:
        p.e(500, 790, 130, 120)
    p.e(300, 900, 70, 45)
    p.e(700, 900, 70, 45)
    p.e(500, 440, 205)
    p.e(500, 510, 95, 72)
    p.eyes(415, 585, 410, 20)
    p.e(500, 480, 30, 22, 0)
    p.line("M500 502 L500 540")
    p.line("M500 540 Q470 575 440 548")
    p.line("M500 540 Q530 575 560 548")
    if r.random() < .5:
        p.poly(_star_pts(500, 770, 55, .5))
    return p.svg()


def penguin(p: Pen) -> str:
    r = p.rng
    p.e(380, 905, 70, 32)
    p.e(620, 905, 70, 32)
    p.e(500, 560, 235, 340)
    p.e(500, 650, 150, 245)
    p.e(255, 600, 60, 170, 12)
    p.e(745, 600, 60, 170, -12)
    p.eyes(415, 585, 330, 22)
    p.poly([(455, 400), (545, 400), (500, 470)])
    p.line("M360 280 Q500 215 640 280")
    if r.random() < .6:
        p.line("M300 480 Q500 540 700 480", 22)
        p.line("M300 480 Q500 540 700 480")
    if not p.simple:
        for k in range(3):
            p.line(f"M{440 + k * 60} 610 q10 14 20 0")
    return p.svg()


def duck(p: Pen) -> str:
    r = p.rng
    p.line("M60 880 Q180 840 300 880 T540 880 T780 880 T950 862")
    p.path("M215 590 L100 470 L260 520 Z")
    p.e(470, 670, 290, 175)
    p.e(700, 410, 118)
    p.e(815, 450, 78, 30, 12)
    p.line("M745 452 Q800 470 855 452")
    p.dot(722, 372, 18)
    p.path("M330 630 Q420 520 590 610 Q560 740 400 720 Q330 700 330 630 Z")
    if not p.simple:
        p.line("M410 640 Q470 590 540 625")
    for x in (400, 560):
        p.line(f"M{x} 840 L{x} 880 M{x - 34} 880 L{x + 34} 880")
    if r.random() < .5:
        p.poly(_star_pts(690, 255, 36, .5))
    return p.svg()

def elephant(p: Pen) -> str:
    r = p.rng
    p.rect(250, 700, 100, 200, 30)
    p.rect(520, 700, 100, 200, 30)
    p.e(450, 590, 290, 210)
    p.line("M180 540 Q110 600 140 700")
    p.rect(380, 760, 100, 150, 30)
    p.rect(630, 740, 100, 160, 30)
    p.band("M780 480 C860 560 880 700 830 790", 80)
    p.e(700, 410, 175, 170)
    p.e(570, 420, 115, 175, 12)
    p.dot(760, 370, 20)
    if not p.simple:
        p.line("M650 490 Q720 520 760 500")
    return p.svg()


def giraffe(p: Pen) -> str:
    r = p.rng
    for x in (260, 340, 560, 640):
        p.rect(x, 700, 56, 230, 18)
    p.line("M180 590 Q130 650 150 730")
    p.band("M520 600 C560 450 600 320 640 200", 130)
    p.e(450, 640, 270, 150)
    p.e(690, 160, 120, 78, 18)
    p.e(790, 195, 40, 28, 18)
    p.line("M640 95 L630 40")
    p.line("M690 85 L705 30")
    p.e(626, 36, 12)
    p.e(706, 28, 12)
    p.e(590, 150, 32, 55, -30)
    p.dot(715, 140, 14)
    p.spots((300, 540, 600, 740), 4 if not p.simple else 2, 28, 46)
    if not p.simple:
        p.spots((560, 250, 640, 560), 3, 18, 28)
    return p.svg()


def lion(p: Pen) -> str:
    r = p.rng
    p.e(500, 820, 190, 130)
    p.e(380, 920, 70, 38)
    p.e(620, 920, 70, 38)
    for k in range(14):
        a = math.radians(k * 360 / 14)
        p.e(500 + 245 * math.cos(a), 450 + 245 * math.sin(a), 70)
    p.e(500, 450, 185)
    for x in (360, 640):
        p.e(x, 300, 42)
    p.e(500, 520, 80, 60)
    p.eyes(425, 575, 410, 20)
    p.poly([(475, 470), (525, 470), (500, 500)])
    p.line("M500 500 L500 540")
    p.line("M500 540 Q470 575 440 548")
    p.line("M500 540 Q530 575 560 548")
    return p.svg()


def bee(p: Pen) -> str:
    r = p.rng
    p.e(410, 330, 90, 150, -24)
    p.e(590, 330, 90, 150, 24)
    p.poly([(770, 580), (900, 560), (780, 630)])
    p.e(500, 590, 260, 170)
    for x in (430, 530, 630):
        h = 170 * math.sqrt(max(0, 1 - ((x - 500) / 260) ** 2))
        p.line(f"M{x} {590 - h + 6:.0f} L{x} {590 + h - 6:.0f}", p.w * 2.2)
    p.e(255, 600, 105)
    p.eyes(220, 295, 585, 16)
    p.smile(255, 630, 36)
    p.line("M225 505 Q190 430 140 420")
    p.line("M290 505 Q310 430 350 410")
    p.e(133, 420, 16)
    p.e(356, 408, 16)
    p.line("M120 900 q60 -40 120 0 t120 0")
    return p.svg()


def crab(p: Pen) -> str:
    r = p.rng
    for sd in (-1, 1):
        for k in range(3):
            y = 590 + k * 70
            p.band(f"M{500 + sd * 200} {y} Q{500 + sd * 330} {y + 10} {500 + sd * (360 + k * 20)} {y + 90}", 30)
        p.band(f"M{500 + sd * 190} 500 Q{500 + sd * 330} 470 {500 + sd * 350} 340", 40)
        cx, cy = 500 + sd * 350, 270
        p.e(cx, cy, 100, 82, sd * 15)
        p.line(f"M{cx - sd * 15} {cy + 78} L{cx + sd * 55} {cy - 5} L{cx - sd * 25} {cy - 78}")
    p.e(500, 620, 280, 175)
    for x in (415, 585):
        p.line(f"M{x} 470 L{x} 395")
        p.e(x, 372, 36)
        p.dot(x + (4 if x > 500 else -4), 374, 15)
    p.smile(500, 620, 85)
    if not p.simple:
        p.spots((350, 540, 650, 600), 3, 12, 20)
    return p.svg()

def shark(p: Pen) -> str:
    r = p.rng
    p.line("M60 860 Q180 820 300 860 T540 860 T780 860 T950 845")
    p.poly([(790, 560), (940, 400), (930, 700)])
    p.poly([(440, 450), (540, 230), (640, 450)])
    p.poly([(360, 700), (420, 800), (520, 690)])
    p.e(480, 570, 360, 175)
    p.e(330, 520, 24)
    p.dot(334, 522, 14)
    p.line("M150 640 L210 610 L250 650 L310 615 L360 655 L410 620")
    for k in range(3):
        p.line(f"M{560 + k * 28} 500 q-14 40 0 80")
    return p.svg()


def airplane(p: Pen) -> str:
    r = p.rng
    for cx, cy, s in ((180, 190, 1.0), (840, 790, .9)):
        p.path(f"M{cx - 110 * s} {cy + 30 * s} a50 50 0 0 1 20 -85 a70 70 0 0 1 130 -20 a55 55 0 0 1 90 45 a38 38 0 0 1 0 60 Z")
    p.poly([(250, 560), (120, 380), (200, 380), (400, 560)])
    p.poly([(420, 520), (560, 250), (680, 250), (640, 520)])
    p.poly([(420, 640), (560, 880), (680, 880), (640, 640)])
    p.e(500, 570, 380, 90, -6)
    p.poly([(790, 520), (910, 540), (800, 600)])
    for k in range(5):
        p.e(330 + k * 75, 560 - k * 8, 22)
    p.e(790, 530, 36, 30, -10)
    return p.svg()


def sailboat(p: Pen) -> str:
    r = p.rng
    p.poly(_star_pts(800, 170, 70, .45, 6))
    p.line("M500 160 L500 640", 14)
    p.poly([(500, 190), (500, 600), (230, 600)])
    p.poly([(530, 280), (530, 600), (730, 600)])
    p.poly([(500, 160), (590, 195), (500, 230)])
    p.path("M150 640 L850 640 Q780 800 640 800 L360 800 Q220 800 150 640 Z")
    p.line("M250 700 L750 700")
    for k, y in enumerate((850, 910)):
        p.line(f"M{50 + k * 60} {y} q60 -50 120 0 t120 0 t120 0 t120 0 t120 0 t120 0")
    return p.svg()


def train(p: Pen) -> str:
    r = p.rng
    for k, cx in enumerate((690, 800, 880)):
        p.e(cx, 170 - k * 50, 50 + k * 15)
    p.rect(120, 460, 230, 220, 14)
    p.rect(150, 490, 70, 80, 10)
    p.rect(380, 380, 270, 300, 18)
    p.rect(410, 410, 90, 90, 10)
    p.rect(530, 410, 90, 90, 10)
    p.rect(660, 440, 130, 240, 20)
    p.rect(700, 280, 90, 110, 12)
    p.rect(680, 240, 130, 50, 12)
    p.rect(60, 680, 800, 40, 8)
    for cx in (200, 380, 540, 740):
        p.e(cx, 740, 66)
        p.e(cx, 740, 24)
    p.line("M40 830 L900 830")
    for k in range(10):
        p.line(f"M{70 + k * 90} 800 L{70 + k * 90} 860")
    return p.svg()


def cupcake(p: Pen) -> str:
    r = p.rng
    p.poly([(250, 590), (750, 590), (670, 900), (330, 900)])
    for x in (330, 410, 500, 590, 670):
        p.line(f"M{x} 590 L{250 + (x - 250) * .8 + 40:.0f} 900")
    p.e(500, 560, 290, 85)
    p.e(500, 440, 230, 90)
    p.e(500, 330, 160, 80)
    p.e(500, 190, 34)
    p.line("M500 160 Q540 100 600 90")
    if not p.simple:
        for _ in range(8):
            x, y, a = r.uniform(360, 640), r.uniform(310, 520), r.uniform(0, math.pi)
            p.line(f"M{x:.0f} {y:.0f} l{26 * math.cos(a):.0f} {26 * math.sin(a):.0f}", p.w * 1.4)
    return p.svg()


def mushroom(p: Pen) -> str:
    r = p.rng
    p.line("M120 880 L880 880")
    p.line("M180 880 l-20 -50 M820 880 l20 -50 M240 880 l10 -35")
    p.path("M380 520 Q360 800 400 880 L600 880 Q640 800 620 520 Z")
    p.path("M110 520 C110 200 890 200 890 520 Z")
    p.line("M110 520 L890 520")
    p.spots((200, 310, 800, 480), 3 if p.simple else r.randint(4, 6), 40, 70)
    p.eyes(450, 550, 640, 14)
    p.smile(500, 680, 40)
    return p.svg()


def unicorn(p: Pen) -> str:
    r = p.rng
    p.band("M250 580 C140 600 90 700 130 800", 70)
    for x in (300, 380, 590, 670):
        p.rect(x, 700, 54, 210, 18)
    p.e(480, 640, 260, 160)
    p.band("M620 560 C650 450 680 370 700 300", 120)
    p.e(730, 250, 120, 85, 28)
    p.poly([(720, 180), (770, 30), (810, 170)])
    p.poly([(655, 190), (630, 120), (700, 160)])
    p.dot(760, 240, 15)
    for k in range(5):
        p.e(610 - k * 10 + (k % 2) * 25, 200 + k * 80, 36)
    p.line("M770 300 q-25 20 -45 4")
    if r.random() < .6:
        p.poly(_star_pts(480, 640, 44, .5))
    return p.svg()


def pizza(p: Pen) -> str:
    r = p.rng
    p.path("M500 900 L110 240 Q500 100 890 240 Z")
    p.path("M110 240 Q500 100 890 240 L860 190 Q500 40 140 190 Z")
    for x, y, rr in ((500, 330, 62), (380, 470, 55), (620, 480, 55), (500, 640, 50), (450, 230, 24), (620, 270, 28)):
        p.e(x, y, rr)
        if not p.simple and rr > 40:
            p.dot(x, y, 10)
    return p.svg()


def apple(p: Pen) -> str:
    r = p.rng
    p.line("M500 280 Q490 190 540 120", 18)
    p.e(640, 190, 100, 44, -28)
    p.path("M500 300 C380 220 160 270 170 540 C175 760 340 900 440 880 Q500 860 560 880 C660 900 825 760 830 540 C840 270 620 220 500 300 Z")
    p.eyes(410, 590, 560, 20)
    p.smile(500, 640, 70)
    p.e(320, 450, 40, 70, 24)
    return p.svg()


def ufo(p: Pen) -> str:
    r = p.rng
    p.poly([(400, 640), (330, 880), (670, 880), (600, 640)])
    p.path("M340 400 C340 180 660 180 660 400 Z")
    p.e(500, 460, 400, 110)
    for k in range(5):
        p.e(200 + k * 150, 470, 24)
    p.e(500, 320, 80, 55)
    p.dot(500, 330, 14)
    for x, y in ((140, 180), (860, 230), (120, 700), (880, 660)):
        p.poly(_star_pts(x, y, 46, .45))
    return p.svg()


def planet(p: Pen) -> str:
    p.e(500, 500, 400, 105, -22)   # the ring, behind the planet
    p.e(500, 500, 230)
    p.line("M120 590 A400 105 -22 0 0 880 410")   # the front half of the ring
    if not p.simple:
        p.spots((380, 330, 620, 450), 3, 20, 36)
    p.eyes(440, 560, 520, 15)
    p.smile(500, 560, 40)
    for x, y in ((150, 160), (860, 190), (200, 860), (840, 820)):
        p.poly(_star_pts(x, y, 44, .45))
    return p.svg()


def balloons(p: Pen) -> str:
    r = p.rng
    pts = [(300, 330, 150), (500, 250, 165), (700, 340, 150)]
    for i, (x, y, rr) in enumerate(pts):
        p.line(f"M{x} {y + rr * 1.15:.0f} Q{500 + (x - 500) * .3:.0f} 760 500 900", p.w * .7)
    for x, y, rr in pts:
        p.e(x, y, rr * .85, rr * 1.05)
        p.poly([(x - 20, y + rr * 1.05), (x + 20, y + rr * 1.05), (x, y + rr * 1.05 + 30)])
        p.e(x - rr * .3, y - rr * .35, 22, 34, 30)
    if not p.simple:
        p.poly(_star_pts(500, 920, 40, .5))
    return p.svg()


_FIGURES = {"cat": cat, "fish": fish, "butterfly": butterfly, "turtle": turtle, "owl": owl, "snail": snail, "ladybug": ladybug, "whale": whale,
            "octopus": octopus, "rocket": rocket, "car": car, "robot": robot, "dino": dino, "flower": flower, "house": house, "icecream": icecream,
            "frog": frog, "bunny": bunny, "bear": bear, "penguin": penguin, "duck": duck, "elephant": elephant, "giraffe": giraffe, "lion": lion, "bee": bee,
            "crab": crab, "shark": shark, "airplane": airplane, "sailboat": sailboat, "train": train, "cupcake": cupcake, "mushroom": mushroom,
            "unicorn": unicorn, "pizza": pizza, "apple": apple, "ufo": ufo, "planet": planet, "balloons": balloons}


def figure(kind: str, seed: int, width: float = 10, simple: bool = False) -> str:
    """The shapes of one figure (no svg wrapper), different for every seed."""
    return _FIGURES[kind](Pen(random.Random(seed), width, simple))


# --------------------------------------------------------------------------- decoration, shapes and pages
def _decor(p: Pen, spot: tuple[float, float], kind: str, size: float) -> None:
    x, y = spot
    if kind == "cloud":
        x = min(max(x, 170), 830)
    if kind == "star":
        p.poly(_star_pts(x, y, size * .5))
    elif kind == "heart":
        s = size / 100
        p.path(f"M{x} {y + 38 * s} C{x - 85 * s} {y - 15 * s} {x - 45 * s} {y - 70 * s} {x} {y - 28 * s} C{x + 45 * s} {y - 70 * s} {x + 85 * s} {y - 15 * s} {x} {y + 38 * s} Z")
    elif kind == "cloud":
        s = size / 200
        p.path(f"M{x - 125 * s} {y + 40 * s} a40 40 0 0 1 20 -75 a60 60 0 0 1 110 -20 a50 50 0 0 1 80 40 a35 35 0 0 1 0 55 Z")
    elif kind == "sun":
        for i in range(8):
            a = math.radians(45 * i)
            p.line(f"M{x + math.cos(a) * size * .62:.0f} {y + math.sin(a) * size * .62:.0f} L{x + math.cos(a) * size * .9:.0f} {y + math.sin(a) * size * .9:.0f}")
        p.e(x, y, size * .42)
    else:
        p.e(x, y, size * .3)


def _frame(inner: str, scale: float = .8) -> str:
    t = 500 * (1 - scale)
    return f"<g transform='translate({t:.0f} {t + 10:.0f}) scale({scale})'>{inner}</g>"


def _wrap(inner: str) -> str:
    return f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 1000' preserveAspectRatio='xMidYMid meet'>{inner}</svg>"


def figure_page(kind: str, seed: int, width: float, simple: bool) -> str:
    rng = random.Random(seed + 7)
    deco = Pen(rng, width * .8, simple)
    corners = [(100, 100), (900, 100), (100, 900), (900, 900)]
    rng.shuffle(corners)
    for spot, k in zip(corners[: 2 if simple else 4], rng.sample(["star", "heart", "cloud", "sun", "dot", "star"], 4)):
        _decor(deco, spot, k, 105 if k != "cloud" else 150)
    return _wrap(deco.svg() + _frame(figure(kind, seed, width / .88, simple), .88))


def cover_art(kind: str, seed: int, width: float, simple: bool) -> str:
    """One big figure with no corner decoration, for the cover circle."""
    return _wrap(_frame(figure(kind, seed, width / .9, simple), .9))


def scene_page(kinds: list[str], seed: int, width: float, simple: bool) -> str:
    spots = [(260, 250), (740, 330), (470, 740)] if len(kinds) == 3 else [(260, 260), (740, 260), (260, 740), (740, 740)]
    out = []
    for i, (k, (x, y)) in enumerate(zip(kinds, spots)):
        s = .58
        out.append(f"<g transform='translate({x - 500 * s:.0f} {y - 500 * s:.0f}) scale({s})'>{figure(k, seed * 3 + i, width / s * .8, True)}</g>")
    return _wrap("".join(out))


def shape_face(p: Pen, shape: str, cx: float, cy: float, r: float) -> None:
    if shape == "circle":
        p.e(cx, cy, r)
    elif shape == "square":
        p.rect(cx - r * .85, cy - r * .85, r * 1.7, r * 1.7, r * .12)
    elif shape == "triangle":
        p.poly([(cx, cy - r), (cx + r * .95, cy + r * .8), (cx - r * .95, cy + r * .8)])
        cy += r * .2
    elif shape == "star":
        p.poly(_star_pts(cx, cy, r * 1.05, .5))
    elif shape == "heart":
        s = r / 55
        p.path(f"M{cx} {cy + 55 * s} C{cx - 120 * s} {cy - 20 * s} {cx - 60 * s} {cy - 100 * s} {cx} {cy - 40 * s} C{cx + 60 * s} {cy - 100 * s} {cx + 120 * s} {cy - 20 * s} {cx} {cy + 55 * s} Z")
    elif shape == "oval":
        p.e(cx, cy, r * 1.05, r * .7)
    elif shape == "diamond":
        p.poly([(cx, cy - r * 1.1), (cx + r * .8, cy), (cx, cy + r * 1.1), (cx - r * .8, cy)])
    else:
        p.poly([(cx + r * math.cos(math.radians(60 * i)), cy + r * math.sin(math.radians(60 * i))) for i in range(6)])
    p.eyes(cx - r * .3, cx + r * .3, cy - r * .12, p.w * 1.3)
    p.smile(cx, cy + r * .12, r * .26)


def shapes_page(seed: int, width: float, which: list[str]) -> str:
    p = Pen(random.Random(seed), width)
    cells = [(270, 230), (730, 230), (270, 590), (730, 590)] if len(which) == 4 else [(180, 250), (500, 250), (820, 250), (180, 640), (500, 640), (820, 640)]
    r = 120 if len(which) == 4 else 86
    for shape, (cx, cy) in zip(which, cells):
        shape_face(p, shape, cx, cy, r * (1.3 if len(which) == 4 else 1.2))
    labels = "".join(f"<text x='{cx}' y='{cy + (230 if len(which) == 4 else 190)}' text-anchor='middle' font-family='Helvetica, Arial, sans-serif' font-weight='700' font-size='{52 if len(which) == 4 else 46}' fill='{INK}'>{s.title()}</text>"
                     for s, (cx, cy) in zip(which, cells))
    return _wrap(p.svg() + labels)


def count_page(kind: str, n: int, seed: int, width: float) -> str:
    cols = 2 if n <= 4 else 3
    rows = math.ceil(n / cols)
    cell = 400 if cols == 2 else 270
    x0 = 500 - (min(n, cols) - 1) * cell / 2
    y0 = 600 - (rows - 1) * cell / 2 - 20
    out = [f"<text x='500' y='215' text-anchor='middle' font-family='Helvetica, Arial, sans-serif' font-weight='800' font-size='260' fill='#ffffff' stroke='{INK}' stroke-width='{width * .8}' stroke-linejoin='round'>{n}</text>"]
    s = cell * (.95 if cols == 2 else 1.05) / 1000
    for i in range(n):
        cx, cy = x0 + (i % cols) * cell, y0 + (i // cols) * cell
        out.append(f"<g transform='translate({cx - 500 * s:.0f} {cy - 500 * s:.0f}) scale({s:.3f})'>{figure(kind, seed * 5 + i, width / s * .55, True)}</g>")
    return _wrap("".join(out))


def trace_page(seed: int, width: float) -> str:
    rng = random.Random(seed)
    which = rng.sample(["circle", "square", "triangle", "star", "heart", "diamond"], 3)
    out = []
    for shape, (cx, cy) in zip(which, [(500, 210), (260, 640), (740, 640)]):
        p = Pen(rng, width)
        shape_face(p, shape, cx, cy, 160)
        body = p.svg().replace(f"fill='#ffffff' stroke='{INK}'", f"fill='none' stroke='{INK}' stroke-dasharray='1 {width * 2.6:.0f}'")
        out.append(body)
    return _wrap("".join(out))


def page_plan(i: int) -> str:
    """Page kind for page number i: mostly big figures, with a shapes, count, scene or trace page now and then."""
    return ["figure", "figure", "scene", "figure", "count", "figure", "shapes", "figure", "figure", "trace"][i % 10]


def page_art(i: int, seed: int, theme: str = "mixed", age: str = "kids") -> tuple[str, str, str]:
    """(kind, svg, caption) for page number i of a children's coloring book. Figures cycle through the theme's list in a seeded shuffle, so the
    same figure never repeats until all have been used, and each one is drawn with different details."""
    width = AGES.get(age, 10)
    simple = age == "toddler"
    pool = list(THEMES.get(theme, THEMES["mixed"])[1])
    order = pool[:]
    random.Random(seed).shuffle(order)
    plan = page_plan(i)
    rng = random.Random(seed * 131 + i)
    n_fig = sum(1 for j in range(i) if page_plan(j) == "figure")
    if plan == "figure":
        kind = order[n_fig % len(order)]
        return "figure", figure_page(kind, seed * 977 + i, width, simple), f"Color the {NAMES[kind]}!"
    if plan == "scene":
        kinds = [order[(n_fig + k) % len(order)] for k in range(3)]
        return "scene", scene_page(kinds, seed * 977 + i, width, simple), "Color all the friends!"
    if plan == "count":
        kind = rng.choice(pool)
        n = rng.randint(2, 5) if simple else rng.randint(3, 9)
        word = PLURALS.get(kind, NAMES[kind] + "s")
        return "count", count_page(kind, n, seed * 977 + i, width), f"Color {n} {word}!"
    if plan == "shapes":
        which = rng.sample(SHAPES, 4 if simple else 6)
        return "shapes", shapes_page(seed * 977 + i, width, which), "Color the shape friends!"
    return "trace", trace_page(seed * 977 + i, width), "Trace the dots, then color!"


from . import kidsart_extra  # noqa: E402,F401  (registers the extra figures and themes)
