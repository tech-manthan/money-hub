"""Checklist pack: printable tick-box checklists, each on its own page."""
from __future__ import annotations

import random

from pydantic import BaseModel, Field

from ..niches import NicheProfile
from ..render.raster import pdf_page_count
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .daily_planner import _CSS as _DAILY_CSS
from .registry import register


class Group(BaseModel):
    name: str = Field(description="Section name, <= 4 words")
    items: list[str] = Field(min_length=3, max_length=12, description="Concrete tick-box items, <= 12 words each")


class Checklist(BaseModel):
    title: str
    intro: str = Field(default="", description="One sentence on when to use it")
    groups: list[Group] = Field(min_length=2, max_length=5)


class ChecklistContent(BaseModel):
    title: str
    subtitle: str = "Printable checklist bundle"
    tagline: str
    checklists: list[Checklist] = Field(min_length=4, max_length=16)


@register
class ChecklistPack(ProductType[ChecklistContent]):
    key = "checklist_pack"
    label = "Checklist pack"
    description = "A bundle of niche-specific printable checklists (routines, prep lists, resets, supplies)."
    content_model = ChecklistContent
    price_range = (3.0, 9.0)

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> ChecklistContent:
        h = list(niche.habits)
        rng.shuffle(h)
        boxes = list(niche.weekly_boxes)
        cls = [
            Checklist(title="Daily routine", intro="A quick tick-through to keep the basics covered.", groups=[
                Group(name="Morning", items=h[:4] or ["Start the day"]), Group(name="Evening", items=(h[4:8] + ["Plan tomorrow", "Wind down"])[:4])]),
            Checklist(title="Weekly reset", intro="Do this on the same day every week.", groups=[
                Group(name="Look back", items=["Review last week's wins", "Move unfinished tasks", "Check upcoming dates"]),
                Group(name="Look ahead", items=[f"Fill in: {b.lower()}" for b in boxes[:4]] or ["Plan the week"])]),
            Checklist(title="Monthly review", groups=[
                Group(name="Progress", items=["What worked this month?", "What did not?", "What will I change?"]),
                Group(name="Admin", items=["Update goals", "Clear clutter", "Celebrate a win"])]),
            Checklist(title="Before you begin", intro="Gather everything so it is easy to start.", groups=[
                Group(name="Set up", items=["Choose a calm time", "Prepare your space", "Silence notifications"]),
                Group(name="Supplies", items=[f"Gather what you need for {niche.name.lower()}", "Pens or stylus", "Water within reach"])]),
            Checklist(title="Bad day plan", intro="For days when everything feels like too much.", groups=[
                Group(name="Keep it small", items=["Pick one thing that matters", "Do the 5-minute version", "Ask for help"]),
                Group(name="Look after you", items=["Drink water", "Eat something", "Rest without guilt"])]),
            Checklist(title="Quarterly goals check", groups=[
                Group(name="Goals", items=["Write down 3 goals", "Break each into steps", "Schedule the first step"]),
                Group(name="Support", items=["Who can help?", "What could get in the way?", "How will I celebrate?"])]),
        ]
        return ChecklistContent(title=f"{niche.name} Checklist Bundle", tagline=niche.tagline[:70], checklists=cls)

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return (
            "Write a bundle of 10 printable CHECKLISTS for this niche. Each has 2-4 sections of concrete tick-box items "
            "that this audience would genuinely use (routines, prep lists, resets, supplies, appointments, special occasions). "
            "Items must be specific actions, not vague advice, and no checklist should repeat another's items."
        )

    def build(self, ctx: BuildContext, content: ChecklistContent) -> BuildResult:
        slug = self.slug(content.title)
        jobs = [(ctx.page(s), ctx.out_dir / f"{slug}-{s}.pdf", {"content": content}) for s in ctx.sizes]
        renderer = self.render_jobs(ctx, "checklists.html.j2", jobs, extra_css=_DAILY_CSS + _CL_CSS, margin=3.0)
        files, pages = [], 0
        for page, out, _ in jobs:
            pages = pdf_page_count(out)
            files.append(ProductFile(out, "pdf", f"{page.label} - printable", True, preview_pages=[0, 1, 2, 3]))
        features = [f"{len(content.checklists)} ready-to-print checklists", "Tick boxes and a notes area on every page",
                    f"Made for {ctx.niche.audience}", "Print as many copies as you need", "Letter and A4"]
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer)


_CL_CSS = """
.cl-item { font-size:1.08em; margin:.62em 0; align-items:center; }
.cl-item .sq { width:1.05em; height:1.05em; margin:0 .7em 0 0; }
"""
