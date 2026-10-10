"""Early-learning workbook for children (ages 3-7): colours, opposites, days, seasons, feelings, telling time, counting, shadow matching,
patterns and word tracing. Pick a focus (mixed, colours, words, numbers, time, feelings). Drawn by learning.py; Letter / A4 PDF, KDP-ready."""
from __future__ import annotations

import random

from pydantic import BaseModel, Field

from .. import learning
from ..translations import LANGS, check_lang
from ..niches import NicheProfile
from ..render.raster import pdf_page_count
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register

FOCUS_TITLES = {"mixed": "Preschool Learning", "colours": "Colors & Shapes Learning", "words": "First Words Tracing", "numbers": "Counting & Numbers Learning",
                "time": "Time, Days & Seasons Learning", "feelings": "Feelings & Opposites Learning", "handwriting": "Print Handwriting Practice",
                "cursive": "Cursive Handwriting Practice", "sightwords": "Sight Words", "stem": "STEM Shapes & Simple Machines"}


class LearningContent(BaseModel):
    title: str
    subtitle: str = "Printable early-learning worksheets"
    tagline: str = Field(description="One short, warm line (<= 70 chars)")
    pages: int = Field(default=24, ge=10, le=48, description="Number of worksheets")


def _grade(options: dict) -> str:
    g = str(options.get("grade") or "k")
    if g not in learning.GRADES:
        raise ValueError(f"unknown grade '{g}'. Choose one of: {', '.join(learning.GRADES)} (prek, k, 1, 2, 3)")
    return g


def _check_language(focus: str, lang: str) -> None:
    if lang != "en" and focus in learning.ENGLISH_ONLY:
        raise ValueError(f"The {focus} focus is English only. Use --language en, or pick another focus (mixed, colours, words, numbers, time, feelings).")


def _title(focus: str, options: dict) -> str:
    base = FOCUS_TITLES[focus]
    return f"{learning.DOLCH[_grade(options)][0]} {base}" if focus == "sightwords" else base


def _focus(options: dict) -> str:
    f = str(options.get("focus") or "mixed")
    if f not in learning.FOCUS:
        raise ValueError(f"unknown focus '{f}'. Choose one of: {', '.join(learning.FOCUS)}")
    return f


@register
class LearningWorkbook(ProductType[LearningContent]):
    key = "learning_workbook"
    label = "Kids learning workbook"
    description = ("Early-learning worksheets for ages 3-7: colours, opposites, days of the week, seasons, feelings, telling time, counting, shadow matching, patterns "
                   "and word tracing. Choose a focus. PDF, KDP-ready.")
    content_model = LearningContent
    default_sizes = ["letter", "a4"]
    supported_sizes = ["letter", "a4"]
    price_range = (3.0, 10.0)
    typical_formats = "PDF (Letter and A4, printable)"
    niche_in_copy = False
    copy_audience = "parents, preschool and homeschool teachers"
    title_suffix = " Workbook for Kids"
    how_steps = ("Purchase and download your files instantly.", "Print the worksheets you need on regular paper (use Actual size).",
                 "Work through them with pencils and crayons, a page a day. Print again as often as you like for your family or classroom.")

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> LearningContent:
        n = max(10, min(int(options.get("pages", 24)), 48))
        lang = check_lang(str(options.get("language") or "en"))
        pre = "" if lang == "en" else f"{LANGS[lang]}-English "
        _check_language(_focus(options), lang)
        return LearningContent(title=f"{pre}{_title(_focus(options), options)} Workbook for Kids", subtitle=f"{n} printable worksheets for ages 3-7",
                               tagline="Colors, counting, words and more, one page at a time.", pages=n)

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return (f"Write a short cheerful title and tagline for a PRESCHOOL / KINDERGARTEN-PREP learning workbook with focus '{_focus(options)}'{' (' + learning.DOLCH[_grade(options)][0] + ' sight word list)' if _focus(options) == 'sightwords' else ''} (ages 3-7). "
                f"Set pages to {int(options.get('pages', 24))}. End the title with 'Workbook for Kids'. Do not mention any niche or profession.")

    def build(self, ctx: BuildContext, content: LearningContent) -> BuildResult:
        focus = _focus(ctx.options)
        lang = check_lang(str(ctx.options.get("language") or "en"))
        _check_language(focus, lang)
        grade = _grade(ctx.options)
        content = content.model_copy(update={"title": self.unique_title(ctx, content.title)})
        slug = self.slug(content.title)
        n = max(10, min(int(ctx.options.get("pages", content.pages)), 48))
        kdp = bool(ctx.options.get("kdp"))
        plan = [learning.page_art(i, ctx.seed, focus, lang, grade) for i in range(n)]
        kinds, arts, captions = (list(x) for x in zip(*plan))
        margin = ctx.options.get("margin_em", 3.0)
        jobs = []
        for size in ctx.sizes:
            page = ctx.page(size)
            side = min(page.width_in * 72 / page.base_pt - 2 * margin - 2.4, page.height_in * 72 / page.base_pt - 2 * margin - 7.0)
            sized = lambda svg, s: svg.replace("<svg ", f"<svg width='{s:.2f}em' height='{s:.2f}em' ", 1)   # noqa: E731
            cover = sized(learning.page_art(0, ctx.seed, "colours")[1], side * .62)
            jobs.append((page, ctx.out_dir / f"{slug}-{size}.pdf", {"content": content, "arts": [sized(a, side) for a in arts], "captions": captions, "side": round(side, 2),
                                                                      "kdp": kdp, "cover": cover, "cover_side": round(side * .62, 2),
                                                                      "chips": [f"{n} worksheets", "Ages 3-7", "Print as often as you like"]}))
        renderer = self.render_jobs(ctx, "coloring.html.j2", jobs, margin=margin)
        files, pages = [], 0
        for page, out, _ in jobs:
            pages = pdf_page_count(out)
            files.append(ProductFile(out, "pdf", f"{page.label} - printable", True, preview_pages=[1, 2, 3, 4, 5, 6]))
        topics = sorted({k for k in kinds})
        nice = {"colours": "colors", "opposites": "opposites", "days": "days of the week", "seasons": "seasons", "feelings": "feelings", "time": "telling time",
                "counting": "counting", "shadows": "shadow matching", "patterns": "patterns", "words": "word tracing", "letterform": "letter formation",
                "handwords": "word writing", "lined": "lined writing paper", "sight_trace": "sight word tracing", "sight_rainbow": "rainbow writing",
                "sight_fill": "missing letters", "sight_lookcover": "look, cover, write, check", "shapenames": "shape names", "solids": "3D shapes",
                "shapecount": "counting shapes", "machines": "simple machines"}
        features = [f"{n} printable learning worksheets for ages 3-7", "Topics: " + ", ".join(nice[t] for t in topics),
                    *([f"Sight words from the {learning.DOLCH[grade][0]} Dolch list ({len(learning.sight_words(grade))} words)"] if focus == "sightwords" else []), "Big pictures and bold lines for little hands", *([f"Bilingual: {LANGS[lang]} words with English instructions"] if lang != "en" else []),
                    "US Letter and A4 PDF", "Print as many copies as you like for your family or classroom", "Instant download - no physical item shipped"]
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer, meta={"pages": n, "focus": focus, "language": lang, "grade": grade if focus == "sightwords" else "", "kinds": kinds})
