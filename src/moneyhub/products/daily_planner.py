"""Undated daily planner: hourly schedule, top-3 priorities, to-do list, niche boxes."""
from __future__ import annotations

import random

from pydantic import BaseModel, Field

from .. import layouts as lay
from ..niches import NicheProfile
from ..render.html import render_html
from ..render.raster import pdf_page_count
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register


class DailyContent(BaseModel):
    title: str
    subtitle: str = "Undated daily planner"
    tagline: str = Field(description="One short line (<= 70 chars)")
    priorities_label: str = Field(default="Top 3 today", description="<= 4 words")
    todo_label: str = Field(default="To do", description="<= 3 words")
    boxes: list[str] = Field(min_length=1, max_length=3, description="1-3 niche-specific small boxes (<= 4 words)")
    daily_labels: list[str] = Field(min_length=3, max_length=4)
    quotes: list[str] = Field(min_length=6, max_length=14)
    start_hour: int = Field(default=6, ge=4, le=10)
    end_hour: int = Field(default=21, ge=16, le=24)
    days: int = Field(default=60, ge=7, le=120)


@register
class DailyPlanner(ProductType[DailyContent]):
    key = "daily_planner"
    label = "Daily planner"
    description = "Undated one-page-per-day planner with hourly schedule, priorities, to-do list and niche boxes."
    content_model = DailyContent
    default_sizes = ["letter", "a4"]
    supported_sizes = ["letter", "a4", "a5", "eink"]
    price_range = (5.0, 12.0)
    layouts = {"hourly": "Hourly: a time schedule beside priorities and to-dos",
               "priorities": "Priorities: no schedule, a long to-do list and room to think",
               "timeblock": "Time-block: plan and actual side by side for every hour"}
    auto_layout = True
    layout_marker = "Day 1"

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> DailyContent:
        q = (list(niche.affirmations) * 2)[:12]
        return DailyContent(
            title=f"{niche.name} Daily Planner", tagline=niche.tagline[:70], boxes=niche.weekly_boxes[:2] or ["Notes"],
            daily_labels=niche.daily_labels[:4] or ["Water", "Move", "Rest"], quotes=q,
            days=int(options.get("days", 60)),
        )

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return (
            "Write the content for an UNDATED DAILY PLANNER page layout for this niche. Choose box labels and daily checks "
            "that match this audience's actual day (start/end hours too: e.g. night-shift workers start later). "
            f"Set days to {int(options.get('days', 60))}."
        )

    def build(self, ctx: BuildContext, content: DailyContent) -> BuildResult:
        slug = self.slug(content.title)
        key = self.layout_of(ctx)
        spec = lay.resolve("daily_planner", key, ctx.options, ctx.seed)
        generated = key.startswith(("auto", "custom"))
        notes: list[str] = []
        jobs = [(ctx.page(s), ctx.out_dir / f"{slug}-{s}.pdf", {"content": content, "spec": spec}) for s in ctx.sizes]
        renderer = ""
        for page, out, tctx in jobs:   # one at a time so a generated layout that overflows can fall back
            renderer = self.render_jobs(ctx, "daily_planner.html.j2", [(page, out, tctx)], extra_css=_CSS + _spec_css(tctx["spec"]), margin=3.0)
            if generated:
                html = render_html("daily_planner.html.j2", ctx.style, page, extra_css=_CSS + _spec_css(tctx["spec"]), margin=ctx.options.get("margin_em", 3.0), **tctx)
                if pdf_page_count(out) > html.count('<section class="page'):
                    notes.append(f"layout '{tctx['spec'].name}' did not fit on {page.label}; used hourly")
                    tctx["spec"] = lay.DAILY_PRESETS["hourly"]
                    renderer = self.render_jobs(ctx, "daily_planner.html.j2", [(page, out, tctx)], extra_css=_CSS + _spec_css(tctx["spec"]), margin=3.0)
        files, pages = [], 0
        for page, out, _ in jobs:
            pages = pdf_page_count(out)
            files.append(ProductFile(out, "pdf", f"{page.label} - printable", True, preview_pages=[0, 1, 2, 5]))
        shown = jobs[0][2]["spec"]
        features = [f"{content.days} undated daily pages ({shown.name} layout)",
                    {"hourly": "Hourly schedule + top priorities", "timeblock": "Plan-and-actual time blocks + top priorities", "none": "Top priorities + long to-do list"}[shown.schedule],
                    "To-do list with tick boxes", f"Boxes made for {ctx.niche.name.lower()}: {', '.join(content.boxes[:max(shown.boxes, 1)])}",
                    "Letter, A4 and A5 compatible", "Print at home or at a print shop"]
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer,
                           meta={"layout": shown.name, "layout_spec": shown.model_dump(), "layout_notes": notes})


def _spec_css(spec) -> str:
    css = f".dp-sched {{ width:{spec.schedule_width}%; }}\n"
    if spec.schedule_side == "right":
        css += ".dp-body { flex-direction:row-reverse; }\n"
    if spec.schedule == "none":
        css += (".dp-side { flex-direction:row; flex-wrap:wrap; align-content:stretch; }\n.dp-side > .card { flex:1 1 46%; }\n.dp-side > .card.wide { flex:1 1 100%; }\n")
    if spec.schedule == "timeblock":
        css += ".dp-hour i { border-left:1px dashed var(--line); margin-left:.4em; }\n.dp-hour i + i { margin-left:0; }\n"
    return css


_CSS = """
.dp-body { flex:1; display:flex; gap:.8em; min-height:0; }
.dp-sched { flex:none; width:38%; }
.dp-hour { flex:1; display:flex; align-items:flex-end; border-bottom:1px solid var(--line); font-size:.62em; color:var(--muted); min-height:0; }
.dp-hour span { width:3em; flex:none; padding-bottom:.15em; }
.dp-hour i { flex:1; }
.dp-side { flex:1; display:flex; flex-direction:column; gap:.55em; min-height:0; }
.dp-side .card { min-height:0; }
.dp-pri { display:flex; align-items:flex-end; flex:1; border-bottom:1px solid var(--line); }
.dp-pri b { width:1.5em; color:var(--accent); font-family:var(--font-h); font-size:1.1em; }
.dp-pri i { flex:1; }
.dp-todo { display:flex; align-items:flex-end; flex:1; border-bottom:1px solid var(--line); padding-bottom:.1em; }
.dp-todo .sq { margin-right:.5em; margin-bottom:.15em; }
.dp-todo i { flex:1; }
.dp-checks { display:flex; flex-wrap:wrap; gap:.3em 1em; font-size:.75em; color:var(--muted); margin-top:.1em; }
.cl-item { display:flex; align-items:flex-start; margin:.3em 0; font-size:.9em; }
.cl-item .sq { flex:none; margin:.2em .6em 0 0; }
"""


