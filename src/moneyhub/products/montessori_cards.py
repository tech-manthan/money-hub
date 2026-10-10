"""Montessori three-part cards: for each picture a control card (picture + name), a picture card and a name card, so a child matches, then checks.
Pictures from the kids library (any theme), names in English or Spanish / French / German (bilingual option). Printable with cut guides."""
from __future__ import annotations

import random

from pydantic import BaseModel, Field

from .. import kidsart
from ..niches import NicheProfile
from ..render.raster import pdf_page_count
from ..translations import LANGS, check_lang, tr
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register


class MontessoriContent(BaseModel):
    title: str
    subtitle: str = "Printable three-part cards"
    tagline: str = Field(description="One short, warm line (<= 70 chars)")
    count: int = Field(default=12, ge=6, le=40, description="Number of pictures (each makes three cards)")


def _theme(options: dict) -> str:
    t = str(options.get("theme") or "mixed")
    if t not in kidsart.THEMES:
        raise ValueError(f"unknown theme '{t}'. Choose one of: {', '.join(kidsart.THEMES)}")
    return t


@register
class MontessoriCards(ProductType[MontessoriContent]):
    key = "montessori_cards"
    label = "Montessori three-part cards"
    description = ("Three-part (control, picture, name) matching cards for Montessori and homeschool use: pictures from the kids library, names in English or "
                   "Spanish / French / German. Printable with cut guides.")
    content_model = MontessoriContent
    default_sizes = ["letter", "a4"]
    supported_sizes = ["letter", "a4"]
    price_range = (3.0, 9.0)
    typical_formats = "PDF (Letter and A4, printable)"
    niche_in_copy = False
    copy_audience = "Montessori, homeschool and preschool families and teachers"
    title_suffix = " Three-Part Cards"
    how_steps = ("Purchase and download your files instantly.", "Print on cardstock at Actual size and cut along the dashed lines (laminate for lasting use).",
                 "Lay out the picture cards, match the name cards, then turn over or compare with the control card to check.")

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> MontessoriContent:
        lang = check_lang(str(options.get("language") or "en"))
        n = max(6, min(int(options.get("count", 12)), 40))
        pre = "" if lang == "en" else f"{LANGS[lang]}-English "
        return MontessoriContent(title=f"{pre}{kidsart.THEMES[_theme(options)][0]} Three-Part Cards", subtitle=f"{n} pictures, {n * 3} cards", tagline="Match, read and check, the Montessori way.", count=n)

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return (f"Write a short title and tagline for a set of MONTESSORI THREE-PART CARDS (theme '{kidsart.THEMES[_theme(options)][0]}', "
                f"{int(options.get('count', 12))} pictures, language {options.get('language') or 'en'}). End the title with 'Three-Part Cards'. Do not mention any niche or profession.")

    def build(self, ctx: BuildContext, content: MontessoriContent) -> BuildResult:
        theme = _theme(ctx.options)
        lang = check_lang(str(ctx.options.get("language") or "en"))
        content = content.model_copy(update={"title": self.unique_title(ctx, content.title)})
        slug = self.slug(content.title)
        n = max(6, min(int(ctx.options.get("count", content.count)), 40))
        pool = list(kidsart.THEMES[theme][1]) if theme != "mixed" else list(kidsart.KINDS)
        pool = list(dict.fromkeys(pool))
        random.Random(ctx.seed).shuffle(pool)
        kinds = [pool[i % len(pool)] for i in range(min(n, max(len(pool), 1)))]
        items = []
        for i, k in enumerate(kinds):
            art = kidsart.figure(k, ctx.seed * 977 + i, 14, False)
            svg = f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 1000'>{art}</svg>"
            items.append({"svg": svg, "name": tr(kidsart.NAMES[k], lang), "english": kidsart.NAMES[k]})
        tctx = {"content": content, "items": items, "lang": lang, "bilingual": lang != "en"}
        jobs = [(ctx.page(s), ctx.out_dir / f"{slug}-{s}.pdf", tctx) for s in ctx.sizes]
        renderer = self.render_jobs(ctx, "montessori.html.j2", jobs, margin=0)
        files, pages = [], 0
        for page, out, _ in jobs:
            pages = pdf_page_count(out)
            files.append(ProductFile(out, "pdf", f"{page.label} - printable", True, preview_pages=[0, 1, 2]))
        features = [f"{len(items)} pictures, {len(items) * 3} cards (control, picture and name)", "Cut guides on every sheet",
                    *([f"Names in {LANGS[lang]} with the English name on the control card"] if lang != "en" else ["Lowercase names for early readers"]),
                    "Print on cardstock; laminate for lasting use", "Instant download - no physical item shipped"]
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer, meta={"pictures": len(items), "language": lang, "theme": theme, "signature": sorted({i["english"] for i in items})})
