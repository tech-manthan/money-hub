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



# --------------------------------------------------------------------------- scenes for the other product families
DOC_SCENES = ["desk", "fan", "tablet"]          # printed pages: planners, journals, trackers, worksheets, coloring pages...
STATIONERY_SCENES = ["cards", "gift", "notebooks"]   # clipart and digital paper, shown on things people make with them
CUT_SCENES = ["mugs", "apparel"]                # cut files, shown as vinyl decals
FAMILIES = {"clipart_pack": STATIONERY_SCENES, "character_clipart": STATIONERY_SCENES, "icon_pack": STATIONERY_SCENES, "digital_paper": STATIONERY_SCENES, "cut_files": CUT_SCENES}


def scenes_for(ptype_key: str) -> list[str]:
    """Mockup scene names for a product type (wall art uses SCENES instead)."""
    return FAMILIES.get(ptype_key, DOC_SCENES)


def save_tiles(art_dir: Path, ims: list[Image.Image], count: int = 4) -> list[Path]:
    """Single designs saved for the mockup scenes (transparent PNG when the design has transparency)."""
    out = []
    for i, im in enumerate(ims[:count], 1):
        p = art_dir / f"tile-{i:02d}.png"
        im.copy().resize((600, 600), Image.LANCZOS).save(p)
        out.append(p)
    return out


def _png_uri(im: Image.Image, size: int = 700) -> str:
    im = im.convert("RGBA")
    im.thumbnail((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def tint(im: Image.Image, colour: str) -> Image.Image:
    """A transparent design filled with one flat colour (a vinyl decal)."""
    im = im.convert("RGBA")
    solid = Image.new("RGBA", im.size, colour)
    solid.putalpha(im.getchannel("A"))
    return solid


def _fit_h(w: float, im_ratio: float, max_h: float) -> tuple[float, float]:
    h = w / im_ratio
    return (w * max_h / h, max_h) if h > max_h else (w, h)


class _Flat(_Scene):
    """Top-down flat-lay and front-view props."""

    def desk_bg(self):
        base = mix(WOOD, self.pal.soft, .55)
        self.box(0, 0, W, H, base)
        for i in range(1, 8):
            self.box(0, i * H / 8, W, 5, "rgba(0,0,0,.07)")

    def sheet(self, x, y, w, h, uri, rot=0, origin="50% 50%", border="#ffffff", fit="cover"):
        t = f"transform:rotate({rot}deg);transform-origin:{origin};" if rot else ""
        self.parts.append(
            f"<div style='position:absolute;left:{x:.0f}px;top:{y:.0f}px;width:{w:.0f}px;height:{h:.0f}px;{t}background:{border};box-shadow:14px 22px 40px rgba(0,0,0,.28)'>"
            f"<img src='{uri}' style='position:absolute;left:0;top:0;width:{w:.0f}px;height:{h:.0f}px;object-fit:{fit}'></div>")

    def mug_top(self, cx, cy, r, col=None):
        col = col or self.pal.accent
        self.box(cx + r * .9, cy - r * .32, r * .75, r * .64, col, r=int(r * .3), extra=f"border:{r * .13:.0f}px solid {mix(col, '#000000', .12)};background:none;")
        self.ellipse(cx + 14, cy + 22, r, r, "rgba(0,0,0,.2)")
        self.ellipse(cx, cy, r, r, col)
        self.ellipse(cx, cy, r * .82, r * .82, mix(col, "#ffffff", .3))
        self.ellipse(cx, cy, r * .72, r * .72, "#5a3a26")
        self.ellipse(cx - r * .18, cy - r * .2, r * .22, r * .12, "rgba(255,255,255,.25)", -30)

    def pencil(self, x, y, length, rot, col=None):
        col = col or self.pal.accent2
        self.parts.append(
            f"<div style='position:absolute;left:{x:.0f}px;top:{y:.0f}px;width:{length:.0f}px;height:34px;transform:rotate({rot}deg);transform-origin:0 50%;'>"
            f"<div style='position:absolute;left:0;top:0;width:{length - 70:.0f}px;height:34px;background:{col};border-radius:4px'></div>"
            f"<div style='position:absolute;left:{length - 70:.0f}px;top:0;width:0;height:0;border-top:17px solid transparent;border-bottom:17px solid transparent;border-left:70px solid #e9c9a0'></div>"
            f"<div style='position:absolute;left:{length - 18:.0f}px;top:12px;width:0;height:0;border-top:5px solid transparent;border-bottom:5px solid transparent;border-left:18px solid #333'></div></div>")

    def leaves(self, x, y, s=1.0, rot=0):
        for k, (dx, dy, a) in enumerate([(0, 0, 0), (60, -30, 35), (-60, -30, -35), (30, -110, 18), (-30, -110, -18), (0, -150, 0)]):
            self.ellipse(x + dx * s, y + dy * s, 38 * s, 105 * s, GREENS[k % 3], rot + a)

    def clip(self, x, y, rot=0):
        self.box(x, y, 26, 86, "none", r=13, rot=rot, extra="border:6px solid #9aa0a6;background:none;")


def _tee(col: str, shadow: str, w: float, h: float) -> str:
    return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 850' width='{w:.0f}' height='{h:.0f}'><path d='M250 60 L100 130 L20 300 L140 345 L175 265 L175 790 L825 790 L825 265 L860 345 L980 300 L900 130 L750 60 Q650 150 500 150 Q350 150 250 60 Z' "
            f"fill='{col}' stroke='{shadow}' stroke-width='6' stroke-linejoin='round'/><path d='M350 62 Q500 190 650 62' fill='none' stroke='{shadow}' stroke-width='6'/></svg>")


def _tote(col: str, shadow: str, w: float, h: float) -> str:
    return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 1000' width='{w:.0f}' height='{h:.0f}'><path d='M230 330 C230 40 570 40 570 330' fill='none' stroke='{shadow}' stroke-width='34' stroke-linecap='round'/>"
            f"<rect x='60' y='300' width='680' height='680' rx='14' fill='{col}' stroke='{shadow}' stroke-width='6'/></svg>")


def product_scene(name: str, imgs: list[Image.Image], pal: Palette, tiles: list[Image.Image] | None = None) -> Image.Image:
    """One flat-illustration listing photo (2700 x 2025). `imgs` are page images (documents) or art tiles; `tiles` are single designs (RGBA for cut files and clipart)."""
    s = _Flat(pal)
    page = [_uri(i, 1500) for i in imgs] or [_uri(Image.new("RGB", (800, 1000), pal.paper), 1000)]
    pg = lambda k: page[k % len(page)]   # noqa: E731
    ratio = lambda k: (imgs[k % len(imgs)].width / imgs[k % len(imgs)].height) if imgs else .77   # noqa: E731
    designs = tiles or imgs
    if name in DOC_SCENES:
        s.desk_bg()
        if name == "desk":
            for k, (x, y, rot) in enumerate([(300, 240, -5), (1020, 170, 3), (1740, 260, 7)]):
                w, h = _fit_h(660, ratio(k), 880)
                s.sheet(x, y + (880 - h) / 2, w, h, pg(k), rot)
            s.mug_top(560, 1620, 200)
            s.pencil(1000, 1600, 560, -8)
            s.pencil(1010, 1690, 520, -3, pal.accent)
            s.leaves(2420, 1760, 1.5, 20)
            s.clip(1790, 1180, 12)
        elif name == "fan":
            for rot, k in zip((-26, -13, 0, 13, 26), (3, 2, 1, 4, 0)):
                w, h = _fit_h(700, ratio(k), 1000)
                s.sheet(W / 2 - w / 2, 1850 - h, w, h, pg(k), rot, origin="50% 100%")
            s.mug_top(470, 520, 190, pal.accent2)
            s.pencil(1950, 330, 540, 22)
            s.leaves(2380, 1000, 1.3, 25)
        else:   # tablet: a digital planner on a tablet
            s.box(420, 260, 1360, 1030, "rgba(0,0,0,.28)", r=70, extra="filter:blur(0px);transform:translate(24px,30px);")
            s.box(400, 230, 1360, 1030, "#1f1f23", r=70)
            w, h = _fit_h(1220, ratio(0), 930)
            s.box(470, 280, 1220, 930, "#ffffff", r=34)
            s.parts.append(f"<img src='{pg(0)}' style='position:absolute;left:{470 + (1220 - w) / 2:.0f}px;top:{280 + (930 - h) / 2:.0f}px;width:{w:.0f}px;height:{h:.0f}px;object-fit:contain'>")
            s.pencil(1900, 440, 700, 78, "#2b2b30")
            w2, h2 = _fit_h(540, ratio(1), 700)
            s.sheet(1960, 880, w2, h2, pg(1), 8)
            s.mug_top(2260, 400, 170, pal.accent)
            s.leaves(520, 1760, 1.5, -15)
            s.box(1100, 1520, 360, 300, "#f2e57b", r=6, rot=-4)
            s.box(1160, 1580, 240, 14, "rgba(0,0,0,.2)", rot=-4)
            s.box(1160, 1630, 200, 14, "rgba(0,0,0,.2)", rot=-4)
    elif name in STATIONERY_SCENES:
        s.box(0, 0, W, H, mix(pal.soft, "#ffffff", .35))
        tile = lambda k: _png_uri(designs[k % len(designs)], 900)   # noqa: E731
        if name == "cards":
            s.box(0, 1500, W, 525, mix(pal.soft, WOOD, .35))
            for k, (x, y, rot) in enumerate([(280, 220, -7), (950, 150, 3), (1620, 240, 8)]):
                s.box(x + 14, y + 22, 660, 900, "rgba(0,0,0,.2)", 6, rot)
                s.box(x, y, 660, 900, "#fffdf8", 6, rot)
                s.parts.append(f"<div style='position:absolute;left:{x + 60:.0f}px;top:{y + 70:.0f}px;width:540px;height:620px;transform:rotate({rot}deg);transform-origin:{270 - 60 + 60}px {310 + 0}px;background:{mix(pal.soft, pal.accent, .15 * k)} url({tile(k)}) center/contain no-repeat'></div>")
            for k, (x, y) in enumerate([(2330, 1230), (2330, 1640)]):
                s.box(x, y, 250, 330, "#fffdf8", 6, -10 if k == 0 else 8, extra="box-shadow:10px 14px 24px rgba(0,0,0,.25);")
                s.parts.append(f"<div style='position:absolute;left:{x + 25:.0f}px;top:{y + 70:.0f}px;width:200px;height:230px;background:url({tile(k + 3)}) center/contain no-repeat;transform:rotate({-10 if k == 0 else 8}deg)'></div>")
            s.pencil(160, 1300, 640, -4)
            s.leaves(2330, 1380, 1.1, -20)
        elif name == "gift":
            s.box(0, 0, W, H, mix(pal.soft, WOOD, .3))
            for k, (cx, cy, size, rot) in enumerate([(820, 1000, 980, -6), (1860, 760, 700, 8)]):
                s.box(cx - size / 2 + 16, cy - size / 2 + 24, size, size, "rgba(0,0,0,.25)", 8, rot)
                s.box(cx - size / 2, cy - size / 2, size, size, mix(pal.paper, pal.soft, .4), 8, rot)
                s.parts.append(f"<div style='position:absolute;left:{cx - size / 2:.0f}px;top:{cy - size / 2:.0f}px;width:{size:.0f}px;height:{size:.0f}px;transform:rotate({rot}deg);border-radius:8px;background:url({tile(k * 2)}) center/cover'></div>")
                s.box(cx - 36, cy - size / 2, 72, size, pal.accent, 0, rot, "opacity:.92;")
                s.box(cx - size / 2, cy - 36, size, 72, pal.accent, 0, rot, "opacity:.92;")
                s.ellipse(cx - 70, cy - 10, 90, 55, mix(pal.accent, "#000000", .08), -25)
                s.ellipse(cx + 70, cy - 10, 90, 55, mix(pal.accent, "#000000", .08), 25)
                s.ellipse(cx, cy, 44, 44, mix(pal.accent, "#ffffff", .15))
            s.box(2200, 1450, 330, 460, "#fffdf8", 6, 9, "box-shadow:10px 14px 24px rgba(0,0,0,.25);")
            s.parts.append(f"<div style='position:absolute;left:2235px;top:1520px;width:260px;height:330px;transform:rotate(9deg);background:url({tile(3)}) center/contain no-repeat'></div>")
            s.leaves(2380, 400, 1.3, 15)
            s.pencil(250, 1800, 700, -3, pal.accent2)
        else:   # notebooks
            for k, (x, y, rot, col) in enumerate([(360, 200, -5, pal.accent), (1180, 130, 4, pal.accent2), (1880, 260, 9, mix(pal.ink, pal.soft, .2))]):
                s.box(x + 16, y + 26, 640, 880, "rgba(0,0,0,.25)", 14, rot)
                s.box(x, y, 640, 880, col, 14, rot)
                s.parts.append(f"<div style='position:absolute;left:{x + 90:.0f}px;top:{y + 140:.0f}px;width:460px;height:560px;transform:rotate({rot}deg);transform-origin:{230 - 90 + 90}px {280 - 140 + 140}px;background:#fffdf8 url({tile(k)}) center/contain no-repeat;border-radius:10px'></div>")
                s.box(x, y, 60, 880, "rgba(0,0,0,.18)", 14, rot)
                s.box(x + 580, y, 18, 880, mix(col, "#000000", .25), 0, rot)
            s.mug_top(560, 1590, 200, pal.accent2)
            s.pencil(1000, 1540, 620, -6)
            s.leaves(2380, 1760, 1.5, 15)
    else:   # cut files as vinyl decals
        decal = lambda k, col: _png_uri(tint(designs[k % len(designs)], col), 700)   # noqa: E731
        cols = ["#ffffff", pal.ink, pal.accent]
        if name == "mugs":
            s.room(1620)
            s.box(260, 1330, 2180, 46, WOOD, r=6)
            for x in (480, 1960):
                s.box(x, 1376, 28, 244, "#2b2622")
            for k, (cx, col) in enumerate([(700, pal.accent), (1350, pal.paper), (2000, pal.accent2)]):
                dark = col == pal.paper
                s.box(cx - 150 + 14, 1330 - 480 + 14, 300, 480, "rgba(0,0,0,.12)", 22)
                s.box(cx + 140, 1330 - 400, 130, 270, "none", r=70, extra=f"border:40px solid {mix(col, '#000000', .1)};border-left:none;background:none;")
                s.box(cx - 150, 1330 - 480, 300, 480, col, r=22, extra="border-top-left-radius:6px;border-top-right-radius:6px;")
                s.box(cx - 150, 1330 - 480, 300, 40, mix(col, "#ffffff", .25), r=6)
                s.parts.append(f"<img src='{decal(k, pal.ink if dark else cols[0])}' style='position:absolute;left:{cx - 105}px;top:{1330 - 420}px;width:210px;height:210px'>")
            s.plant(2380, 1330, .9)
            s.books(300, 1330, [pal.accent, pal.accent2, mix(pal.ink, "#ffffff", .3)])
        else:   # apparel
            s.box(0, 0, W, H, mix(pal.soft, "#ffffff", .3))
            s.box(0, 1650, W, 375, mix(pal.soft, WOOD, .3))
            for k, (cx, cy, w, col, dcol) in enumerate([(780, 880, 1250, pal.paper, pal.ink), (2000, 930, 760, pal.soft, pal.accent)]):
                dark = mix(col, "#000000", .18)
                h = w * (850 / 1000 if k == 0 else 1000 / 800)
                svg = _tee(col, dark, w, h) if k == 0 else _tote(mix(col, "#ffffff", .2), dark, w, h)
                s.parts.append(f"<div style='position:absolute;left:{cx - w / 2:.0f}px;top:{cy - h / 2:.0f}px;width:{w}px;height:{h:.0f}px'>{svg}</div>")
                dw = 420 if k == 0 else 300
                dy = cy - 40 if k == 0 else cy + 90
                s.parts.append(f"<img src='{decal(k, dcol)}' style='position:absolute;left:{cx - dw / 2:.0f}px;top:{dy - dw / 2 + 20:.0f}px;width:{dw}px;height:{dw}px'>")
            s.leaves(250, 1830, 1.3, -10)
            s.pencil(1380, 1760, 560, -4)
    return s.render()
