"""Guided journal: 30 prompt pages + weekly check-ins."""
from __future__ import annotations

import random

from pydantic import BaseModel, Field

from ..niches import NicheProfile
from ..render.raster import pdf_page_count
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register


class JournalDay(BaseModel):
    theme: str = Field(description="1-3 word theme for the day")
    prompt: str = Field(description="The day's journaling prompt, one or two sentences")
    nudge: str = Field(default="", description="Optional gentle tip (<= 22 words)")


class JournalContent(BaseModel):
    title: str
    subtitle: str = "30-day guided journal"
    tagline: str
    welcome: str
    how_to: list[str] = Field(min_length=3, max_length=5)
    days: list[JournalDay] = Field(min_length=14, max_length=60)
    affirmations: list[str] = Field(min_length=5, max_length=14)


_THEMES = ["Notice", "Release", "Gratitude", "Strength", "Boundaries", "Joy", "Plan", "Reflect"]
_GENERIC = [
    ("What felt easy today, and what felt heavy?", "There is no wrong answer. Just notice."),
    ("Describe one small moment from today that you want to remember.", "Think sights, sounds, smells."),
    ("Which thought keeps looping, and what would you tell a friend who had it?", ""),
    ("What is one boundary you need this week?", "Write the exact words you could use."),
    ("What are you looking forward to?", "Even something small counts."),
    ("Who made a difference to you recently, and how could you thank them?", ""),
    ("What did you do today that future you will thank you for?", ""),
    ("If tomorrow went perfectly, what would it look like?", "Be specific about the first hour."),
    ("What are you ready to let go of?", "Write it down, then cross it out if you like."),
    ("What does your body need right now?", "Rest, water, movement, quiet?"),
    ("What is a win from this week, however small?", ""),
    ("What would you try if you were not afraid of getting it wrong?", ""),
    ("Which habit is helping you most right now?", ""),
    ("What drained your energy today, and what restored it?", ""),
    ("What do you want to remember about this season of life?", ""),
    ("Write a kind note to yourself.", "Imagine you are writing to someone you love."),
    ("What is one thing you can simplify?", ""),
    ("What made you laugh or smile recently?", ""),
]


@register
class GuidedJournal(ProductType[JournalContent]):
    key = "guided_journal"
    decor_ok = True
    label = "Guided journal"
    description = "30 days of prompts with gratitude, mood and a small-step box, plus weekly check-ins."
    content_model = JournalContent
    supported_sizes = ["letter", "a4", "eink"]
    price_range = (5.0, 12.0)
    typical_formats = "PDF (printable, also fillable on a tablet)"
    layouts = {"classic": "Classic: prompt card, ruled lines, three small boxes",
               "dotted": "Dotted: big plain prompt and a dotted page for writing or sketching",
               "banner": "Banner: prompt in a coloured band, check-in every ten days",
               "open": "Open: just the prompt and a blank page"}
    auto_layout = True
    layout_marker = "Day 1"

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> JournalContent:
        specific = [(p, "") for p in niche.prompts]
        generic = list(_GENERIC)
        rng.shuffle(generic)
        days: list[JournalDay] = []
        si = gi = 0
        for i in range(30):
            # alternate niche-specific and general prompts, niche first
            if (i % 2 == 0 and si < len(specific)) or gi >= len(generic):
                prompt, nudge = specific[si % len(specific)] if specific else generic[gi % len(generic)]
                si += 1
            else:
                prompt, nudge = generic[gi]
                gi += 1
            days.append(JournalDay(theme=_THEMES[i % len(_THEMES)], prompt=prompt, nudge=nudge))
        return JournalContent(
            title=f"{niche.name} Guided Journal",
            tagline=niche.tagline[:70],
            welcome=(f"Thirty short prompts, written for {niche.audience}. Each page takes about ten minutes: "
                     "answer the prompt, name one thing you are grateful for, and pick one small step."),
            how_to=[
                "Choose a quiet time you can repeat: morning coffee or last thing at night.",
                "Read the prompt, then write without editing. Messy is fine.",
                "Finish with gratitude, one small step and your mood.",
                "Every seventh day, use the check-in page to look back.",
            ],
            days=days,
            affirmations=(list(niche.affirmations) * 2)[:14],
        )

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return (
            "Write a 30-DAY GUIDED JOURNAL for this niche: exactly 30 days. Each day has a short theme, a specific, "
            "emotionally intelligent prompt that speaks to this audience's real situation, and an optional nudge. "
            "Build a gentle arc across the 30 days (start easy, deepen in the middle, end with looking forward). "
            "Prompts must not repeat each other. Also write a welcome and four how-to steps."
        )

    def build(self, ctx: BuildContext, content: JournalContent) -> BuildResult:
        slug = self.slug(content.title)
        files, renderer, pages = [], "", 0
        jobs = [(ctx.page(s), ctx.out_dir / f"{slug}-{s}.pdf", {"content": content}) for s in ctx.sizes]
        renderer, lmeta = self.render_layout(ctx, "journal.html.j2", [(s, j[1]) for s, j in zip(ctx.sizes, jobs)], {"content": content}, lambda spec, page: _jr_css(spec, page, ctx.style), margin=3.0)
        every = lmeta["layout_spec"]["checkin_every"]
        for page, out, _ in jobs:
            pages = pdf_page_count(out)
            files.append(ProductFile(out, "pdf", f"{page.label} - printable", True, preview_pages=[0, 2, 3, 10]))
        features = [
            f"{len(content.days)} guided daily pages",
            "Gratitude, small-step and mood boxes on every page" if lmeta["layout_spec"]["bottom"] else "Open writing space on every page",
            *([f"{len(content.days) // every} reflection check-in pages"] if every else []),
            "Print at home or fill in on an iPad",
            f"Prompts written for {ctx.niche.audience}",
        ]
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer, meta=lmeta)


def _jr_css(spec, page, style) -> str:
    """Writing-area background as an SVG tile (WeasyPrint does not draw the gradient version)."""
    col = style.palette.line.replace("#", "%23")
    px = round(1.5 * page.base_pt * 96 / 72, 2)
    if spec.writing == "dotted":
        body = f"<circle cx='{px / 2}' cy='{px / 2}' r='1.3' fill='{col}'/>"
    elif spec.writing == "grid":
        body = f"<path d='M0 0H{px}M0 0V{px}' stroke='{col}' stroke-width='1' fill='none'/>"
    elif spec.writing == "blank":
        return ".jr-write .lines { background-image:none; }\n"
    else:
        return ""
    svg = f"<svg xmlns='http://www.w3.org/2000/svg' width='{px}' height='{px}' viewBox='0 0 {px} {px}'>{body}</svg>"
    return f".jr-write .lines {{ background-image:url(\"data:image/svg+xml;utf8,{svg}\"); background-size:{px}px {px}px; background-repeat:repeat; background-position:0 0; }}\n"
