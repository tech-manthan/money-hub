"""Printable card deck (affirmations, prompts, flashcards): 9 cards per sheet with cut guides."""
from __future__ import annotations

import random

from pydantic import BaseModel, Field

from ..niches import NicheProfile
from ..render.raster import pdf_page_count
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register


class Card(BaseModel):
    text: str = Field(description="Card text, <= 120 characters")
    hint: str = Field(default="", description="Optional small handwritten-style line, <= 50 characters")
    category: str = ""


class CardContent(BaseModel):
    title: str
    subtitle: str = "Printable card deck"
    tagline: str
    cards: list[Card] = Field(min_length=9, max_length=72)


@register
class CardDeck(ProductType[CardContent]):
    key = "card_deck"
    label = "Card deck"
    description = "Printable affirmation / prompt / flashcard deck with cut guides, 9 cards per sheet."
    content_model = CardContent
    price_range = (3.0, 8.0)
    typical_formats = "PDF"

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> CardContent:
        cards = [Card(text=a, category="Affirm") for a in niche.affirmations]
        cards += [Card(text=p, category="Reflect") for p in niche.prompts]
        cards += [Card(text=f"Today: {h.lower()}.", category="Try") for h in niche.habits]
        rng.shuffle(cards)
        n = max(18, (len(cards) // 9) * 9)
        cards = (cards * 2)[:n]
        return CardContent(title=f"{niche.name} Card Deck", tagline=niche.tagline[:70], cards=cards)

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return (
            "Write a deck of exactly 36 cards for this niche, mixing three categories: 'Affirm' (short affirmations), "
            "'Reflect' (journal prompts) and 'Try' (tiny actions). Each card text <= 120 characters, specific to this "
            "audience, no duplicates. Optional hint line <= 50 characters."
        )

    def build(self, ctx: BuildContext, content: CardContent) -> BuildResult:
        slug = self.slug(content.title)
        files, renderer, pages = [], "", 0
        for size in ctx.sizes:
            page = ctx.page(size)
            out = ctx.out_dir / f"{slug}-{size}.pdf"
            renderer = self.pdf_from_template(ctx, "cards.html.j2", page, out, extra_css=_CARD_CSS, margin=0, content=content)
            pages = pdf_page_count(out)
            files.append(ProductFile(out, "pdf", f"{page.label} - printable", True, preview_pages=[0, 1, 2]))
        features = [f"{len(content.cards)} cards (poker size 2.5 x 3.5 in)", "Cut guides on every sheet",
                    "Affirmation, reflection and action cards", f"Made for {ctx.niche.audience}",
                    "Print on cardstock for best results"]
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer)


_CARD_CSS = """
.cardsheet { display:grid; grid-template-columns:repeat(3, 2.5in); grid-template-rows:repeat(3, 3.5in); justify-content:center; align-content:center; flex:1; }
.deckcard { width:2.5in; height:3.5in; border:1px dashed var(--muted); position:relative; padding:1.1em 1em; display:flex; flex-direction:column; align-items:center; text-align:center; overflow:hidden; font-size:10pt; }
.deckcard.a { background:var(--soft); }
.deckcard.b { background:var(--paper); }
.deckcard.c { background:var(--accent); color:var(--accent-ink); }
.deckcard.c .h, .deckcard.c .label, .deckcard.c .dc-hint, .deckcard.c .dc-num { color:var(--accent-ink); }
.deckcard::before { content:''; position:absolute; left:.5em; right:.5em; top:.5em; bottom:.5em; border:1.2px solid var(--accent2); border-radius:calc(var(--radius) + 2px); opacity:.55; }
.dc-top { margin-top:.7em; }
.dc-text { flex:1; display:flex; align-items:center; justify-content:center; font-size:1.55em; line-height:1.2; padding:0 .3em; }
.dc-hint { font-size:1.2em; color:var(--accent); margin-bottom:.5em; }
.dc-num { font-size:.6em; color:var(--muted); margin-bottom:.4em; }
"""
