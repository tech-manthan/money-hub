"""Room mockups for art listings: your artwork framed in flat-illustration rooms (living room, gallery wall, shelf, bedroom), drawn in the
product's colours. Scenes are HTML/CSS shapes rendered with WeasyPrint, so they are sharp at any size and need no photo templates."""
from __future__ import annotations

import base64
import io
import tempfile
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

from ..design import Palette
from .pdf import render_pdf

W, H = 2700, 2025
SCENES = ["sofa", "gallery", "shelf", "bedroom"]
GREENS = ("#3f7a55", "#5c9a6e", "#2f6b45")
WOOD = "#b98f63"


def _rgb(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def mix(a: str, b: str, t: float) -> str:
    ra, rb = _rgb(a), _rgb(b)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ra, rb))


def _uri(im: Image.Image, height: int = 1100) -> str:
    im = im.convert("RGB")
    im = im.resize((round(im.width * height / im.height), height), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


class _Scene:
    def __init__(self, pal: Palette):
        self.pal = pal
        self.parts: list[str] = []
        self.wall = mix(pal.soft, "#ffffff", .45)
        self.floor = mix(WOOD, self.wall, .35)

    def box(self, x, y, w, h, bg, r=0, rot=0, extra=""):
        t = f"transform:rotate({rot}deg);" if rot else ""
        self.parts.append(f"<div style='position:absolute;left:{x:.0f}px;top:{y:.0f}px;width:{w:.0f}px;height:{h:.0f}px;background:{bg};border-radius:{r}px;{t}{extra}'></div>")

    def ellipse(self, cx, cy, rx, ry, bg, rot=0):
        self.box(cx - rx, cy - ry, rx * 2, ry * 2, bg, r=max(rx, ry), rot=rot)

    def room(self, floor_y=1560):
        self.box(0, 0, W, H, self.wall)
        self.box(0, floor_y, W, H - floor_y, self.floor)
        self.box(0, floor_y - 18, W, 18, mix(self.wall, "#000000", .08))   # skirting

    def frame(self, x, y, inner_w, art: str, fcol="#2b2622", mat="#fdfbf7", bw=26, mw=46):
        inner_h = inner_w * 1.25
        w, h = inner_w + 2 * (bw + mw), inner_h + 2 * (bw + mw)
        self.box(x + 16, y + 24, w, h, "rgba(0,0,0,.15)", 4)
        self.box(x, y, w, h, fcol, 4)
        self.box(x + bw, y + bw, w - 2 * bw, h - 2 * bw, mat)
        self.box(x + bw + mw - 3, y + bw + mw - 3, inner_w + 6, inner_h + 6, "rgba(0,0,0,.08)")
        self.parts.append(f"<img src='{art}' style='position:absolute;left:{x + bw + mw:.0f}px;top:{y + bw + mw:.0f}px;width:{inner_w:.0f}px;height:{inner_h:.0f}px;object-fit:cover'>")
        return w, h

    def plant(self, x, y, s=1.0, pot=None):
        pot = pot or self.pal.accent2
        for k, (dx, dy, rx, ry, rot, g) in enumerate([(0, -250, 34, 150, 0, 0), (-70, -200, 30, 130, -32, 1), (70, -200, 30, 130, 32, 1), (-125, -130, 28, 105, -58, 2), (125, -130, 28, 105, 58, 2), (0, -170, 26, 110, 14, 2)]):
            self.ellipse(x + dx * s, y + dy * s, rx * s, ry * s, GREENS[g], rot)
        self.box(x - 85 * s, y - 20 * s, 170 * s, 190 * s, pot, r=int(26 * s), extra="border-top-left-radius:6px;border-top-right-radius:6px;")
        self.box(x - 96 * s, y - 34 * s, 192 * s, 36 * s, mix(pot, "#000000", .12), r=8)

    def lamp(self, x, y):
        self.box(x - 7, y + 150, 14, 560, "#2b2622")
        self.box(x - 70, y + 700, 140, 22, "#2b2622", r=10)
        self.box(x - 120, y, 240, 190, self.pal.paper, r=30, extra="border:6px solid rgba(0,0,0,.08);")

    def books(self, x, y, colours, w=44):
        for i, c in enumerate(colours):
            h = 190 + (i * 37) % 70
            self.box(x + i * (w + 4), y - h, w, h, c, r=4)

    def vase(self, x, y):
        for dx, h, rot in ((-30, 190, -8), (0, 270, 0), (34, 220, 9)):
            self.box(x + dx - 4, y - h, 8, h, "#6f5b3e", rot=rot)
            self.ellipse(x + dx * 1.9, y - h - 10, 22, 42, self.pal.accent2, rot)
        self.box(x - 64, y - 20, 128, 190, mix(self.pal.paper, "#000000", .06), r=60)

    def sofa(self, x, y, w):
        c = self.pal.accent
        self.box(x + 30, y + 330, 38, 70, "#2b2622", r=6)
        self.box(x + w - 68, y + 330, 38, 70, "#2b2622", r=6)
        self.box(x + 60, y - 60, w - 120, 330, mix(c, "#000000", .1), r=70)
        self.box(x, y + 120, w, 230, c, r=50)
        self.box(x - 20, y + 20, 180, 340, mix(c, "#000000", .06), r=70)
        self.box(x + w - 160, y + 20, 180, 340, mix(c, "#000000", .06), r=70)
        for dx in (210, w - 540):
            self.box(x + dx, y + 30, 330, 200, self.pal.accent2, r=44, rot=-2 if dx < w / 2 else 2)

    def render(self) -> Image.Image:
        html = (f"<style>@page{{size:{W}px {H}px;margin:0}}html,body{{margin:0;padding:0}}.s{{position:relative;width:{W}px;height:{H}px;overflow:hidden}}</style>"
                f"<div class='s'>{''.join(self.parts)}</div>")
        with tempfile.TemporaryDirectory() as t:
            pdf = Path(t) / "scene.pdf"
            render_pdf(html, pdf, page_css_size=f"{W}px {H}px")
            doc = pdfium.PdfDocument(str(pdf))
            try:
                im = doc[0].render(scale=1 / 0.75).to_pil().convert("RGB")
            finally:
                doc.close()
        return im.resize((W, H), Image.LANCZOS) if im.size != (W, H) else im


def room_scene(name: str, arts: list[Image.Image], pal: Palette) -> Image.Image:
    """One framed-art room photo (2700 x 2025). `arts` are portrait 4:5 artwork previews; scenes reuse them if there are fewer than needed."""
    uris = [_uri(a) for a in arts] or [_uri(Image.new("RGB", (800, 1000), pal.soft))]
    pick = lambda i: uris[i % len(uris)]   # noqa: E731
    s = _Scene(pal)
    if name == "sofa":
        s.room()
        iw = 500
        fw = iw + 144
        s.frame(W / 2 - fw / 2, 250, iw, pick(0))
        s.ellipse(W / 2, 1830, 800, 95, mix(pal.accent2, s.floor, .55))
        s.sofa(W / 2 - 590, 1140, 1180)
        s.lamp(430, 780)
        s.plant(2240, 1560, 1.15)
        s.box(2030, 1500, 150, 20, WOOD, r=4)
    elif name == "gallery":
        s.room(1620)
        s.frame(520, 440, 330, pick(1))
        s.frame(1040, 250, 480, pick(0))
        s.frame(1840, 440, 330, pick(2))
        s.box(520, 1250, 1660, 44, WOOD, r=6)
        for x in (600, 2040):
            s.box(x, 1294, 26, 326, "#2b2622")
        s.vase(760, 1250)
        s.books(1420, 1250, [pal.accent, pal.accent2, mix(pal.ink, "#ffffff", .3)])
        s.ellipse(1900, 1226, 90, 30, pal.paper)
    elif name == "shelf":
        s.room(1640)
        s.frame(900, 260, 400, pick(0))
        s.frame(1560, 470, 300, pick(1))
        s.box(520, 1280, 1700, 40, WOOD, r=6)
        s.box(520, 1320, 1700, 12, "rgba(0,0,0,.10)")
        s.books(560, 1280, [pal.accent, pal.accent2, mix(pal.accent, "#ffffff", .5), pal.ink])
        s.plant(2000, 1280, .75)
        s.ellipse(1480, 1240, 36, 46, pal.paper)
        s.ellipse(1480, 1194, 8, 16, "#e8a33d")
        s.lamp(2470, 640)
    else:   # bedroom
        s.room(1500)
        s.frame(W / 2 - 332, 130, 520, pick(0), fcol="#f4efe6", mat="#ffffff")
        s.box(W / 2 - 900, 960, 1800, 500, mix(pal.accent, "#000000", .08), r=90)   # headboard
        s.box(W / 2 - 960, 1230, 1920, 420, mix(pal.paper, "#000000", .03), r=50)   # bed
        s.box(W / 2 - 960, 1450, 1920, 200, mix(pal.accent, "#ffffff", .25), r=30)
        for dx, rot in ((-560, -3), (80, 2)):
            s.box(W / 2 + dx, 1080, 520, 260, pal.paper, r=70, rot=rot)
        s.box(W / 2 - 200, 1260, 400, 240, pal.accent2, r=50)
        for x in (210, 2250):
            s.box(x, 1250, 240, 40, WOOD, r=6)
            s.box(x + 100, 1290, 40, 330, "#2b2622")
        s.plant(2380, 1250, .7)
        s.lamp(330, 880)
    return s.render()
