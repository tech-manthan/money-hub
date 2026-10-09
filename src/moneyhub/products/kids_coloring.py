"""Children's coloring books: bold friendly figures (animals, sea life, vehicles, treats...), shape-face, count-and-colour and trace pages,
all drawn by kidsart.py so every book has different figures and details. Letter / A4 PDF, also a KDP interior (a blank page behind each page)."""
from __future__ import annotations

import random

from pydantic import BaseModel, Field

from .. import kidsart
from ..niches import NicheProfile
from ..render.raster import pdf_page_count
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register


class KidsContent(BaseModel):
    title: str
    subtitle: str = "Printable coloring pages for kids"
    tagline: str = Field(description="One short, warm line (<= 70 chars)")
    pages: int = Field(default=20, ge=10, le=40, description="Number of coloring pages")


def _theme(options: dict) -> str:
    t = str(options.get("theme") or "mixed")
    if t not in kidsart.THEMES:
        raise ValueError(f"unknown kids theme '{t}'. Choose one of: {', '.join(kidsart.THEMES)}")
    return t


def _age(options: dict) -> str:
    a = str(options.get("age") or "kids")
    if a not in kidsart.AGES:
        raise ValueError(f"unknown age '{a}'. Choose one of: {', '.join(kidsart.AGES)}")
    return a


@register
class KidsColoring(ProductType[KidsContent]):
    key = "kids_coloring"
    label = "Kids coloring book"
    description = ("Children's coloring pages: bold, friendly animals, sea life, vehicles and treats, plus shape, counting and tracing pages. "
                   "Different figures every time. PDF, also a KDP coloring-book interior.")
    content_model = KidsContent
    default_sizes = ["letter", "a4"]
    supported_sizes = ["letter", "a4"]
    price_range = (3.0, 9.0)
    typical_formats = "PDF (Letter and A4, printable)"
    niche_in_copy = False
    copy_audience = "parents, teachers and kids"
    title_suffix = " Coloring Pages for Kids"
    how_steps = ("Purchase and download your files instantly.", "Print the pages you want on regular paper (use Actual size).",
                 "Color with crayons, markers or pencils. Print again as often as you like for your family or classroom.")

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> KidsContent:
        n = max(10, min(int(options.get("pages", 20)), 40))
        name = kidsart.THEMES[_theme(options)][0]
        return KidsContent(title=f"{name} Coloring Pages for Kids", subtitle=f"{n} printable coloring pages for kids", tagline="Big, friendly pictures to color.", pages=n)

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return (f"Write a short, cheerful title and tagline for a CHILDREN'S coloring book with the theme '{kidsart.THEMES[_theme(options)][0]}' "
                f"(big simple figures, shape and counting pages). Set pages to {int(options.get('pages', 20))}. End the title with 'Coloring Pages for Kids'. "
                "Do not mention any niche or profession.")

    def build(self, ctx: BuildContext, content: KidsContent) -> BuildResult:
        theme, age = _theme(ctx.options), _age(ctx.options)
        content = content.model_copy(update={"title": self.unique_title(ctx, content.title)})
        slug = self.slug(content.title)
        n = max(10, min(int(ctx.options.get("pages", content.pages)), 40))
        kdp = bool(ctx.options.get("kdp"))
        plan = [kidsart.page_art(i, ctx.seed, theme, age) for i in range(n)]
        kinds, arts, captions = (list(x) for x in zip(*plan))
        margin = ctx.options.get("margin_em", 3.0)
        cover_kind = kidsart.THEMES[theme][1][ctx.seed % len(kidsart.THEMES[theme][1])]
        jobs = []
        for size in ctx.sizes:
            page = ctx.page(size)
            side = min(page.width_in * 72 / page.base_pt - 2 * margin - 2.4, page.height_in * 72 / page.base_pt - 2 * margin - 7.0)
            sized = lambda svg, s: svg.replace("<svg ", f"<svg width='{s:.2f}em' height='{s:.2f}em' ", 1)   # noqa: E731
            cover = sized(kidsart.cover_art(cover_kind, ctx.seed * 7 + 1, kidsart.AGES[age], age == "toddler"), side * .62)
            jobs.append((page, ctx.out_dir / f"{slug}-{size}.pdf", {"content": content, "arts": [sized(a, side) for a in arts], "captions": captions, "side": round(side, 2),
                                                                      "kdp": kdp, "cover": cover, "cover_side": round(side * .62, 2),
                                                                      "chips": [f"{n} pages", "Big simple pictures", "Print as often as you like"]}))
        renderer = self.render_jobs(ctx, "coloring.html.j2", jobs, margin=margin)
        files, pages = [], 0
        for page, out, _ in jobs:
            pages = pdf_page_count(out)
            files.append(ProductFile(out, "pdf", f"{page.label} - printable", True, preview_pages=[1, 2, 3, 4, 5, 6]))
        figs = sum(1 for k in kinds if k in ("figure", "scene"))
        features = [f"{n} printable coloring pages for kids", f"{figs} big friendly pictures, plus shape, counting and tracing pages",
                    "Bold, easy-to-color outlines" + (" (extra thick lines for little hands)" if age == "toddler" else ""), "US Letter and A4 PDF",
                    "Print as many copies as you like for your family or classroom", "Instant download - no physical item shipped"]
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer, meta={"pages": n, "theme": theme, "age": age, "kinds": kinds})
