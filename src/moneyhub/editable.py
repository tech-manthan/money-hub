"""Visual editing step: export layered, editable SVGs (live text + separate image layers) for Penpot, Inkscape or Open Design,
then import the images you export back into the product's upload package."""
from __future__ import annotations

import base64
import io
import json
import re
import shutil
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .design import font_file, style_from_dict
from .paths import FONT_DIR
from .render import graphics as g

PIN_W, PIN_H = 1000, 1500


# ----------------------------------------------------------------------------- helpers
def _b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _layers(page: Image.Image, height: int) -> tuple[str, str, int, int, int]:
    """(page_png, shadow_png, w, h, pad): page with rounded corners, plus a separate soft shadow layer."""
    p = g.rounded_page(g.fit_height(page, height), 14, (225, 225, 225))
    pad = 60
    sh = Image.new("RGBA", (p.width + pad * 2, p.height + pad * 2), (0, 0, 0, 0))
    a = p.split()[3].point(lambda v: 80 if v > 10 else 0)
    sh.paste((0, 0, 0, 255), (pad, pad), a)
    sh = sh.filter(ImageFilter.GaussianBlur(24))
    return _b64(p), _b64(sh), p.width, p.height, pad


class _Svg:
    def __init__(self, w: int, h: int, brush: g.Brush):
        self.w, self.h, self.b = w, h, brush
        self.parts: list[str] = []
        self._probe = ImageDraw.Draw(Image.new("RGB", (4, 4)))

    @staticmethod
    def hexc(c) -> str:
        return "#%02x%02x%02x" % tuple(c)

    def rect(self, x, y, w, h, fill=None, stroke=None, sw=0, rx=0, id=None):
        a = f' id="{id}"' if id else ""
        self.parts.append(f'<rect{a} x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill or "none"}"'
                          + (f' stroke="{stroke}" stroke-width="{sw}"' if stroke else "") + "/>")

    def ellipse(self, cx, cy, rx, ry, fill, opacity=1, id=None):
        a = f' id="{id}"' if id else ""
        self.parts.append(f'<ellipse{a} cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" opacity="{opacity}"/>')

    def image(self, data, x, y, w, h, angle=0, id=None):
        a = f' id="{id}"' if id else ""
        tr = f' transform="rotate({angle} {x + w / 2:.1f} {y + h / 2:.1f})"' if angle else ""
        self.parts.append(f'<image{a} x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" href="{data}" xlink:href="{data}"{tr}/>')

    def page(self, img: Image.Image, x, y, height, angle=0, name="page"):
        pg, sh, w, h, pad = _layers(img, height)
        self.image(sh, x - pad + 10, y - pad + 18, w + pad * 2, h + pad * 2, angle, id=f"{name}-shadow")
        self.image(pg, x, y, w, h, angle, id=name)
        return w, h

    def text(self, text, x, y, size, fill, font, weight=700, anchor="middle", max_w=None, gap=1.12, max_lines=4, id=None, upper=False):
        """Live (editable) text, wrapped with real font metrics. Returns the y below the block."""
        if upper:
            text = text.upper()
        ft = ImageFont.truetype(str(font), int(size))
        lines = g.wrap(self._probe, text, ft, int(max_w)) if max_w else [text]
        lines = lines[:max_lines]
        fam = self.b._h.stem.split("-")[0] if font == self.b._h else (self.b._s.stem.split("-")[0] if font == self.b._s else self.b._b.stem.split("-")[0])
        tsp = "".join(f'<tspan x="{x}" dy="{0 if i == 0 else size * gap:.1f}">{escape(l)}</tspan>' for i, l in enumerate(lines))
        a = f' id="{id}"' if id else ""
        self.parts.append(f'<text{a} x="{x}" y="{y + size * 0.85:.1f}" font-family="{fam}" font-weight="{weight}" font-size="{size}" '
                          f'fill="{fill}" text-anchor="{anchor}">{tsp}</text>')
        return y + size * gap * len(lines)

    def raw(self, s: str):
        self.parts.append(s)

    def render(self) -> str:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}">' + "".join(self.parts) + "</svg>")


# ----------------------------------------------------------------------------- pins
def pin_svg(pages: list[Image.Image], headline: str, sub: str, variant: int, brush: g.Brush) -> str:
    """Editable pin: same layout as the PNG pin (shared plan), with live text and separate image layers."""
    plan = g.pin_plan(variant, headline, sub, brush, (PIN_W, PIN_H))
    s = _Svg(PIN_W, PIN_H, brush)
    hx = _Svg.hexc
    for rid, x, y, w, h, col in plan["rects"]:
        s.rect(x, y, w, h, hx(col), id=rid)
    for rid, cx, cy, rx, ry, col in plan["ellipses"]:
        s.ellipse(cx, cy, rx, ry, hx(col), id=rid)
    for rid, x, y, w, h, col, sw in plan.get("frames", []):
        s.rect(x, y, w, h, stroke=hx(col), sw=sw, id=rid)
    for pi, x, y, ph, ang, pid, _ in plan["pages"]:
        pg = pages[min(pi, len(pages) - 1)]
        pw = round(pg.width * ph / pg.height)
        if x == "center":
            x = (PIN_W - pw) // 2
        elif x is None:
            x = (PIN_W - pw) // 2 + 60
        s.page(pg, int(x), int(y), ph, ang, pid)
    for cid, x, y, w, h, col, text, tcol in plan["chips"]:
        s.rect(x, y, w, h, hx(col), rx=h // 2, id=cid)
        s.text(text, x + w // 2, y + 20, 30, hx(tcol), brush._b, id=cid + "-text")
    for t in plan["texts"]:
        fam = t["font"].stem.split("-")[0]
        yy = t["y"]
        tsp = "".join(f'<tspan x="{t["x"]}" dy="{0 if i == 0 else t["size"] * t["gap"]:.1f}">{escape(l.upper() if t["upper"] else l)}</tspan>' for i, l in enumerate(t["lines"]))
        s.raw(f'<text id="{t["id"]}" x="{t["x"]}" y="{yy + t["size"] * .85:.1f}" font-family="{fam}" font-weight="700" font-size="{t["size"]}" '
              f'fill="{hx(t["fill"])}" text-anchor="{t["anchor"]}">{tsp}</text>')
    return s.render()


def hero_svg(pages: list[Image.Image], title: str, subtitle: str, badges: list[str], brush: g.Brush, size=(2700, 2025)) -> str:
    W, H = size
    hx = _Svg.hexc
    s = _Svg(W, H, brush)
    s.rect(0, 0, W, H, hx(brush.soft), id="background")
    s.ellipse(W * .08, H * .05, W * .27, H * .3, hx(brush.bg), 0.5, id="light")
    s.ellipse(W * 1.0, H * .96, W * .24, H * .34, hx(brush.accent), 0.15, id="accent-shape")
    ph = int(H * .7)
    cx, cy = int(W * .7), int(H * .15)
    spec = [(-int(W * .12), int(H * .05), -7), (0, 0, 0), (int(W * .12), int(H * .06), 7)]
    shown = pages[:3]
    for idx in ([0, 2, 1] if len(shown) == 3 else range(len(shown))):
        pw = round(shown[idx].width * ph / shown[idx].height)
        ox, oy, ang = spec[idx] if len(shown) == 3 else (0, 0, 0)
        s.page(shown[idx], cx + ox - pw // 2, cy + oy, ph, ang, f"page-{idx + 1}")
    x = int(W * .06)
    s.text(subtitle, x, int(H * .12), 44, hx(brush.accent), brush._b, anchor="start", upper=True, id="kicker")
    y = s.text(title, x, int(H * .19), 132, hx(brush.ink), brush._h, anchor="start", max_w=W * .36, gap=1.08, id="title")
    by = int(y + 60)
    for i, b in enumerate(badges[:3]):
        bw = int(len(b) * 26 + 60)
        s.rect(x, by, bw, 84, hx(brush.accent), rx=42, id=f"badge-{i + 1}")
        s.text(b, x + bw // 2, by + 22, 40, hx(brush.accent_ink), brush._b, id=f"badge-text-{i + 1}", upper=True)
        by += 106
    return s.render()


# ----------------------------------------------------------------------------- wall art posters
def poster_svg(d: dict, palette_ink: str, w: int = 1000, h: int = 1250) -> str:
    """One poster design as editable SVG. `d` is the design dict used by the wall-art product."""
    def box(l, t, bw, bh):
        return l * w, t * h, bw * w, bh * h

    def motif(x, y, bw, bh):
        inner = re.sub(r"^<svg[^>]*>|</svg>$", "", d["svg"].strip())
        sc = min(bw, bh) / 1000
        return f'<g id="motif" transform="translate({x + (bw - 1000 * sc) / 2:.1f} {y + (bh - 1000 * sc) / 2:.1f}) scale({sc:.4f})">{inner}</g>'

    fg, bg = d["fg"], d["bg"]
    fam = "sans-serif"
    size = round(d["fs"] * 0.01634 * w)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
           f'<rect id="background" width="{w}" height="{h}" fill="{bg}"/>']
    probe = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    ft = ImageFont.truetype(str(FONT_DIR / "Nunito-700.ttf"), size)

    def text(x, top, width, anchor="middle", fsz=size, fill=fg, content=None, ident="quote", family=None):
        lines = g.wrap(probe, content or d["text"], ft if fsz == size else ImageFont.truetype(str(FONT_DIR / "Nunito-700.ttf"), fsz), int(width))
        tsp = "".join(f'<tspan x="{x}" dy="{0 if i == 0 else fsz * 1.14:.1f}">{escape(l)}</tspan>' for i, l in enumerate(lines))
        return (f'<text id="{ident}" x="{x}" y="{top + fsz * .85:.1f}" font-family="{family or fam}" font-weight="700" font-size="{fsz}" '
                f'fill="{fill}" text-anchor="{anchor}">{tsp}</text>')

    lay = d["layout"]
    small = d.get("small") or ""
    ssz = round(3 * 0.01634 * w)

    def small_t(top):
        return text(w / 2, top, w * .7, fsz=ssz, content=small, ident="small-text", family="Caveat") if small else ""

    if lay == 0:
        out += [motif(*box(.12, .08, .76, .46)), text(w / 2, h * .60, w * .76), small_t(h * .91 - ssz)]
    elif lay == 1:
        out += [text(w / 2, h * .12, w * .76), motif(*box(.05, .41, .90, .56))]
    elif lay == 2:
        out += [f'<rect id="frame" x="{w * .06}" y="{h * .045}" width="{w * .88}" height="{h * .91}" rx="12" fill="none" stroke="{fg}" stroke-width="3" opacity=".7"/>',
                motif(*box(.30, .12, .40, .26)), text(w / 2, h * .44, w * .68), small_t(h * .89 - ssz)]
    elif lay == 3:
        out += [motif(*box(-.15, -.06, 1.3, .62)), text(w * .11, h * .70, w * .78, anchor="start", fsz=round(5.6 * 0.01634 * w))]
    else:
        out += [motif(*box(.20, .14, .60, .30)), f'<rect id="rule" x="{w * .44}" y="{h * .50}" width="{w * .12}" height="4" fill="{fg}"/>',
                text(w / 2, h * .54, w * .72), small_t(h * .91 - ssz)]
    out.append("</svg>")
    return "".join(out)


# ----------------------------------------------------------------------------- export / import
BRIEF = """# Editing brief - {title}

Everything here is layered and editable. Text is live text, images are separate layers, and each shape has an id.

## Design tokens
- Palette `{palette}`: paper `{paper}`, ink `{ink}`, muted `{muted}`, line `{line}`, accent `{accent}`, accent text `{accent_ink}`, soft `{soft}`, accent 2 `{accent2}`
- Fonts: heading **{heading}**, body **{body}**, script **{script}** (files in `fonts/`, SIL Open Font License: install or upload them, but do not resell the font files)
- Header style `{header}`, corner radius {radius}px

## Copy
- Product: {title} - {subtitle}
- Pin headlines: {headlines}
- Pin title ideas: {pin_titles}

## Files
{files}

## Workflow
1. Open Penpot (see `docs/editing.md`), drag the SVGs in, edit, and export each frame as PNG/JPG **with the same file name** (e.g. `pin-01.png`) into the `edited/` folder.
2. Run `moneyhub edit import {pid} {edited}` (or upload them on the product page) - originals are backed up in `images/_original/`.
3. Re-check the sizes in the marketplace guides: Etsy 2700x2025, Gumroad cover 1280x720, Pinterest 1000x1500.

## For an AI design agent (Open Design, Claude Code with the Penpot MCP, etc.)
Use the tokens and copy above. Keep text inside the safe area (Pinterest crops the bottom third). Keep contrast at least 4.5:1. Output PNG files named as the SVGs.
"""


def export_editable(folder: Path, pid: int | None = None) -> Path:
    """Write <folder>/editable/ with layered SVGs, fonts and a design brief. Returns that directory."""
    spec = json.loads((folder / "spec.json").read_text())
    style = style_from_dict(spec["style"])
    brush = g.Brush(style)
    listing = json.loads((folder / "listing" / "listing.json").read_text())["copy_"]
    out = folder / "editable"
    for sub in ("pins", "listing", "posters", "fonts", "edited"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    pages = _page_images(folder)
    written: list[str] = []
    if pages:
        headlines = listing["pin_headlines"]
        title = spec["content"].get("title", "")
        for i, h in enumerate(headlines[:6]):
            p = out / "pins" / f"pin-{i + 1:02d}.svg"
            p.write_text(pin_svg(pages, h, title, i, brush), encoding="utf-8")
            written.append(f"pins/{p.name}  (1000x1500, export as pin-{i + 1:02d}.png)")
        sub = spec["content"].get("subtitle", "")
        badges = ["Instant download", "Printable", "Digital"]
        p = out / "listing" / "01-hero.svg"
        p.write_text(hero_svg(pages, title, sub, badges, brush), encoding="utf-8")
        written.append("listing/01-hero.svg  (2700x2025, export as 01-hero.jpg)")

    if spec["request"]["product_type"] == "wall_art":
        from .products.wall_art import make_designs
        from .products.wall_art import WallArtContent
        designs = make_designs(WallArtContent.model_validate(spec["content"]), style, spec["request"]["seed"], use_ai=False)[0]
        for i, d in enumerate(designs):
            p = out / "posters" / f"design-{i + 1:02d}.svg"
            p.write_text(poster_svg(d, spec["style"]["palette"]), encoding="utf-8")
            written.append(f"posters/{p.name}  (4:5 poster; re-export for other ratios)")

    f = style.fonts
    for family, weights in ((f.heading, f.heading_weights), (f.body, f.body_weights), (f.script, (400, 700))):
        for w in weights:
            src = FONT_DIR / font_file(family, w)
            if src.exists():
                shutil.copy(src, out / "fonts" / src.name)
    pal = style.palette
    (out / "BRIEF.md").write_text(BRIEF.format(
        title=spec["content"].get("title", ""), subtitle=spec["content"].get("subtitle", ""), palette=pal.key, paper=pal.paper, ink=pal.ink,
        muted=pal.muted, line=pal.line, accent=pal.accent, accent_ink=pal.accent_ink, soft=pal.soft, accent2=pal.accent2,
        heading=f.heading, body=f.body, script=f.script, header=style.header, radius=style.radius,
        headlines="; ".join(listing["pin_headlines"]), pin_titles="; ".join(listing["pin_titles"][:4]),
        files="\n".join(f"- `{w}`" for w in written), pid=pid if pid is not None else "<id>", edited=out / "edited"), encoding="utf-8")
    return out


def _page_images(folder: Path, n: int = 3) -> list[Image.Image]:
    art = sorted((folder / "art").glob("preview-*.png"))
    if art:
        return [Image.open(p).convert("RGB") for p in art[:n]]
    pdfs = sorted((folder / "product").glob("*.pdf"))
    if not pdfs:
        return []
    from .render.raster import pdf_page_count, render_pages
    total = pdf_page_count(pdfs[0])
    idx = [i for i in (0, 1, 2, 4) if i < total][:n]
    return render_pages(pdfs[0], idx, scale=1.4)


_ALIASES = {"gumroad-cover": ("gumroad", "cover-"), "gumroad-thumbnail": ("gumroad", "thumbnail-"),
            "payhip-cover": ("payhip", "cover-"), "kofi-square": ("kofi", "square-")}


def _target_for(stem: str, folder: Path) -> Path | None:
    stem = stem.lower()
    if stem in _ALIASES:
        sub, prefix = _ALIASES[stem]
        hits = sorted((folder / "images" / sub).glob(f"{prefix}*"))
        return hits[0] if hits else None
    for sub in ("etsy", "pinterest", "gumroad", "payhip", "kofi"):
        for f in sorted((folder / "images" / sub).glob("*")):
            fs = f.stem.lower()
            if fs == stem or fs.startswith(stem + "-") or fs.startswith(stem):
                return f
    return None


def import_edits(folder: Path, source: Path) -> list[tuple[str, str]]:
    """Replace listing images with your edited exports (matched by file name). Returns [(edited, replaced)]."""
    done = []
    backup = folder / "images" / "_original"
    for f in sorted(source.glob("*")):
        if f.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        target = _target_for(f.stem, folder)
        if not target:
            continue
        backup.mkdir(exist_ok=True)
        bk = backup / target.relative_to(folder / "images").as_posix().replace("/", "__")
        if not bk.exists():
            shutil.copy(target, bk)
        with Image.open(target) as old:
            size = old.size
        im = Image.open(f).convert("RGB")
        if im.size != size:
            im = im.resize(size, Image.LANCZOS)
        im.save(target, quality=93) if target.suffix.lower() in (".jpg", ".jpeg") else im.save(target)
        done.append((f.name, str(target.relative_to(folder))))
    if done:
        from .pipeline import make_package
        make_package(folder)
    return done
