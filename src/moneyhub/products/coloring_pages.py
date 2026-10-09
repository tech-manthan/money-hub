"""Printable coloring pages: mandalas, repeat patterns and shape pictures as clean line art (PDF, Letter / A4), drawn by MoneyHub's own
engines so every pack is unique. Also a KDP coloring-book interior (a blank page behind each design)."""
from __future__ import annotations

import random

from .. import coloring
from ..niches import NicheProfile
from ..render.raster import pdf_page_count
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register
from pydantic import BaseModel, Field


class ColoringContent(BaseModel):
    title: str
    subtitle: str = "Printable coloring pages"
    tagline: str = Field(description="One short, warm line (<= 70 chars)")
    pages: int = Field(default=20, ge=10, le=40, description="Number of coloring pages")


@register
class ColoringPages(ProductType[ColoringContent]):
    key = "coloring_pages"
    label = "Coloring pages"
    description = "Printable mandala, pattern and shape coloring pages as clean line art (PDF), also usable as a KDP coloring-book interior."
    content_model = ColoringContent
    default_sizes = ["letter", "a4"]
    supported_sizes = ["letter", "a4"]
    price_range = (3.0, 9.0)
    typical_formats = "PDF (Letter and A4, printable)"
    niche_in_copy = False
    copy_audience = "colorists of all ages: kids, teens and adults"
    title_suffix = " Coloring Pages"
    how_steps = ("Purchase and download your files instantly.", "Print the pages you want on regular paper or cardstock (use Actual size).",
                 "Color with pencils, markers or gel pens. Print again as often as you like for yourself or your classroom.")

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> ColoringContent:
        n = max(10, min(int(options.get("pages", 20)), 40))
        return ColoringContent(title="Mandala & Pattern Coloring Pages", subtitle=f"{n} printable coloring pages", tagline="Calm, detailed pages to color.", pages=n)

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return ("Write a short title and warm tagline for a set of MANDALA and PATTERN coloring pages (black line art). "
                f"Set pages to {int(options.get('pages', 20))}. Do not mention any niche or profession.")

    def build(self, ctx: BuildContext, content: ColoringContent) -> BuildResult:
        slug = self.slug(content.title)
        n = max(10, min(int(ctx.options.get("pages", content.pages)), 40))
        kdp = bool(ctx.options.get("kdp"))
        kinds, arts = zip(*[coloring.page_art(i, ctx.seed, ctx.style.palette) for i in range(n)])
        margin = ctx.options.get("margin_em", 3.0)
        jobs = []
        for size in ctx.sizes:
            page = ctx.page(size)
            side = min(page.width_in * 72 / page.base_pt - 2 * margin - 2.4, page.height_in * 72 / page.base_pt - 2 * margin - 5.5)
            sized = lambda svg, s: svg.replace("<svg ", f"<svg width='{s:.2f}em' height='{s:.2f}em' ", 1)   # noqa: E731
            cover = sized(coloring.mandala(ctx.seed * 17 + 5), side * .62)
            jobs.append((page, ctx.out_dir / f"{slug}-{size}.pdf", {"content": content, "arts": [sized(a, side) for a in arts], "side": round(side, 2), "kdp": kdp,
                                                                      "cover": cover, "cover_side": round(side * .62, 2)}))
        renderer = self.render_jobs(ctx, "coloring.html.j2", jobs, margin=margin)
        files, pages = [], 0
        for page, out, _ in jobs:
            pages = pdf_page_count(out)
            files.append(ProductFile(out, "pdf", f"{page.label} - printable", True, preview_pages=[1, 2, 3, 4, 5, 6]))
        mix = {k: kinds.count(k) for k in ("mandala", "pattern", "motif")}
        features = [f"{n} printable coloring pages", f"{mix['mandala']} mandalas, {mix['pattern']} patterns and {mix['motif']} shape pictures",
                    "Clean black line art, easy to print and color", "US Letter and A4 PDF", "Print as many copies as you like for yourself or your classroom",
                    "Instant download - no physical item shipped"]
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer, meta={"pages": n, "mix": mix})
