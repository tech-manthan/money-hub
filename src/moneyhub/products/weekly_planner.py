"""Undated weekly planner (printable PDFs + hyperlinked tablet PDF)."""
from __future__ import annotations

import random
from pathlib import Path

from pydantic import BaseModel, Field

from .. import layouts as lay
from ..niches import NicheProfile
from ..render.html import render_html
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
    decor_ok = True
    label = "Weekly planner"
    description = "Undated weekly planner with monthly overviews, goal pages and notes. Printable + hyperlinked tablet version."
    content_model = PlannerContent
    default_sizes = ["letter", "a4", "tablet"]
    supported_sizes = ["letter", "a4", "a5", "tablet", "eink"]
    price_range = (6.0, 15.0)
    typical_formats = "PDF (printable + hyperlinked tablet)"
    layouts = {"classic": "Classic: days down the left, boxes on the right",
               "grid": "Grid: all seven days in a grid, plus a notes square",
               "focus": "Focus: top priorities first, then compact day rows",
               "minimal": "Minimal: just the days and plenty of writing space"}
    auto_layout = True
    layout_marker = "Week 1"

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
        slug = self.slug(content.title)
        key = self.layout_of(ctx)
        base = lay.resolve("weekly_planner", key, ctx.options, ctx.seed)
        generated = key.startswith(("auto", "custom"))
        pages, notes, jobs, meta = 0, [], [], []
        for size in ctx.sizes:
            page = ctx.page(size)
            hyper = size in ("tablet", "eink")
            out = ctx.out_dir / f"{slug}-{size}{'-hyperlinked' if hyper else ''}.pdf"
            jobs.append((page, out, {"content": content, "hyper": hyper, "spec": base.for_page(page.landscape)}))
            meta.append((page, out, hyper))
        renderer = ""
        for page, out, tctx in jobs:   # one at a time so a generated layout that overflows can fall back to classic
            spec = tctx["spec"]
            renderer = self.render_jobs(ctx, "weekly_planner.html.j2", [(page, out, tctx)], extra_css=lambda pg, sp=spec: _css(sp, pg))
            if generated and pdf_page_count(out) > _expected_pages(ctx, page, tctx, _css(spec, page)):
                notes.append(f"layout '{spec.name}' did not fit on {page.label}; used classic")
                tctx["spec"] = spec = lay.WEEKLY_PRESETS["classic"].for_page(page.landscape)
                renderer = self.render_jobs(ctx, "weekly_planner.html.j2", [(page, out, tctx)], extra_css=lambda pg, sp=spec: _css(sp, pg))
        for page, out, hyper in meta:
            pages = pdf_page_count(out)
            label = f"{page.label}" + (" - hyperlinked for GoodNotes / Notability" if hyper else " - printable")
            files.append(ProductFile(out, "pdf", label, True, preview_pages=[0, 2 + 0, 4, 15]))
        shown = jobs[0][2]["spec"]
        features = [
            f"{content.weeks} undated weekly spreads ({shown.name} layout)",
            "12 monthly overview pages",
            "Big-picture goal setting page",
            "8 dotted notes pages",
            f"Made for {ctx.niche.audience}",
            "Instant PDF download - print at home or at a print shop",
        ]
        if "tablet" in ctx.sizes:
            features.append("Hyperlinked tabs for GoodNotes, Notability and Samsung Notes")
        if "eink" in ctx.sizes:
            features.append("Black-and-white, hyperlinked pages made for reMarkable, Kindle Scribe and Boox")
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer,
                           meta={"weeks": content.weeks, "sizes": ctx.sizes, "layout": shown.name, "layout_spec": shown.model_dump(), "layout_notes": notes})


def _expected_pages(ctx: BuildContext, page, tctx: dict, extra_css: str) -> int:
    """How many pages the template should make; a PDF with more means something overflowed onto an extra page."""
    import re as _re
    html = render_html("weekly_planner.html.j2", ctx.style, page, extra_css=extra_css, margin=ctx.options.get("margin_em", 3.4), **tctx)
    return len(_re.findall(r'<section class="page', html))


_BASE = """
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
.week .hab { font-size:.62em; color:var(--muted); line-height:1.9; }
.week .hab .hrow { display:flex; align-items:center; gap:.45em; } .week .hab .hrow span { flex:1; white-space:nowrap; overflow:hidden; }
"""
_GRID_DAYS = """
.week .days { display:grid; grid-template-columns:repeat(4,1fr); grid-template-rows:1fr 1fr; gap:.5em; flex:3; }
.week .day { border:1px solid var(--line); border-radius:var(--radius); flex-direction:column; padding:.35em .55em; }
.week .day.notes { border:0; padding:0; }
.week .day.notes .card { flex:1; }
.week .dname { width:auto; padding:0 0 .25em; border-bottom:1px solid var(--line); font-size:1em; }
.week .dname .ds { display:none; } .week .dname .dl { display:inline; }
.week .dlines { padding:.1em 0 0; }
.week .dchecks { width:auto; display:flex; gap:.8em; padding-top:.3em; flex-wrap:wrap; }
.week .footer { margin-top:.5em; }
"""
_COLUMN_DAYS = """
.week .days { display:grid; grid-template-columns:repeat(7,1fr); gap:.4em; flex:3; }
.week .day { flex-direction:column; border:1px solid var(--line); border-radius:var(--radius); padding:.35em .4em; }
.week .dname { width:auto; text-align:center; border-bottom:1px solid var(--line); padding:0 0 .25em; }
.week .dlines { padding:.1em 0 0; }
.week .dchecks { width:auto; display:flex; flex-direction:column; font-size:.55em; white-space:normal; }
"""


def _css(spec, page) -> str:
    """CSS for a weekly layout spec on a page size."""
    css = _BASE
    if spec.days == "grid":
        css += _GRID_DAYS
    elif spec.days == "columns":
        css += _COLUMN_DAYS
    if spec.body == "left":
        css += ".week .wk-body { flex-direction:row-reverse; }\n"
    elif spec.body in ("top", "bottom"):
        css += (".week .wk-body { flex-direction:column; }\n.week .side { width:auto; flex:none; display:grid; "
                f"grid-template-columns:repeat({spec.side_cols},1fr); gap:.5em; }}\n.week .side .card {{ min-height:4.6em; }}\n")
        if spec.body == "top":
            css += ".week .side { order:-1; }\n"
    css += f".week .wk-body {{ gap:{ {'airy': '1.4em', 'normal': '.9em', 'tight': '.45em'}[spec.gap] }; }}\n"
    if not spec.checks:
        css += ".week .dchecks { display:none; }\n"
    if spec.day_label == "long" and spec.days == "list":
        css += ".week .dname { width:4.8em; } .week .dname .ds { display:none; } .week .dname .dl { display:inline; }\n"
    return css
