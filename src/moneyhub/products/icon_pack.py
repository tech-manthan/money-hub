"""Icon stickers: open-source line icons (Tabler MIT, Lucide ISC, or your own licence-checked set) turned into colourful die-cut stickers for planners:
transparent PNGs for GoodNotes, SVG, and printable sheets. The icon licence text is included in the download."""
from __future__ import annotations

import io
import math
import random
import zipfile

import pypdfium2 as pdfium
from PIL import Image
from pydantic import BaseModel, Field

from .. import stickers, svgassets
from ..design import contrast
from ..niches import NicheProfile
from ..render import mockups
from ..render.pdf import render_many
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register

PER_SHEET = 20


class IconContent(BaseModel):
    title: str
    subtitle: str = "Planner icon stickers: printable and digital"
    tagline: str = Field(description="One short, warm line (<= 70 chars)")
    count: int = Field(default=48, ge=12, le=120, description="Number of icons")


def _pick(icons: dict[str, str], count: int, query: str, seed: int) -> list[tuple[str, str]]:
    names = sorted(icons)
    words = [w.strip().lower() for w in query.split(",") if w.strip()]
    if words:
        hit = [n for n in names if any(w in n for w in words)]
        names = hit or names
    random.Random(seed).shuffle(names)
    names.sort(key=lambda n: (n.count('-') + (3 if n.endswith(('-off', '-filled')) or n[-1].isdigit() else 0)))   # plain base icons first, variants last (stable: the shuffle breaks ties)
    return [(n, icons[n]) for n in names[:count]]


def _icon_svg(inner: str, badge: str, ink: str, filled: bool, shape: str) -> str:
    glyph = (f"<g transform='translate(180 180) scale(26.7)' fill='{ink if filled else 'none'}' stroke='{'none' if filled else ink}' stroke-width='2' "
             f"stroke-linecap='round' stroke-linejoin='round'>{inner.replace('currentColor', ink)}</g>")
    back = {"circle": f"<circle cx='500' cy='500' r='440' fill='{badge}'/>", "rounded": f"<rect x='60' y='60' width='880' height='880' rx='190' fill='{badge}'/>", "none": ""}[shape]
    return f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 1000'>{back}{glyph}</svg>"


@register
class IconPack(ProductType[IconContent]):
    key = "icon_pack"
    label = "Planner icon stickers"
    description = "Colourful die-cut icon stickers made from open-source line icons (MIT / ISC licensed, notice included): printable sheets and transparent PNGs for digital planners."
    content_model = IconContent
    default_sizes = ["letter", "a4"]
    supported_sizes = ["letter", "a4"]
    price_range = (3.0, 8.0)
    typical_formats = "PDF sheets (Letter and A4) + transparent PNG + SVG"
    niche_in_copy = False
    copy_audience = "planner lovers and digital planners"
    title_suffix = " Icon Stickers"
    how_steps = ("Purchase and download your files instantly.", "Print the sheets on sticker paper at Actual size, or add the transparent PNGs to GoodNotes, Notability or Canva.",
                 "Plan and decorate. Personal use only; the icon licence notice is in LICENSES.txt.")

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> IconContent:
        n = max(12, min(int(options.get("count", 48)), 120))
        return IconContent(title="Planner Icon Stickers", subtitle=f"{n} printable and digital icon stickers", tagline="Tiny icons that make a planner easier to read.", count=n)

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return ("Write a short cheerful title and tagline for a pack of colourful PLANNER ICON STICKERS (printable sheets and transparent PNGs for GoodNotes). "
                "End the title with 'Icon Stickers'. Do not mention any niche or profession.")

    def build(self, ctx: BuildContext, content: IconContent) -> BuildResult:
        coll = str(ctx.options.get("collection") or "tabler")
        meta, icons = svgassets.load(coll)   # refuses an uninstalled set or a disallowed licence
        shape = str(ctx.options.get("shape") or "circle")
        if shape not in ("circle", "rounded", "none"):
            raise ValueError("shape must be circle, rounded or none")
        content = content.model_copy(update={"title": self.unique_title(ctx, content.title)})
        slug = self.slug(content.title)
        n = max(12, min(int(ctx.options.get("count", content.count)), 120))
        pick = _pick(icons, n, str(ctx.options.get("query") or ""), ctx.seed)
        pal = ctx.style.palette
        badges = [pal.accent, pal.accent2, pal.soft, stickers._mix(pal.accent, "#ffffff", .5), stickers._mix(pal.accent2, "#ffffff", .5)]
        art_dir = ctx.out_dir.parent / "art"
        art_dir.mkdir(exist_ok=True)
        filled = meta.get("style") == "filled"
        svgs = []
        for i, (name, inner) in enumerate(pick):
            badge = badges[i % len(badges)] if shape != "none" else "none"
            ink = pal.paper if shape != "none" and contrast(badge, pal.paper) > contrast(badge, pal.ink) else pal.ink
            svgs.append((name, _icon_svg(inner, badge, ink if shape != "none" else pal.accent, filled, shape)))
        html = ("<style>@page{size:3in 3in;margin:0}html,body{margin:0;background:none}.p{width:3in;height:3in;page-break-after:always}.p svg{width:3in;height:3in;display:block}</style>"
                + "".join(f"<div class='p'>{svg}</div>" for _, svg in svgs))
        pdf = art_dir / f"{slug}-art.pdf"
        renderer = render_many([(html, pdf, "3in 3in")])[0]
        cut: list[Image.Image] = []
        doc = pdfium.PdfDocument(str(pdf))
        try:
            for i in range(len(svgs)):
                im = doc[i].render(scale=600 / 216, fill_color=(255, 255, 255, 0)).to_pil().convert("RGBA")
                cut.append(stickers.die_cut(im, 200))
        finally:
            doc.close()

        sheets = math.ceil(len(cut) / PER_SHEET)
        files: list[ProductFile] = []
        for size in ctx.sizes:
            page = ctx.page(size)
            w, h = round(page.width_in * 300), round(page.height_in * 300)
            ims = [stickers.pack_sheet(cut[k * PER_SHEET:(k + 1) * PER_SHEET], w, h, 90, cols=4, rows=5) for k in range(sheets)]
            out = ctx.out_dir / f"{slug}-{size}.pdf"
            ims[0].save(out, "PDF", resolution=300, save_all=True, append_images=ims[1:])
            files.append(ProductFile(out, "pdf", f"{page.label} - printable icon sheets", True, preview_pages=list(range(min(sheets, 3)))))
        lic = svgassets.notice(meta)
        zp = ctx.out_dir / f"{slug}-PNG-and-SVG.zip"
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as zf:
            for (name, svg), im in zip(svgs, cut):
                buf = io.BytesIO()
                im.save(buf, "PNG", dpi=(300, 300), optimize=True)
                zf.writestr(f"png/{name}.png", buf.getvalue())
                zf.writestr(f"svg/{name}.svg", svg)
            zf.writestr("LICENSES.txt", lic)
        files.append(ProductFile(zp, "zip", "Transparent PNG and SVG icons (digital planners)", True))
        (ctx.out_dir / "LICENSES.txt").write_text(lic, encoding="utf-8")
        files.append(ProductFile(ctx.out_dir / "LICENSES.txt", "txt", "Icon licence notice", False))
        features = [f"{len(cut)} colourful die-cut icon stickers on {sheets} printable sheets", "US Letter and A4 PDF for sticker paper", f"{len(cut)} transparent PNG and SVG icons for GoodNotes and digital planners",
                    "Matching colours from one palette", f"Icon artwork from {meta['name']} ({meta['license']} licence, notice included); personal use", "Instant download - no physical item shipped"]
        return BuildResult(content.title, content.subtitle, files, features, sheets, renderer,
                           meta={"min_pages": 1, "min_px": 300, "icons": len(cut), "collection": coll, "icon_license": meta["license"], "mockup_tiles": mockups.save_tiles(art_dir, cut[::max(1, len(cut) // 4)], 4)})
