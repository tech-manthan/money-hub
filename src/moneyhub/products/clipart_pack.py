"""Clipart pack: your own abstract/boho motifs as transparent 3000 px PNGs (300 DPI) in several colourways, matching SVG vectors
and a plain-language commercial licence PDF. Drawn by the same procedural engine as the wall art, so every set is unique."""
from __future__ import annotations

import io
import random
import re
import tempfile
import zipfile
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image
from pydantic import BaseModel, Field

from ..art import MOTIFS, motif_svg
from ..config import get_config
from ..design import PALETTES, Palette
from ..niches import NicheProfile
from ..render.pdf import render_many
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register
from .wall_art import JPEG_BUDGET, srgb_profile

MOTIF_NAMES = {
    "arches": "Sunrise arches", "sun": "Rising sun", "waves": "Soft waves", "blobs": "Organic blobs", "botanical": "Botanical stems",
    "geo": "Geometric tiles", "sparkles": "Sparkles", "terrazzo": "Terrazzo chips", "rainbow": "Boho rainbow", "scallop": "Scallop scales",
    "topo": "Contour lines", "bouquet": "Wildflower bouquet", "retro": "Retro sunset bands",
}
PNG_SIZES = (3000, 2400, 2000)   # px; the first that keeps the zip under Etsy's 20 MB per file


class ClipartContent(BaseModel):
    title: str
    subtitle: str = "Commercial-use PNG + SVG clipart"
    tagline: str = Field(description="One short, warm line (<= 70 chars)")
    names: list[str] = Field(min_length=len(MOTIFS), max_length=len(MOTIFS),
                             description=f"{len(MOTIFS)} short element names (2-3 words), in the order of the motif list in the brief")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "element"


@register
class ClipartPack(ProductType[ClipartContent]):
    key = "clipart_pack"
    label = "Clipart pack"
    description = "Abstract boho clipart: transparent PNGs in several colourways, SVG vectors and a commercial licence PDF."
    content_model = ClipartContent
    default_sizes = ["png"]
    supported_sizes = ["png"]
    price_range = (5.0, 16.0)
    typical_formats = "PNG (transparent, 300 DPI) + SVG + licence PDF"
    niche_in_copy = False
    copy_audience = "crafters, planner makers and small shops"
    title_suffix = " Clipart Set"
    license_terms = ("Commercial use is included: use the clipart in your own finished designs and products (printables, stickers, cards, planners, "
                     "social posts, packaging) with no credit needed. You may not resell, share or redistribute the clipart files themselves, "
                     "include them in other clipart or template packs, or use them to train AI models. Full terms are in the Commercial-License PDF inside the download.")
    license_faq = "Q: Can I use it for my business? A: Yes, commercial use is included. You may not resell or share the clipart files themselves. See the licence PDF."
    how_steps = ("Purchase and download your files instantly.", "Unzip, then place the PNG or SVG files in Canva, Photoshop, Procreate, Cricut Design Space or any design app.",
                 "Create and sell your own designs, following the included licence.")

    def size_options(self):
        return [("png", "Transparent PNG (3000 px) + SVG vectors + licence PDF")]

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> ClipartContent:
        return ClipartContent(title="Boho Shapes Clipart Set", tagline="Original shapes to create with.", names=[MOTIF_NAMES[m] for m in MOTIFS])

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return ("Name the elements of a boho abstract-shapes CLIPART set for crafters and small-shop owners. Give exactly "
                f"{len(MOTIFS)} short names (2-3 words) for these shapes, in this order: " + ", ".join(f"{m} ({MOTIF_NAMES[m]})" for m in MOTIFS)
                + ". Names describe the artwork (for example 'Sunrise arches'), not the audience. Write a warm one-line tagline.")

    def colourways(self, ctx: BuildContext) -> list[Palette]:
        n = max(1, min(int(ctx.options.get("colourways", 3)), 5))
        rng = random.Random(ctx.seed)
        others = [p for p in PALETTES if p.key != ctx.style.palette.key and not p.issues()]
        rng.shuffle(others)
        return [ctx.style.palette, *others[: n - 1]]

    def build(self, ctx: BuildContext, content: ClipartContent) -> BuildResult:
        content = content.model_copy(update={"title": self.unique_title(ctx, f"{ctx.style.palette.key.replace('_', ' ').title()} Boho Shapes")})   # named after the colour, never the niche
        slug = self.slug(content.title)
        ways = self.colourways(ctx)
        names = [_slug(n) for n in content.names]
        art_dir = ctx.out_dir.parent / "art"
        art_dir.mkdir(exist_ok=True)

        # one transparent PDF per colourway (a page per motif), drawn in parallel
        css = "10in 10in"
        jobs, pdfs = [], []
        for pal in ways:
            pages = "".join(f"<div class='p'>{motif_svg(m, pal, ctx.seed * 31 + i)}</div>" for i, m in enumerate(MOTIFS))
            html = ("<style>@page{size:10in 10in;margin:0}html,body{margin:0;background:none}.p{width:10in;height:10in;page-break-after:always}"
                    f".p svg{{width:10in;height:10in;display:block}}</style>{pages}")
            pdf = art_dir / f"{slug}-{pal.key}.pdf"
            jobs.append((html, pdf, css))
            pdfs.append(pdf)
        renderer = render_many(jobs)[0]

        png_zip = ctx.out_dir / f"{slug}-PNG-transparent.zip"
        used_px, rendered = PNG_SIZES[0], []
        for px in PNG_SIZES:
            rendered = []
            for pal, pdf in zip(ways, pdfs):
                doc = pdfium.PdfDocument(str(pdf))
                try:
                    for i in range(len(MOTIFS)):
                        im = doc[i].render(scale=px / 720, fill_color=(255, 255, 255, 0)).to_pil().convert("RGBA")
                        if im.size != (px, px):
                            im = im.resize((px, px), Image.LANCZOS)
                        buf = io.BytesIO()
                        im.save(buf, "PNG", dpi=(300, 300), optimize=True, icc_profile=srgb_profile())
                        rendered.append((pal.key, i, buf.getvalue(), im))
                finally:
                    doc.close()
            used_px = px
            if sum(len(r[2]) for r in rendered) < JPEG_BUDGET:
                break
        with zipfile.ZipFile(png_zip, "w", zipfile.ZIP_STORED) as z:   # PNGs are already compressed
            for key, i, data, _ in rendered:
                z.writestr(f"{key}/{i + 1:02d}-{names[i]}.png", data)
            z.writestr("READ-ME.txt", _readme(content, ways, used_px))

        svg_zip = ctx.out_dir / f"{slug}-SVG-vector.zip"
        with zipfile.ZipFile(svg_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for pal in ways:
                for i, m in enumerate(MOTIFS):
                    svg = motif_svg(m, pal, ctx.seed * 31 + i).replace("<svg ", "<svg width='1000' height='1000' ", 1)
                    z.writestr(f"{pal.key}/{i + 1:02d}-{names[i]}.svg", svg)
            z.writestr("READ-ME.txt", "Vector (SVG) versions of the clipart. Open in Illustrator, Inkscape, Affinity, Canva or Cricut Design Space.\n"
                                       "Each file is a 1000 x 1000 square; colours can be edited. See the Commercial-License PDF for the terms.\n")

        license_pdf = ctx.out_dir / "Commercial-License.pdf"
        cfg = get_config()
        self.render_jobs(ctx, "clipart_license.html.j2", [(ctx.page("letter"), license_pdf, {"title": content.title, "count": len(MOTIFS) * len(ways), "noun": "clipart designs",
                                                         "shop": {k: (cfg.get(f"shop.{k}") or "") for k in ("name", "email", "url")}})], margin=3.0)

        previews = _previews(art_dir, ways, rendered)
        files = [ProductFile(png_zip, "zip", f"Transparent PNG files ({len(ways)} colourways, {used_px} px)", True),
                 ProductFile(svg_zip, "zip", "SVG vector files", True),
                 ProductFile(license_pdf, "pdf", "Commercial licence (PDF)", True, preview_pages=[0])]
        features = [f"{len(MOTIFS)} abstract boho clipart designs", f"{len(ways)} colourways: {len(MOTIFS) * len(ways)} transparent PNG files",
                    f"{len(MOTIFS) * len(ways)} editable SVG vector files", f"PNG at {used_px} x {used_px} px, 300 DPI, transparent background",
                    "Commercial use included, no credit needed", "Instant download - works in Canva, Procreate, Photoshop and Cricut Design Space"]
        return BuildResult(content.title, content.subtitle, files, features, len(MOTIFS) * len(ways), renderer,
                           meta={"art_previews": previews, "flat_art": True, "badges": ["Instant download", "PNG + SVG", "Commercial use"],
                                 "delivery_note": "Instant download: transparent PNG and SVG files, plus a commercial licence.", "colourways": [p.key for p in ways]})


def _readme(content: ClipartContent, ways: list[Palette], px: int) -> str:
    return (f"{content.title}\n\nTransparent PNG files, {px} x {px} px at 300 DPI, sRGB. One folder per colourway: "
            + ", ".join(p.key for p in ways) + ".\nSee the Commercial-License PDF for what you may and may not do.\n")


def _previews(art_dir: Path, ways: list[Palette], rendered: list) -> list[Path]:
    """Contact sheets (2 x 3 designs) on light and dark backgrounds, used as listing photos."""
    by_way: dict[str, list[Image.Image]] = {}
    for key, _, _, im in rendered:
        by_way.setdefault(key, []).append(im)
    out: list[Path] = []
    plan = [(ways[0], 0, "paper"), (ways[0], 6, "soft"), (ways[-1], 0, "dark"), (ways[len(ways) // 2], 6, "paper"), (ways[0], 0, "dark"), (ways[-1], 6, "soft")]
    for n, (pal, start, mode) in enumerate(plan, 1):
        bg = {"paper": pal.paper, "soft": pal.soft, "dark": pal.accent}[mode]
        sheet = Image.new("RGB", (1200, 1500), bg)
        ims = by_way[pal.key][start:start + 6]
        for k, im in enumerate(ims):
            t = im.resize((480, 480), Image.LANCZOS)
            x, y = 60 + (k % 2) * 540, 90 + (k // 2) * 450
            sheet.paste(t, (x, y), t)
        p = art_dir / f"preview-{n:02d}.png"
        sheet.save(p)
        out.append(p)
    return out
