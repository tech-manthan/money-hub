"""Sticker sheets: friendly colourful stickers (animals, vehicles, treats and decorations) with a white die-cut border, as printable Letter / A4 sheets
(print on sticker paper) plus transparent PNGs for digital planners such as GoodNotes. Drawn by stickers.py, so every pack is different."""
from __future__ import annotations

import io
import math
import random
import tempfile
import zipfile
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image
from pydantic import BaseModel, Field

from .. import kidsart, stickers
from ..niches import NicheProfile
from ..render import mockups
from ..render.pdf import render_many
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register

PER_SHEET = 12
PTC_W_IN, PTC_H_IN, PTC_MARGIN_IN, PTC_PER_SHEET = 6.75, 9.25, 0.2, 9   # inside the 6.75 x 9.25 in print area Cricut Design Space allowed on Letter
PTC_README = """{title}: print-then-cut files

Each sheet-NN-print.png is a transparent PNG of {w} x {h} in at 300 DPI with the stickers already laid out ({sheets} sheet(s), 9 stickers each).
Upload it as a "Complex" image, remove nothing, choose "Print Then Cut", keep the size, print on sticker paper, then cut. Do not enlarge it:
the machine's software adds its own registration marks inside its print area, so no marks are drawn on these files.

sheet-NN-cut-lines.svg holds the cut line of every sticker in the same positions (inches, hairline red) for cutters that read an SVG cut line
(Silhouette, Brother, Glowforge, or a plotter). Match it to the printed sheet in your software.

Tips: print at 100% (no "fit to page"), use the "Bleed" option if your software has one, and test one sheet before a full run.
Print-then-cut limits and the way registration marks work change between software versions; check your machine's current help pages.
Personal use only: please do not resell or share the files.
"""
STICKER_PX = 900   # each sticker is drawn at 3 in x 3 in, 300 DPI, before trimming


class StickerContent(BaseModel):
    title: str
    subtitle: str = "Printable and digital stickers"
    tagline: str = Field(description="One short, warm line (<= 70 chars)")
    count: int = Field(default=24, ge=12, le=48, description="Number of stickers")


def _theme(options: dict) -> str:
    t = str(options.get("theme") or "mixed")
    if t not in kidsart.THEMES:
        raise ValueError(f"unknown sticker theme '{t}'. Choose one of: {', '.join(kidsart.THEMES)}")
    return t


@register
class StickerSheets(ProductType[StickerContent]):
    key = "sticker_sheets"
    label = "Sticker sheets"
    description = "Colourful stickers with a white die-cut border: printable sheets (Letter and A4) for sticker paper plus transparent PNGs for GoodNotes and other planners."
    content_model = StickerContent
    default_sizes = ["letter", "a4"]
    supported_sizes = ["letter", "a4"]
    price_range = (3.0, 8.0)
    typical_formats = "PDF sheets (Letter and A4) + transparent PNG stickers"
    niche_in_copy = False
    copy_audience = "planner lovers, journal keepers, kids and crafters"
    title_suffix = " Sticker Sheets"
    how_steps = ("Purchase and download your files instantly.", "Print the sheet on sticker paper at Actual size (or on plain paper for glue-stick stickers), then cut out each sticker. "
                 "For a digital planner, add the transparent PNGs from the PNG folder to GoodNotes, Notability or similar.", "Stick, plan and decorate. Print again as often as you like for yourself.")

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> StickerContent:
        n = max(12, min(int(options.get("stickers", 24)), 48))
        return StickerContent(title=f"{kidsart.THEMES[_theme(options)][0]} Sticker Sheets", subtitle=f"{n} printable and digital stickers", tagline="Cute stickers for planners, journals and fun.", count=n)

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return (f"Write a short cheerful title and tagline for a pack of colourful STICKER SHEETS with the theme '{kidsart.THEMES[_theme(options)][0]}' "
                f"({int(options.get('stickers', 24))} stickers, printable plus digital PNGs). End the title with 'Sticker Sheets'. Do not mention any niche or profession.")

    def _print_then_cut(self, ctx: BuildContext, slug: str, title: str, cut: list[Image.Image]) -> ProductFile:
        """Print-then-cut files: per sheet a transparent PNG inside the cutting machine's print area, plus a cut-line SVG in the same position."""
        dpi = 300
        w_px, h_px = round(PTC_W_IN * dpi), round(PTC_H_IN * dpi)
        sheets = math.ceil(len(cut) / PTC_PER_SHEET)
        out = ctx.out_dir / f"{slug}-print-then-cut.zip"
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for k in range(sheets):
                chunk = cut[k * PTC_PER_SHEET:(k + 1) * PTC_PER_SHEET]
                im = stickers.pack_sheet(chunk, w_px, h_px, round(PTC_MARGIN_IN * dpi), cols=3, rows=3, bg="transparent")
                buf = io.BytesIO()
                im.save(buf, "PNG", dpi=(dpi, dpi))
                z.writestr(f"sheet-{k + 1:02d}-print.png", buf.getvalue())
                place = stickers.pack_layout([c.size for c in chunk], w_px, h_px, round(PTC_MARGIN_IN * dpi), cols=3, rows=3)
                d = " ".join(p for c, (x, y, tw, th) in zip(chunk, place) for p in stickers.cut_paths(c, x, y, tw, th, dpi))
                z.writestr(f"sheet-{k + 1:02d}-cut-lines.svg",
                           f"<svg xmlns='http://www.w3.org/2000/svg' width='{PTC_W_IN}in' height='{PTC_H_IN}in' viewBox='0 0 {PTC_W_IN} {PTC_H_IN}'>"
                           f"<path d='{d}' fill='none' stroke='#ff0000' stroke-width='0.006'/></svg>")
            z.writestr("READ-ME-print-then-cut.txt", PTC_README.format(title=title, w=PTC_W_IN, h=PTC_H_IN, sheets=sheets))
        return ProductFile(out, "zip", "Print-then-cut sheets (PNG + cut lines)", True)

    def build(self, ctx: BuildContext, content: StickerContent) -> BuildResult:
        theme = _theme(ctx.options)
        content = content.model_copy(update={"title": self.unique_title(ctx, content.title)})
        slug = self.slug(content.title)
        n = max(12, min(int(ctx.options.get("stickers", content.count)), 48))
        pal = ctx.style.palette
        art_dir = ctx.out_dir.parent / "art"
        art_dir.mkdir(exist_ok=True)

        items = [stickers.sticker_svg(i, ctx.seed, theme, pal) for i in range(n)]
        pages = "".join(f"<div class='p'>{svg}</div>" for _, svg in items)
        html = ("<style>@page{size:3in 3in;margin:0}html,body{margin:0;background:none}.p{width:3in;height:3in;page-break-after:always}"
                ".p svg{width:3in;height:3in;display:block}</style>" + pages)
        pdf = art_dir / f"{slug}-art.pdf"
        renderer = render_many([(html, pdf, "3in 3in")])[0]
        cut: list[Image.Image] = []
        doc = pdfium.PdfDocument(str(pdf))
        try:
            for i in range(n):
                im = doc[i].render(scale=STICKER_PX / 216, fill_color=(255, 255, 255, 0)).to_pil().convert("RGBA")
                cut.append(stickers.die_cut(im))
        finally:
            doc.close()

        sheets = math.ceil(n / PER_SHEET)
        files: list[ProductFile] = []
        for size in ctx.sizes:
            page = ctx.page(size)
            w, h = round(page.width_in * 300), round(page.height_in * 300)
            ims = [stickers.pack_sheet(cut[k * PER_SHEET:(k + 1) * PER_SHEET], w, h, 90) for k in range(sheets)]
            out = ctx.out_dir / f"{slug}-{size}.pdf"
            ims[0].save(out, "PDF", resolution=300, save_all=True, append_images=ims[1:])
            files.append(ProductFile(out, "pdf", f"{page.label} - printable sticker sheets", True, preview_pages=list(range(min(sheets, 3)))))

        png_zip = ctx.out_dir / f"{slug}-PNG-stickers.zip"
        with zipfile.ZipFile(png_zip, "w", zipfile.ZIP_STORED) as z:
            for i, (im, (name, _)) in enumerate(zip(cut, items), 1):
                buf = io.BytesIO()
                im.save(buf, "PNG", dpi=(300, 300), optimize=True)
                z.writestr(f"{i:02d}-{name.replace(' ', '-')}.png", buf.getvalue())
            z.writestr("READ-ME.txt", f"{content.title}\n\n{n} transparent PNG stickers (300 DPI) with a white die-cut border. Add them to GoodNotes, Notability, Canva or any "
                                      "app that accepts PNG images. Personal use only: please do not resell or share the files.\n")
        files.append(ProductFile(png_zip, "zip", "Transparent PNG stickers (digital planners)", True))
        if ctx.options.get("print_then_cut"):
            files.append(self._print_then_cut(ctx, slug, content.title, cut))
        features = [f"{n} colourful stickers on {sheets} printable sheets", "US Letter and A4 PDF sheets for sticker paper", f"{n} transparent PNG stickers for GoodNotes and digital planners",
                    "White die-cut border on every sticker", "Print as many sheets as you like for yourself", "Instant download - no physical item shipped"]
        tiles = mockups.save_tiles(art_dir, cut[::3], 4)
        return BuildResult(content.title, content.subtitle, files, features, sheets, renderer, meta={"min_pages": 1, "min_px": 300, "stickers": n, "theme": theme, "mockup_tiles": tiles, "signature": sorted({n for n, _ in items})})
