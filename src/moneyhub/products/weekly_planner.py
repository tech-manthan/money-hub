"""Undated weekly planner (printable PDFs + hyperlinked tablet PDF)."""
from __future__ import annotations

import random
from pathlib import Path

from pydantic import BaseModel, Field

from ..niches import NicheProfile
from ..render.raster import pdf_page_count
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register


class PlannerContent(BaseModel):
    title: str = Field(description="Product title shown on the cover, 2-6 words")
    subtitle: str = Field(description="Short label above the title, e.g. 'Undated weekly planner'")
    tagline: str = Field(description="One handwritten-style line under the title (<= 70 chars)")
    welcome: str = Field(description="2-3 sentence welcome that speaks to the buyer's real problem")
    how_to: list[str] = Field(min_length=3, max_length=5, description="Short how-to-use steps (<= 16 words each)")
    yearly_prompts: list[str] = Field(min_length=4, max_length=6, description="Big-picture box labels, e.g. 'My three goals'")
    monthly_prompts: list[str] = Field(min_length=2, max_length=3, description="Monthly box labels")
    weekly_boxes: list[str] = Field(min_length=4, max_length=6, description="Weekly side boxes (<= 4 words each)")
    daily_labels: list[str] = Field(min_length=3, max_length=4, description="Tiny daily checks (<= 2 words)")
    weekly_quotes: list[str] = Field(min_length=6, max_length=14, description="Short encouraging footer lines (<= 60 chars)")
    weeks: int = Field(default=52, ge=4, le=60)


@register
class WeeklyPlanner(ProductType[PlannerContent]):
    key = "weekly_planner"
    label = "Weekly planner"
    description = "Undated weekly planner with monthly overviews, goal pages and notes. Printable + hyperlinked tablet version."
    content_model = PlannerContent
    default_sizes = ["letter", "a4", "tablet"]
    supported_sizes = ["letter", "a4", "a5", "tablet"]
    price_range = (6.0, 15.0)
    typical_formats = "PDF (printable + hyperlinked tablet)"

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> PlannerContent:
        quotes = list(niche.affirmations)
        rng.shuffle(quotes)
        while len(quotes) < 6:
            quotes += quotes
        problem = niche.pain_points[0].lower() if niche.pain_points else "keeping everything organised"
        return PlannerContent(
            title=f"{niche.name} Weekly Planner",
            subtitle="Undated weekly planner",
            tagline=niche.tagline[:70],
            welcome=(
                f"This planner was made for {niche.audience}. If {problem} is your daily struggle, "
                "the layout below keeps each week light: a place for every task, a place for every worry, "
                "and room for the small wins that are easy to forget."
            ),
            how_to=[
                "Start with the Big picture pages and write down what matters this year.",
                "Pick a month page and mark the dates you cannot move.",
                "Fill in one weekly spread every Sunday or Monday morning.",
                "Review on Friday: tick, move, or let go. Begin again.",
            ],
            yearly_prompts=["My three goals", "What I want more of", "What I want less of", "Habits I will build", "People who support me", "How I will celebrate"],
            monthly_prompts=["This month's focus", "Must-do list", "Wins to celebrate"],
            weekly_boxes=niche.weekly_boxes[:6],
            daily_labels=niche.daily_labels[:4],
            weekly_quotes=quotes[:12],
            weeks=int(options.get("weeks", 52)),
        )

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return (
            "Write the copy and structure for an UNDATED WEEKLY PLANNER for this niche. "
            "Make the weekly side boxes and daily checks specific to this audience's real routines (not generic 'Notes'). "
            "The welcome text must name the audience's actual struggle in plain language. "
            f"Set weeks to {int(options.get('weeks', 52))}. Avoid cliches like 'unlock your potential'."
        )

    def build(self, ctx: BuildContext, content: PlannerContent) -> BuildResult:
        files: list[ProductFile] = []
        renderer = ""
        slug = self.slug(content.title)
        pages = 0
        for size in ctx.sizes:
            page = ctx.page(size)
            hyper = size == "tablet"
            out = ctx.out_dir / f"{slug}-{size}{'-hyperlinked' if hyper else ''}.pdf"
            renderer = self.pdf_from_template(ctx, "weekly_planner.html.j2", page, out,
                                              extra_css=_extra_css(page), content=content, hyper=hyper)
            pages = pdf_page_count(out)
            label = f"{page.label}" + (" - hyperlinked for GoodNotes / Notability" if hyper else " - printable")
            files.append(ProductFile(out, "pdf", label, True, preview_pages=[0, 2 + 0, 4, 15]))
        features = [
            f"{content.weeks} undated weekly spreads",
            "12 monthly overview pages",
            "Big-picture goal setting page",
            "8 dotted notes pages",
            f"Made for {ctx.niche.audience}",
            "Instant PDF download - print at home or at a print shop",
        ]
        if "tablet" in ctx.sizes:
            features.append("Hyperlinked tabs for GoodNotes, Notability and Samsung Notes")
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer,
                           meta={"weeks": content.weeks, "sizes": ctx.sizes})


def _extra_css(page) -> str:
    land = page.landscape
    css = """
.week .wk-body { display:flex; flex:1; min-height:0; gap:.9em; }
.week .days { flex:1; display:flex; flex-direction:column; min-height:0; }
.week .day { flex:1; display:flex; align-items:stretch; border-bottom:1px solid var(--line); min-height:0; }
.week .dname { flex:none; width:3.2em; padding-top:.35em; font-family:var(--font-h); color:var(--accent); font-size:.95em; }
.week .dname b { font-weight:700; }
.week .dname .dl { display:none; }
.week .dlines { flex:1; min-width:0; padding:.2em .3em 0 0; display:flex; flex-direction:column; }
.week .dlines .lines { flex:1; }
.week .dchecks { flex:none; width:7.6em; font-size:.62em; line-height:1.6; color:var(--muted); padding-top:.5em; white-space:nowrap; }
.week .side { flex:none; width:35%; display:flex; flex-direction:column; gap:.5em; min-height:0; }
.week .side .card { flex:1; }
"""
    if land:
        css += """
.week .wk-body { flex-direction:column; }
.week .days { display:grid; grid-template-columns:repeat(4,1fr); grid-template-rows:1fr 1fr; gap:.5em; flex:3; }
.week .day { border:1px solid var(--line); border-radius:var(--radius); flex-direction:column; padding:.35em .55em; }
.week .day.notes { border:0; padding:0; }
.week .day.notes .card { flex:1; }
.week .dname { width:auto; padding:0 0 .25em; border-bottom:1px solid var(--line); font-size:1em; }
.week .dname .ds { display:none; } .week .dname .dl { display:inline; }
.week .dlines { padding:.1em 0 0; }
.week .dchecks { width:auto; display:flex; gap:.8em; padding-top:.3em; flex-wrap:wrap; }
.week .side { width:auto; flex:1; flex-direction:row; }
.week .footer { margin-top:.5em; }
"""
    return css
