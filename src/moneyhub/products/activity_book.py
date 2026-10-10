"""Children's activity book: mazes with an answer key, dot-to-dot, letter and number tracing, odd-one-out. Drawn by activities.py, so every
book has new mazes and puzzles. Letter / A4 PDF; KDP-ready (blank backs, answer pages at the end)."""
from __future__ import annotations

import random

from pydantic import BaseModel, Field

from .. import activities, kidsart
from ..niches import NicheProfile
from ..render.raster import pdf_page_count
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register


class ActivityContent(BaseModel):
    title: str
    subtitle: str = "Mazes, dot-to-dot, tracing and puzzles"
    tagline: str = Field(description="One short, warm line (<= 70 chars)")
    pages: int = Field(default=24, ge=10, le=48, description="Number of activity pages")


def _level(options: dict) -> str:
    v = str(options.get("level") or "kids")
    if v not in activities.LEVELS:
        raise ValueError(f"unknown level '{v}'. Choose one of: {', '.join(activities.LEVELS)}")
    return v


@register
class ActivityBook(ProductType[ActivityContent]):
    key = "activity_book"
    label = "Kids activity book"
    description = "Mazes with answer pages, dot-to-dot, letter and number tracing and odd-one-out puzzles for children, in three difficulty levels (PDF, KDP-ready)."
    content_model = ActivityContent
    default_sizes = ["letter", "a4"]
    supported_sizes = ["letter", "a4"]
    price_range = (3.0, 9.0)
    typical_formats = "PDF (Letter and A4, printable)"
    niche_in_copy = False
    copy_audience = "parents, teachers and kids"
    title_suffix = " Activity Book for Kids"
    how_steps = ("Purchase and download your files instantly.", "Print the pages you want on regular paper (use Actual size).",
                 "Solve with a pencil or crayon. The maze answers are on the last pages. Print again as often as you like for your family or classroom.")

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> ActivityContent:
        n = max(10, min(int(options.get("pages", 24)), 48))
        lv = {"toddler": "Little Learner", "kids": "Fun Puzzle", "big": "Super Brain"}[_level(options)]
        th = str(options.get("theme") or "mixed")
        pre = f"{kidsart.THEMES[th][0]} " if th in kidsart.THEMES and th != "mixed" else ""
        return ActivityContent(title=f"{pre}{lv} Activity Book for Kids", subtitle=f"{n} pages of mazes, dot-to-dot, tracing and puzzles", tagline="Mazes, dots and letters to keep little minds busy.", pages=n)

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return (f"Write a short cheerful title and tagline for a CHILDREN'S ACTIVITY BOOK ({_level(options)} level) with mazes, dot-to-dot, letter tracing and odd-one-out "
                f"puzzles. Set pages to {int(options.get('pages', 24))}. End the title with 'Activity Book for Kids'. Do not mention any niche or profession.")

    def build(self, ctx: BuildContext, content: ActivityContent) -> BuildResult:
        level = _level(ctx.options)
        theme = str(ctx.options.get("theme") or "mixed")
        if theme not in kidsart.THEMES:
            raise ValueError(f"unknown theme '{theme}'")
        content = content.model_copy(update={"title": self.unique_title(ctx, content.title)})
        slug = self.slug(content.title)
        n = max(10, min(int(ctx.options.get("pages", content.pages)), 48))
        kdp = bool(ctx.options.get("kdp"))
        plan = [activities.page_art(i, ctx.seed, level, theme) for i in range(n)]
        kinds, arts, captions = (list(x) for x in zip(*plan))
        maze_seeds = [ctx.seed * 1009 + i * 31 for i, k in enumerate(kinds) if k == "maze"]
        for g in range(0, len(maze_seeds), 4):   # answer pages, four mazes each
            arts.append(activities.maze_answers(level, maze_seeds[g:g + 4]))
            captions.append("Answers: the dotted line is the way out")
            kinds.append("answers")
        margin = ctx.options.get("margin_em", 3.0)
        jobs = []
        for size in ctx.sizes:
            page = ctx.page(size)
            side = min(page.width_in * 72 / page.base_pt - 2 * margin - 2.4, page.height_in * 72 / page.base_pt - 2 * margin - 7.0)
            sized = lambda svg, s: svg.replace("<svg ", f"<svg width='{s:.2f}em' height='{s:.2f}em' ", 1)   # noqa: E731
            cover = sized(activities.maze_page(level, ctx.seed), side * .62)
            jobs.append((page, ctx.out_dir / f"{slug}-{size}.pdf", {"content": content, "arts": [sized(a, side) for a in arts], "captions": captions, "side": round(side, 2),
                                                                      "kdp": kdp, "cover": cover, "cover_side": round(side * .62, 2),
                                                                      "chips": [f"{n} pages", "Mazes, dots & tracing", "Answers included"]}))
        renderer = self.render_jobs(ctx, "coloring.html.j2", jobs, margin=margin)
        files, pages = [], 0
        for page, out, _ in jobs:
            pages = pdf_page_count(out)
            files.append(ProductFile(out, "pdf", f"{page.label} - printable", True, preview_pages=[1, 2, 3, 4, 5, 6]))
        mix = {k: kinds.count(k) for k in ("maze", "dots", "letter", "number", "odd")}
        features = [f"{n} printable activity pages", f"{mix['maze']} mazes with an answer key, {mix['dots']} dot-to-dot pictures, {mix['letter']} letter and {mix['number']} number tracing pages",
                    f"{mix['odd']} odd-one-out puzzles", {"toddler": "Easy mazes and thick lines for ages 2-4", "kids": "Made for ages 4-7", "big": "Harder mazes and 38-dot pictures for ages 6-9"}[level],
                    "US Letter and A4 PDF", "Print as many copies as you like for your family or classroom", "Instant download - no physical item shipped"]
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer, meta={"pages": n, "level": level, "mix": mix})
