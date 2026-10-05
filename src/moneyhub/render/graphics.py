"""Pillow graphics: listing mockups, marketplace covers and Pinterest pins built from rendered product pages."""
from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..design import Style, font_file
from ..paths import FONT_DIR


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


class Brush:
    """Fonts + colours for one style."""

    def __init__(self, style: Style):
        p = style.palette
        self.style = style
        self.bg, self.ink, self.muted = _hex(p.paper), _hex(p.ink), _hex(p.muted)
        self.accent, self.accent_ink, self.soft, self.accent2, self.line = (
            _hex(p.accent), _hex(p.accent_ink), _hex(p.soft), _hex(p.accent2), _hex(p.line))
        f = style.fonts
        self._h = FONT_DIR / font_file(f.heading, max(f.heading_weights))
        self._b = FONT_DIR / font_file(f.body, 700 if 700 in f.body_weights else max(f.body_weights))
        self._bm = FONT_DIR / font_file(f.body, 500 if 500 in f.body_weights else min(f.body_weights))
        self._s = FONT_DIR / font_file(f.script, 700)

    def heading(self, size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(self._h), size)

    def body(self, size: int, medium: bool = False) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(self._bm if medium else self._b), size)

    def script(self, size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(self._s), size)


def wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if draw.textlength(t, font=font) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_text_block(draw, xy, text, font, fill, max_w, line_gap=1.15, anchor="l", max_lines=None) -> int:
    x, y = xy
    lines = wrap(draw, text, font, max_w)
    if max_lines:
        lines = lines[:max_lines]
    lh = int(font.size * line_gap)
    for ln in lines:
        w = draw.textlength(ln, font=font)
        dx = {"l": 0, "c": -w / 2, "r": -w}[anchor]
        draw.text((x + dx, y), ln, font=font, fill=fill)
        y += lh
    return y


def rounded_page(img: Image.Image, radius: int = 18, border: tuple | None = None) -> Image.Image:
    img = img.convert("RGBA")
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *img.size), radius, fill=255)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    if border:
        ImageDraw.Draw(out).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius, outline=border, width=2)
    return out


def paste_with_shadow(canvas: Image.Image, page: Image.Image, xy: tuple[int, int], angle: float = 0,
                      blur: int = 28, offset=(10, 22), opacity=70) -> None:
    page = rounded_page(page, 14, (225, 225, 225))
    if angle:
        page = page.rotate(angle, expand=True, resample=Image.BICUBIC)
    shadow = Image.new("RGBA", (page.width + blur * 4, page.height + blur * 4), (0, 0, 0, 0))
    alpha = page.split()[3].point(lambda v: opacity if v > 10 else 0)
    shadow.paste((0, 0, 0, 255), (blur * 2, blur * 2), alpha)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(shadow, (xy[0] - blur * 2 + offset[0], xy[1] - blur * 2 + offset[1]))
    canvas.alpha_composite(page, xy)


def fit_height(img: Image.Image, h: int) -> Image.Image:
    return img.resize((round(img.width * h / img.height), h), Image.LANCZOS)


def chip(draw, xy, text, font, fill, ink, pad=(28, 14)) -> tuple[int, int]:
    w = int(draw.textlength(text, font=font)) + pad[0] * 2
    h = font.size + pad[1] * 2
    draw.rounded_rectangle((xy[0], xy[1], xy[0] + w, xy[1] + h), h // 2, fill=fill)
    draw.text((xy[0] + pad[0], xy[1] + pad[1] - 2), text, font=font, fill=ink)
    return w, h


def _bg(size, brush: Brush, kind: str = "soft") -> Image.Image:
    img = Image.new("RGBA", size, brush.soft + (255,) if kind == "soft" else brush.accent + (255,))
    d = ImageDraw.Draw(img)
    w, h = size
    d.ellipse((-w * 0.2, -h * 0.25, w * 0.35, h * 0.35), fill=brush.bg + (120,))
    d.ellipse((w * 0.78, h * 0.62, w * 1.25, h * 1.3), fill=brush.accent + (38,))
    return img


# ----------------------------------------------------------------- listing images
def hero(pages: list[Image.Image], title: str, subtitle: str, badges: list[str], brush: Brush, size=(2700, 2025)) -> Image.Image:
    W, H = size
    img = _bg(size, brush)
    d = ImageDraw.Draw(img)
    # right: fanned pages
    ph = int(H * 0.7)
    shown = [fit_height(p, ph) for p in pages[:3]]
    cx, cy = int(W * 0.7), int(H * 0.15)
    offsets = [(-int(W * 0.12), int(H * 0.05), -7), (int(W * 0.0), 0, 0), (int(W * 0.12), int(H * 0.06), 7)]
    order = [0, 2, 1] if len(shown) == 3 else list(range(len(shown)))
    for idx in order:
        pg = shown[idx]
        ox, oy, ang = offsets[idx] if len(shown) == 3 else (0, 0, 0)
        paste_with_shadow(img, pg, (cx + ox - pg.width // 2, cy + oy), angle=ang)
    # left: copy
    x, maxw = int(W * 0.06), int(W * 0.36)
    d.text((x, int(H * 0.12)), subtitle.upper(), font=brush.body(44), fill=brush.accent)
    y = draw_text_block(d, (x, int(H * 0.19)), title, brush.heading(132), brush.ink, maxw, 1.08)
    by = y + 60
    for b in badges[:3]:
        w, h = chip(d, (x, by), b.upper(), brush.body(40), brush.accent, brush.accent_ink)
        by += h + 22
    return img.convert("RGB")


def included(pages: list[Image.Image], features: list[str], brush: Brush, size=(2700, 2025)) -> Image.Image:
    W, H = size
    img = Image.new("RGBA", size, brush.bg + (255,))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, int(W * 0.52), H), fill=brush.soft)
    d.text((int(W * 0.06), int(H * 0.09)), "WHAT'S INCLUDED", font=brush.body(54), fill=brush.accent)
    y = int(H * 0.2)
    f = brush.body(58, medium=True)
    for feat in features[:7]:
        d.ellipse((int(W * 0.06), y + 6, int(W * 0.06) + 56, y + 62), fill=brush.accent)
        d.line((int(W * 0.06) + 15, y + 36, int(W * 0.06) + 25, y + 46, int(W * 0.06) + 42, y + 24), fill=brush.accent_ink, width=7)
        y = draw_text_block(d, (int(W * 0.06) + 90, y), feat, f, brush.ink, int(W * 0.37), 1.2, max_lines=3) + 34
    ph = int(H * 0.66)
    for i, pg in enumerate(pages[:2]):
        p = fit_height(pg, ph)
        paste_with_shadow(img, p, (int(W * 0.53) + i * int(W * 0.06), int(H * 0.12) + i * int(H * 0.08)), angle=-3 + i * 6)
    return img.convert("RGB")


def page_grid(pages: list[Image.Image], caption: str, brush: Brush, size=(2700, 2025)) -> Image.Image:
    W, H = size
    img = _bg(size, brush)
    d = ImageDraw.Draw(img)
    d.text((W // 2, int(H * 0.07)), caption.upper(), font=brush.body(56), fill=brush.accent, anchor="mt")
    n = min(len(pages), 4)
    ph = int(H * 0.72)
    shown = [fit_height(p, ph) for p in pages[:n]]
    total = sum(p.width for p in shown) + 60 * (n - 1)
    x = (W - total) // 2
    for p in shown:
        paste_with_shadow(img, p, (x, int(H * 0.18)))
        x += p.width + 60
    return img.convert("RGB")


def sizes_image(labels: list[str], formats: str, pages: list[Image.Image], brush: Brush, size=(2700, 2025)) -> Image.Image:
    W, H = size
    img = Image.new("RGBA", size, brush.accent + (255,))
    d = ImageDraw.Draw(img)
    d.text((int(W * 0.07), int(H * 0.14)), "SIZES & FORMATS", font=brush.body(54), fill=brush.accent_ink)
    y = int(H * 0.26)
    for lab in labels[:5]:
        w, h = chip(d, (int(W * 0.07), y), lab, brush.body(56), brush.bg, brush.accent, (40, 22))
        y += h + 30
    y += 30
    draw_text_block(d, (int(W * 0.07), y), formats, brush.body(48, True), brush.accent_ink, int(W * 0.45), 1.25)
    if pages:
        p = fit_height(pages[0], int(H * 0.72))
        paste_with_shadow(img, p, (int(W * 0.6), int(H * 0.13)), angle=4)
    return img.convert("RGB")


def how_it_works(steps: list[tuple[str, str]], brush: Brush, size=(2700, 2025)) -> Image.Image:
    W, H = size
    img = _bg(size, brush)
    d = ImageDraw.Draw(img)
    d.text((W // 2, int(H * 0.1)), "HOW IT WORKS", font=brush.body(60), fill=brush.accent, anchor="mt")
    n = len(steps)
    cw = int(W * 0.26)
    gap = (W - cw * n) // (n + 1)
    for i, (head, body) in enumerate(steps):
        x = gap + i * (cw + gap)
        d.rounded_rectangle((x, int(H * 0.25), x + cw, int(H * 0.72)), 40, fill=brush.bg)
        d.ellipse((x + cw // 2 - 70, int(H * 0.25) + 50, x + cw // 2 + 70, int(H * 0.25) + 190), fill=brush.accent)
        d.text((x + cw // 2, int(H * 0.25) + 120), str(i + 1), font=brush.heading(90), fill=brush.accent_ink, anchor="mm")
        d.text((x + cw // 2, int(H * 0.25) + 260), head, font=brush.heading(70), fill=brush.ink, anchor="mt")
        draw_text_block(d, (x + cw // 2, int(H * 0.25) + 380), body, brush.body(46, True), brush.muted, cw - 100, 1.25, anchor="c")
    return img.convert("RGB")


def detail(page: Image.Image, caption: str, brush: Brush, size=(2700, 2025)) -> Image.Image:
    W, H = size
    img = _bg(size, brush)
    d = ImageDraw.Draw(img)
    zoom = page.crop((0, 0, page.width, int(page.height * 0.55)))
    zoom = zoom.resize((int(W * 0.8), int(W * 0.8 * zoom.height / zoom.width)), Image.LANCZOS)
    if zoom.height > H * 0.72:
        zoom = zoom.crop((0, 0, zoom.width, int(H * 0.72)))
    paste_with_shadow(img, zoom, ((W - zoom.width) // 2, int(H * 0.08)))
    d.text((W // 2, int(H * 0.9)), caption, font=brush.script(96), fill=brush.accent, anchor="mm")
    return img.convert("RGB")


# ----------------------------------------------------------------- marketplace covers
def cover_wide(pages, title, subtitle, brush: Brush, size=(1280, 720)) -> Image.Image:
    W, H = size
    img = _bg(size, brush)
    d = ImageDraw.Draw(img)
    p = fit_height(pages[0], int(H * 0.86))
    paste_with_shadow(img, p, (int(W * 0.68), int(H * 0.08)), angle=3, blur=16, offset=(6, 12))
    if len(pages) > 1:
        p2 = fit_height(pages[1], int(H * 0.72))
        paste_with_shadow(img, p2, (int(W * 0.5), int(H * 0.2)), angle=-5, blur=16, offset=(6, 12))
    d.text((int(W * 0.06), int(H * 0.17)), subtitle.upper(), font=brush.body(24), fill=brush.accent)
    draw_text_block(d, (int(W * 0.06), int(H * 0.25)), title, brush.heading(76), brush.ink, int(W * 0.42), 1.08)
    return img.convert("RGB")


def square(pages, title, subtitle, brush: Brush, size=(1000, 1000)) -> Image.Image:
    W, H = size
    img = _bg(size, brush)
    d = ImageDraw.Draw(img)
    p = fit_height(pages[0], int(H * 0.5))
    paste_with_shadow(img, p, ((W - p.width) // 2, int(H * 0.44)), blur=18, offset=(6, 12))
    d.text((W // 2, int(H * 0.07)), subtitle.upper(), font=brush.body(28), fill=brush.accent, anchor="mt")
    draw_text_block(d, (W // 2, int(H * 0.12)), title, brush.heading(78), brush.ink, int(W * 0.86), 1.05, anchor="c")
    return img.convert("RGB")


# ----------------------------------------------------------------- pinterest pins (1000 x 1500)
def pin(pages: list[Image.Image], headline: str, sub: str, variant: int, brush: Brush, size=(1000, 1500)) -> Image.Image:
    W, H = size
    img = Image.new("RGBA", size, brush.bg + (255,))
    d = ImageDraw.Draw(img)
    v = variant % 4
    if v == 0:  # photo-style: big mock on top, headline band below
        d.rectangle((0, 0, W, int(H * 0.62)), fill=brush.soft)
        p = fit_height(pages[0], int(H * 0.52))
        paste_with_shadow(img, p, ((W - p.width) // 2 + 70, int(H * 0.07)), angle=3, blur=22)
        if len(pages) > 1:
            p2 = fit_height(pages[1], int(H * 0.42))
            paste_with_shadow(img, p2, (int(W * 0.08), int(H * 0.17)), angle=-6, blur=22)
        d.rectangle((0, int(H * 0.62), W, H), fill=brush.accent)
        y = draw_text_block(d, (W // 2, int(H * 0.67)), headline, brush.heading(92), brush.accent_ink, int(W * 0.86), 1.08, anchor="c", max_lines=4)
        d.text((W // 2, H - 90), sub.upper(), font=brush.body(30), fill=brush.accent_ink, anchor="mm")
    elif v == 1:  # headline on top, mock below
        d.rectangle((0, 0, W, H), fill=brush.soft)
        y = draw_text_block(d, (W // 2, int(H * 0.06)), headline, brush.heading(96), brush.ink, int(W * 0.86), 1.06, anchor="c", max_lines=4)
        chip(d, (W // 2 - 190, y + 20), "INSTANT DOWNLOAD", brush.body(30), brush.accent, brush.accent_ink)
        p = fit_height(pages[0], int(H * 0.56))
        paste_with_shadow(img, p, ((W - p.width) // 2, int(H * 0.4)))
    elif v == 2:  # accent background, script headline
        d.rectangle((0, 0, W, H), fill=brush.accent)
        d.ellipse((-W * 0.3, H * 0.62, W * 0.7, H * 1.3), fill=brush.accent2 + (255,))
        draw_text_block(d, (W // 2, int(H * 0.07)), headline, brush.heading(100), brush.accent_ink, int(W * 0.84), 1.06, anchor="c", max_lines=4)
        p = fit_height(pages[min(1, len(pages) - 1)], int(H * 0.52))
        paste_with_shadow(img, p, ((W - p.width) // 2, int(H * 0.38)), angle=-4, blur=22)
        d.text((W // 2, H - 70), sub, font=brush.script(60), fill=brush.accent_ink, anchor="mm")
    else:  # three pages cascade + framed headline
        d.rectangle((0, 0, W, H), fill=brush.bg)
        d.rectangle((40, 40, W - 40, H - 40), outline=brush.accent, width=6)
        draw_text_block(d, (W // 2, int(H * 0.08)), headline, brush.heading(88), brush.ink, int(W * 0.78), 1.08, anchor="c", max_lines=4)
        shown = pages[:3]
        for i, pg in enumerate(shown):
            q = fit_height(pg, int(H * 0.38))
            paste_with_shadow(img, q, (int(W * 0.1) + i * int(W * 0.24), int(H * 0.46) + (i % 2) * 50), angle=(-5, 0, 5)[i % 3], blur=18)
        d.text((W // 2, H - 100), sub.upper(), font=brush.body(32), fill=brush.accent, anchor="mm")
    return img.convert("RGB")


def save(img: Image.Image, path: Path, quality: int = 92) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() in (".jpg", ".jpeg"):
        img.save(path, quality=quality, optimize=True)
    else:
        img.save(path, optimize=True)
    return path
