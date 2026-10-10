"""Visual schedules and supports: daily routine boards, first-then, now / next / later, a choice board and a feelings board, with 24 routine
picture cards, 15 choice cards from the kids library and 12 feelings cards. Cut-out cards with hook-and-loop dot guides; large print, calm colours.
No therapy or outcome claims: these are printable picture cards and boards."""
from __future__ import annotations

import random

from pydantic import BaseModel, Field

from .. import kidsart, schedules
from ..niches import NicheProfile
from ..render.raster import pdf_page_count
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register

PER_SHEET = 15


class ScheduleContent(BaseModel):
    title: str
    subtitle: str = "Routine boards, first-then, choice and feelings cards"
    tagline: str = Field(description="One short, calm line (<= 70 chars)")


def _theme(options: dict) -> str:
    t = str(options.get("theme") or "treats")
    if t not in kidsart.THEMES:
        raise ValueError(f"unknown theme '{t}'. Choose one of: {', '.join(kidsart.THEMES)}")
    return t


def _sheets(cards: list[dict]) -> list[list[dict]]:
    out = [cards[i:i + PER_SHEET] for i in range(0, len(cards), PER_SHEET)]
    out[-1] = out[-1] + [{"svg": "", "label": "", "blank": True}] * (PER_SHEET - len(out[-1]))   # write-in cards fill the sheet
    return out


@register
class VisualSchedule(ProductType[ScheduleContent]):
    key = "visual_schedule"
    label = "Visual schedule and picture cards"
    description = ("Daily routine boards, first-then, now / next / later, a choice board and a feelings board with 24 routine picture cards, "
                   "choice cards and 12 feelings cards. Cut-out cards with hook-and-loop dot guides (PDF).")
    content_model = ScheduleContent
    default_sizes = ["letter", "a4"]
    supported_sizes = ["letter", "a4"]
    price_range = (3.0, 8.0)
    typical_formats = "PDF (Letter and A4, printable)"
    niche_in_copy = False
    copy_audience = "parents, teachers and carers"
    title_suffix = " Visual Schedule"
    how_steps = ("Purchase and download your files instantly.", "Print on cardstock at Actual size, cut out the cards and laminate them if you like.",
                 "Stick a soft (loop) hook-and-loop dot on the back of each card and a rough (hook) dot on each board space (the dashed circle shows where), then build the day together.")

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> ScheduleContent:
        return ScheduleContent(title="Daily Routine Picture Cards and Visual Schedule", subtitle="Routine boards, first-then, choice and feelings cards",
                               tagline="Calm picture cards for routines, choices and feelings.")

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return ("Write a short calm title and tagline for a printable VISUAL SCHEDULE set (daily routine board, first-then board, choice board, picture cards, feelings cards "
                "with hook-and-loop dot guides). End the title with 'Visual Schedule'. Do not mention any niche, profession, therapy, diagnosis or outcomes.")

    def build(self, ctx: BuildContext, content: ScheduleContent) -> BuildResult:
        theme = _theme(ctx.options)
        content = content.model_copy(update={"title": self.unique_title(ctx, content.title)})
        slug = self.slug(content.title)
        rng = random.Random(ctx.seed)
        routine = []
        for k in schedules.ROUTINE:
            label, svg = schedules.routine_card(k)
            routine.append({"svg": svg, "label": label})
        pool = list(dict.fromkeys(kidsart.THEMES[theme][1] if theme != "mixed" else kidsart.KINDS))
        rest = [k for k in kidsart.KINDS if k not in pool]
        rng.shuffle(pool)
        rng.shuffle(rest)
        choices = []
        for i, k in enumerate((pool + rest)[:PER_SHEET]):
            svg = f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 1000'>{kidsart.figure(k, ctx.seed * 613 + i, 14, False)}</svg>"
            choices.append({"svg": svg, "label": kidsart.NAMES[k]})
        feelings = []
        for k in schedules.FEELINGS:
            label, svg = schedules.feeling_card(k)
            feelings.append({"svg": svg, "label": label})
        card_sets = [("Routine cards", s) for s in _sheets(routine)] + [("Choice cards", s) for s in _sheets(choices)] + \
                    [("Feelings cards", s) for s in _sheets(feelings)] + [("Blank cards", [{"svg": "", "label": "", "blank": True}] * PER_SHEET)]
        tctx = {"content": content, "card_sets": card_sets, "chips": ["24 routine cards", "Choice & feelings cards", "hook-and-loop dot guides"]}
        jobs = [(ctx.page(s), ctx.out_dir / f"{slug}-{s}.pdf", tctx) for s in ctx.sizes]
        renderer = self.render_jobs(ctx, "visual_schedule.html.j2", jobs, margin=0)
        files, pages = [], 0
        for page, out, _ in jobs:
            pages = pdf_page_count(out)
            files.append(ProductFile(out, "pdf", f"{page.label} - printable", True, preview_pages=[0, 2, 3, 5, 7, 9]))
        features = ["Daily routine boards, first-then, now / next / later, choice board and feelings board",
                    f"{len(routine)} routine picture cards, {len(choices)} choice cards and {len(feelings)} feelings cards, plus blank cards to write your own",
                    "hook-and-loop dot guides on every board space and card", "Large print and calm colours; print on cardstock and laminate",
                    "US Letter and A4 PDF", "Instant download - no physical item shipped"]
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer,
                           meta={"pages": pages, "theme": theme, "routine_cards": len(routine), "choice_cards": len(choices), "feelings": len(feelings)})
