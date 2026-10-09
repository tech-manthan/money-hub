"""SVG cut-file bundle for Cricut, Silhouette and other cutting machines: designs drawn as single clean outlines (nothing to weld), exported as
SVG, DXF, EPS and transparent PNG, with a commercial licence PDF. The thinnest cut-out gap is measured and checked."""
from __future__ import annotations

import io
import random
import re
import zipfile
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image
from pydantic import BaseModel, Field

from .. import cutfiles
from ..config import get_config
from ..niches import NicheProfile
from ..render.pdf import render_many
from ..render import mockups
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register


class CutContent(BaseModel):
    title: str
    subtitle: str = "SVG, DXF, EPS and PNG cut files"
    tagline: str = Field(description="One short, warm line (<= 70 chars)")
    designs: int = Field(default=24, ge=12, le=40, description="Number of cut-file designs")


@register
class CutFiles(ProductType[CutContent]):
    key = "cut_files"
    label = "SVG cut files bundle"
    description = "Cut files for Cricut and Silhouette: clean single-outline designs as SVG, DXF, EPS and PNG, with a commercial licence."
    content_model = CutContent
    default_sizes = ["svg"]
    supported_sizes = ["svg"]
    price_range = (4.0, 14.0)
    typical_formats = "SVG + DXF + EPS + PNG + licence PDF"
    niche_in_copy = False
    copy_audience = "Cricut and Silhouette crafters and small shops"
    title_suffix = " SVG Cut Files Bundle"
    license_terms = ("Commercial use is included: cut and sell the physical items you make with these files (shirts, mugs, signs, stickers, cards, decor) "
                     "with no credit needed. You may not resell, share or redistribute the cut files themselves or include them in other bundles. "
                     "Full terms are in the Commercial-License PDF inside the download.")
    license_faq = "Q: Can I sell what I make? A: Yes, commercial use is included for the physical items and finished designs you make. You may not resell the files themselves."
    how_steps = ("Purchase and download your files instantly.", "Unzip, then upload the SVG (Cricut Design Space, Silhouette Studio) or DXF (Brother ScanNCut and others) file.",
                 "Resize if you like, cut, and sell what you make, following the included licence.")

    def size_options(self):
        return [("svg", "SVG + DXF + EPS + PNG cut files (6 in designs)")]

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> CutContent:
        return CutContent(title="Boho Shapes SVG Cut Files Bundle", tagline="Clean shapes that cut beautifully.", designs=max(12, min(int(options.get("designs", 24)), 40)))

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return ("Write a short title and warm tagline for a bundle of SVG CUT FILES (simple boho shapes: stars, flowers, scallops, hearts, rainbows). "
                "Do not mention any niche or profession.")

    def build(self, ctx: BuildContext, content: CutContent) -> BuildResult:
        content = content.model_copy(update={"title": self.unique_title(ctx, content.title)})
        slug = self.slug(content.title)
        n = max(12, min(int(ctx.options.get("designs", content.designs)), 40))
        size_in = max(3.0, min(float(ctx.options.get("size_in", 6.0)), 12.0))
        designs = cutfiles.make_designs(n, ctx.seed)
        names = [f"{i + 1:02d}-{re.sub(r'[^a-z0-9]+', '-', d.name.lower()).strip('-')}" for i, d in enumerate(designs)]
        art_dir = ctx.out_dir.parent / "art"
        art_dir.mkdir(exist_ok=True)

        px = round(size_in * 300)
        html = (f"<style>@page{{size:{size_in}in {size_in}in;margin:0}}html,body{{margin:0}}.p{{width:{size_in}in;height:{size_in}in;page-break-after:always}}"
                f".p svg{{width:{size_in}in;height:{size_in}in;display:block}}</style>" + "".join(f"<div class='p'>{cutfiles.to_svg(d, size_in)}</div>" for d in designs))
        pdf = art_dir / f"{slug}.pdf"
        renderer = render_many([(html, pdf, f"{size_in}in {size_in}in")])[0]
        pngs: list[Image.Image] = []
        doc = pdfium.PdfDocument(str(pdf))
        try:
            for i in range(n):
                im = doc[i].render(scale=px / (size_in * 72), fill_color=(255, 255, 255, 0)).to_pil().convert("RGBA")
                pngs.append(im if im.size == (px, px) else im.resize((px, px), Image.LANCZOS))
        finally:
            doc.close()

        def write_zip(label: str, ext: str, make) -> Path:
            z = ctx.out_dir / f"{slug}-{label}.zip"
            with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
                for name, d, im in zip(names, designs, pngs):
                    zf.writestr(f"{name}.{ext}", make(d, im))
                zf.writestr("READ-ME.txt", _readme(content, label, size_in))
            return z

        def png_bytes(_d, im):
            buf = io.BytesIO()
            im.save(buf, "PNG", dpi=(300, 300), optimize=True)
            return buf.getvalue()
        zips = [write_zip("SVG", "svg", lambda d, _i: cutfiles.to_svg(d, size_in)), write_zip("DXF", "dxf", lambda d, _i: cutfiles.to_dxf(d, size_in)),
                write_zip("EPS", "eps", lambda d, _i: cutfiles.to_eps(d, size_in)), write_zip("PNG", "png", png_bytes)]

        cfg = get_config()
        license_pdf = ctx.out_dir / "Commercial-License.pdf"
        self.render_jobs(ctx, "clipart_license.html.j2", [(ctx.page("letter"), license_pdf, {
            "title": content.title, "count": n, "noun": "cut-file designs",
            "uses": "the physical items and finished designs you make and sell: shirts, mugs, signs, stickers, cards, decor, packaging and printables",
            "shop": {k: (cfg.get(f"shop.{k}") or "") for k in ("name", "email", "url")}})], margin=3.0)

        gap = min(cutfiles.thinnest_gap_mm(d, size_in) for d in designs)
        labels = {"SVG": "SVG files (Cricut, Silhouette, Brother)", "DXF": "DXF files (Silhouette Basic, ScanNCut)", "EPS": "EPS files (Illustrator, CorelDRAW)", "PNG": "Transparent PNG files"}
        files = [ProductFile(z, "zip", labels[z.stem.rsplit("-", 1)[-1]], True) for z in zips] + [ProductFile(license_pdf, "pdf", "Commercial licence (PDF)", True, preview_pages=[0])]
        features = [f"{n} cut-file designs", "SVG, DXF, EPS and PNG versions of every design", f"Designed at {size_in:g} inches; resize to any size",
                    "Single clean outlines: nothing to weld, ready to cut", "Commercial use included, no credit needed", "Works with Cricut, Silhouette, Brother ScanNCut and more"]
        return BuildResult(content.title, content.subtitle, files, features, n, renderer,
                           meta={"art_previews": _previews(art_dir, ctx.style.palette, pngs), "mockup_tiles": mockups.save_tiles(art_dir, pngs), "flat_art": True, "badges": ["Instant download", "SVG + DXF + EPS + PNG", "Commercial use"],
                                 "delivery_note": "Instant download: SVG, DXF, EPS and PNG cut files, plus a commercial licence.", "cut_min_gap_mm": round(gap, 1),
                                 "cut_roundtrip_problems": sorted({p for d in designs for p in cutfiles.validate_exports(d, size_in)})})


def _readme(content: CutContent, fmt: str, size_in: float) -> str:
    how = {"SVG": "Cricut Design Space: Upload > Upload Image > choose the SVG. Silhouette Studio (Designer Edition or above): File > Open. Brother, Glowforge and most cutters also open SVG.",
           "DXF": "Silhouette Studio Basic Edition and Brother ScanNCut open DXF: File > Open. The size is in inches; if a program shows it tiny (about 25 times too small), it read the units as millimetres: set the units to inches or scale it by 25.4.",
           "EPS": "For Illustrator, CorelDRAW and professional cutting software. The size is in points (72 per inch).",
           "PNG": "Transparent PNG (300 DPI) for printing, sublimation, Print Then Cut or mockups. Not for cutting directly."}[fmt]
    return (f"{content.title}\n\n{fmt} versions, designed at {size_in:g} x {size_in:g} inches. Resize freely in your cutting software.\n{how}\n"
            "Each design is one closed outline (with round or shaped cut-outs), so there is nothing to weld. Test-cut on scrap before a big job.\n"
            "See the Commercial-License PDF for what you may and may not do.\n")


def _previews(art_dir: Path, pal, pngs: list[Image.Image]) -> list[Path]:
    """Contact sheets (3 x 4 designs) in colour on light, soft and dark backgrounds."""
    def tint(im: Image.Image, colour: str) -> Image.Image:
        mask = im.getchannel("A")
        solid = Image.new("RGBA", im.size, colour)
        solid.putalpha(mask)
        return solid
    plan = [(pal_c, bg, start) for start, (pal_c, bg) in enumerate([(pal.accent, pal.paper), (pal.accent2, pal.soft), (pal.paper, pal.accent), (pal.ink, pal.soft), (pal.accent, pal.soft), (pal.accent2, pal.paper)])]
    out: list[Path] = []
    for n, (colour, bg, k) in enumerate(plan, 1):
        sheet = Image.new("RGB", (1200, 1500), bg)
        start = (k * 6) % max(len(pngs) - 11, 1)
        for j, im in enumerate(pngs[start:start + 12]):
            t = tint(im, colour).resize((330, 330), Image.LANCZOS)
            sheet.paste(t, (50 + (j % 3) * 380, 70 + (j // 3) * 345), t)
        p = art_dir / f"preview-{n:02d}.png"
        sheet.save(p)
        out.append(p)
    return out
