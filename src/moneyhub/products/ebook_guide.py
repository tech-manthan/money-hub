"""Short printable guide (e-book style): intro, chapters with tips + action steps. Best written by an LLM; the offline
version is a thin framework you should expand."""
from __future__ import annotations

import random

from pydantic import BaseModel, Field

from ..niches import NicheProfile
from ..render.raster import pdf_page_count
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .daily_planner import _CSS as _DAILY_CSS
from .registry import register


class Chapter(BaseModel):
    title: str
    intro: str = Field(description="2-3 sentences")
    tips: list[str] = Field(min_length=4, max_length=8, description="Specific, accurate points, 1-2 sentences each")
    callout: str = Field(default="", description="One memorable takeaway sentence")
    action_steps: list[str] = Field(min_length=3, max_length=5, description="Small actions the reader can tick off")


class GuideContent(BaseModel):
    title: str
    subtitle: str = "Beginner's guide"
    tagline: str
    intro: str
    disclaimer: str = Field(default="", description="Needed for health, money, legal topics: general information only")
    chapters: list[Chapter] = Field(min_length=4, max_length=10)


@register
class EbookGuide(ProductType[GuideContent]):
    key = "ebook_guide"
    label = "Short guide"
    description = "Printable beginner guide with chapters, key points and action steps (LLM-written; review facts before selling)."
    content_model = GuideContent
    price_range = (4.0, 14.0)

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> GuideContent:
        titles = list(dict.fromkeys((niche.pain_points or ["Getting started"]) + ["Build a simple routine", "Keep going when it gets hard"]))[:5]
        chapters = []
        for i, pain in enumerate(titles):
            pool = (niche.habits + niche.prompts) or ["Start with one small step", "Review what worked", "Ask for help", "Keep it simple"]
            tips = [pool[(i * 3 + k) % len(pool)] for k in range(5)]
            chapters.append(Chapter(
                title=pain, intro=f"A common challenge for {niche.audience}. Start small and build from there.",
                tips=[t if t.endswith(("?", ".")) else t + "." for t in tips][:5] or ["Start with one small step."],
                callout=niche.affirmations[i % len(niche.affirmations)] if niche.affirmations else "",
                action_steps=["Pick one idea from this chapter", "Try it this week", "Write down what happened"]))
        return GuideContent(title=f"The {niche.name} Starter Guide", tagline=niche.tagline[:70],
                            intro=f"A short, practical guide for {niche.audience}.",
                            disclaimer="General information only; not professional advice. This offline draft is a framework: expand each chapter before selling.",
                            chapters=chapters)

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return (
            "Write a practical 6-chapter beginner's GUIDE (printable e-book) for this niche. Each chapter: a clear title, short intro, "
            "5-7 specific and ACCURATE points, one takeaway and 3-4 action steps. Do not invent statistics, studies or quotes. "
            "If the topic touches health, money, legal or safety, add a disclaimer saying it is general information, not professional advice."
        )

    def build(self, ctx: BuildContext, content: GuideContent) -> BuildResult:
        slug = self.slug(content.title)
        jobs = [(ctx.page(s), ctx.out_dir / f"{slug}-{s}.pdf", {"content": content}) for s in ctx.sizes]
        renderer = self.render_jobs(ctx, "guide.html.j2", jobs, extra_css=_DAILY_CSS, margin=3.2)
        files, pages = [], 0
        for page, out, _ in jobs:
            pages = pdf_page_count(out)
            files.append(ProductFile(out, "pdf", f"{page.label} - printable / read on screen", True, preview_pages=[0, 1, 2, 3]))
        features = [f"{len(content.chapters)} chapters", "Key points and a takeaway in every chapter", "Action steps with tick boxes and notes",
                    f"Written for {ctx.niche.audience}", "Read on screen or print"]
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer)
