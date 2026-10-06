"""Listing copy: titles, tags, descriptions, pin text. LLM-written when available, rule-based otherwise;
always sanitised to each marketplace's limits."""
from __future__ import annotations

import random
import re

from pydantic import BaseModel, Field

from ..llm import LLMRouter
from ..niches import NicheProfile
from ..products.base import BuildResult, ProductType

ETSY_TITLE_MAX = 140
ETSY_TAG_MAX_LEN = 20
ETSY_TAG_COUNT = 13
PIN_TITLE_MAX = 100
PIN_DESC_MAX = 500

AI_DISCLOSURE = (
    "Designed by the seller with AI-assisted tools. All layouts, copy and final files were directed, reviewed "
    "and edited by the seller."
)


class ListingCopy(BaseModel):
    title: str = Field(description="Etsy listing title, <= 140 chars, most important keywords first, no emojis")
    short_title: str = Field(description="Gumroad/Payhip product name, <= 60 chars")
    tags: list[str] = Field(min_length=8, max_length=20, description="13 Etsy tags, each <= 20 chars, multi-word, no duplicates of the title")
    intro: str = Field(description="2-3 sentence opening paragraph that speaks to the buyer's problem")
    faq: list[str] = Field(min_length=2, max_length=5, description="Short Q&A lines, 'Q: ... A: ...'")
    pin_titles: list[str] = Field(min_length=4, max_length=8, description="Pinterest pin titles <= 100 chars, keyword rich")
    pin_headlines: list[str] = Field(min_length=4, max_length=8, description="Short text for pin images, <= 8 words")
    pin_description: str = Field(description="Pinterest description <= 500 chars, natural keywords, ends with a call to action")


class ListingKit(BaseModel):
    copy_: ListingCopy
    description: str
    price: float
    price_note: str
    ai_disclosure: str = AI_DISCLOSURE
    source: str = "builtin"


def _clip(text: str, n: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= n:
        return text
    cut = text[:n]
    return cut[: cut.rfind(" ")].rstrip(",;:-| ") if " " in cut else cut


def sanitize(copy: ListingCopy) -> ListingCopy:
    seen, tags = set(), []
    for t in copy.tags:
        t = re.sub(r"[^A-Za-z0-9 \-']", "", t).strip().lower()
        if t and len(t) <= ETSY_TAG_MAX_LEN and t not in seen:
            seen.add(t)
            tags.append(t)
    return copy.model_copy(update={
        "title": _clip(copy.title, ETSY_TITLE_MAX),
        "short_title": _clip(copy.short_title, 60),
        "tags": tags[:ETSY_TAG_COUNT],
        "pin_titles": [_clip(t, PIN_TITLE_MAX) for t in copy.pin_titles],
        "pin_headlines": [_clip(t, 60) for t in copy.pin_headlines],
        "pin_description": _clip(copy.pin_description, PIN_DESC_MAX),
    })


_TYPE_WORDS = {
    "weekly_planner": ["weekly planner", "undated planner", "printable planner", "goodnotes planner", "digital planner", "planner pdf"],
    "habit_tracker": ["habit tracker", "habit tracker printable", "excel habit tracker", "google sheets habit", "monthly habit", "routine tracker"],
    "budget_tracker": ["budget planner", "budget spreadsheet", "excel budget", "google sheets budget", "expense tracker", "budget template"],
    "guided_journal": ["guided journal", "journal prompts", "printable journal", "30 day journal", "daily journal", "journal pdf"],
    "worksheet_pack": ["printable worksheets", "worksheet pack", "classroom printables", "homeschool worksheets", "practice sheets", "worksheets pdf"],
    "card_deck": ["printable cards", "affirmation cards", "prompt cards", "card deck", "flash cards", "cards pdf"],
    "wall_art": ["printable wall art", "digital wall art", "wall art set", "poster print", "affirmation print", "downloadable art"],
    "daily_planner": ["daily planner", "daily planner printable", "to do list", "day planner pdf", "daily schedule", "productivity planner"],
    "checklist_pack": ["printable checklists", "checklist bundle", "to do checklist", "organizer printable", "checklist pdf", "planner inserts"],
    "ebook_guide": ["printable guide", "beginner guide pdf", "digital guide", "how to guide", "starter guide", "cheat sheet pdf"],
}


def _builtin_copy(niche: NicheProfile, ptype: ProductType, build: BuildResult, rng: random.Random) -> ListingCopy:
    words = _TYPE_WORDS.get(ptype.key, [ptype.label.lower()])
    nm = niche.name
    title_parts = [f"{nm} {ptype.label}", words[1 % len(words)].title(), words[2 % len(words)].title(), "Instant Download", "Printable PDF" if "PDF" in ptype.typical_formats else "Digital Download",
                   niche.seo_keywords[0].title() if niche.seo_keywords else ""]
    seen_t, uniq = set(), []
    for part in title_parts:
        if part and part.lower() not in seen_t:
            seen_t.add(part.lower())
            uniq.append(part)
    title = ", ".join(uniq)
    tags: list[str] = []
    for kw in niche.seo_keywords + words + [f"{nm.lower()} {ptype.label.lower()}", "instant download", "digital download", "printable"]:
        kw = kw.lower().strip()
        if 3 <= len(kw) <= ETSY_TAG_MAX_LEN and kw not in tags:
            tags.append(kw)
    pains = niche.pain_points or ["staying organised"]
    intro = (
        f"Made for {niche.audience}. If {pains[0].lower()} sounds familiar, this {ptype.label.lower()} gives you a simple, "
        f"beautiful place to start - download it, print it or open it on your device, and begin today."
    )
    kw = niche.seo_keywords[:3] or [nm.lower()]
    pin_titles = [
        f"{nm} {ptype.label}: {kw[0]} you will actually use",
        f"Printable {nm.lower()} {ptype.label.lower()} (instant download)",
        f"{kw[0].title()} - a simple {ptype.label.lower()} for {nm.lower()}s"[:100],
        f"A {ptype.label.lower()} made for {niche.audience.split(' who ')[0]}"[:100],
        f"{nm} {words[0]} - {rng.choice(['digital download', 'PDF', 'print at home'])}",
        f"Best {nm.lower()} {words[1 % len(words)]} to start this week",
    ]
    headlines = [
        niche.tagline.rstrip(".") or f"{nm} {ptype.label}", f"{nm} {ptype.label}", f"Made for {nm.lower()}s"[:48],
        "Print it. Plan it. Do it.", "Instant download", f"For {nm.lower()}s"[:40],
    ]
    pin_desc = (
        f"Looking for a {nm.lower()} {ptype.label.lower()}? This printable is made for {niche.audience}. "
        f"Includes {', '.join(build.features[:3]).lower()}. Instant download - save this pin and get yours today."
    )
    return ListingCopy(
        title=title, short_title=f"{nm} {ptype.label}", tags=tags[:ETSY_TAG_COUNT + 4], intro=intro,
        faq=[
            "Q: How do I receive the files? A: Instantly after purchase - you get a download link by email and on your purchases page.",
            "Q: Can I print it at home? A: Yes. Print on regular paper or cardstock, at home or at a print shop.",
            "Q: Can I resell or share the files? A: No - personal use only. Please do not redistribute or resell.",
        ],
        pin_titles=pin_titles, pin_headlines=headlines, pin_description=pin_desc,
    )


def _description(copy: ListingCopy, build: BuildResult, ptype: ProductType) -> str:
    inc = "\n".join(f"- {f}" for f in build.features)
    files = "\n".join(f"- {f.label}" for f in build.files if f.primary)
    faq = "\n".join(copy.faq)
    return (
        f"{copy.intro}\n\n"
        f"WHAT'S INCLUDED\n{inc}\n\n"
        f"FILES YOU RECEIVE\n{files}\n\n"
        "HOW IT WORKS\n1. Purchase and download your files instantly.\n"
        "2. Print at home or at a print shop, or open on your tablet/computer.\n"
        "3. Start today.\n\n"
        f"GOOD TO KNOW\n{faq}\n\n"
        "TERMS\nFor personal use only. No resale, sharing or redistribution of the digital files. "
        "Colours may vary slightly between screens and printers. This is a digital product; no physical item will be shipped.\n\n"
        f"DISCLOSURE\n{AI_DISCLOSURE}"
    )


def _price(ptype: ProductType, build: BuildResult) -> tuple[float, str]:
    lo, hi = ptype.price_range
    # more files/pages -> higher in range
    weight = min(1.0, (len(build.files) - 1) * 0.25 + min(build.page_count, 120) / 160)
    price = round(lo + (hi - lo) * weight, 0) - 0.01
    note = (f"Typical range for this product type is ${lo:.0f}-${hi:.0f}. Start near ${price:.2f}; "
            "run a launch discount (20-30%) for the first two weeks to collect reviews, and test one price change after 4 weeks.")
    return max(price, 2.99), note


def make_kit(niche: NicheProfile, ptype: ProductType, build: BuildResult, router: LLMRouter,
             rng: random.Random, providers: list[str] | None = None) -> ListingKit:
    prompt = (
        f"Product: {ptype.label} - {ptype.description}\nTitle: {build.title}\nFeatures:\n- " + "\n- ".join(build.features)
        + f"\nFormats: {ptype.typical_formats}\nNiche JSON:\n{niche.model_dump_json()}\n\n"
        "Write the marketplace listing copy. Use the exact keywords buyers would search on Etsy and Pinterest. "
        "Be truthful: only claim what the features list says."
    )
    system = ("You are an expert Etsy/Gumroad SEO copywriter. Titles front-load the strongest buyer keywords. "
              "Tags are multi-word buyer search phrases (<= 20 characters). Never make income, health or guarantee claims.")
    copy = router.complete_json("listing", system, prompt, ListingCopy, providers=providers)
    source = router.last_used or "builtin"
    if copy is None:
        copy, source = _builtin_copy(niche, ptype, build, rng), "builtin"
    copy = sanitize(copy)
    price, note = _price(ptype, build)
    return ListingKit(copy_=copy, description=_description(copy, build, ptype), price=price, price_note=note, source=source)
