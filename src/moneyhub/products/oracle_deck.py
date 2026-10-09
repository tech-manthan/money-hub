"""Tarot-style and oracle card decks: illustrated cards (a symbol in an arched, starry window), a name, a keyword and a short gentle message, printed at
card size with cut guides, plus a how-to-use page and matching card backs. Art by oracle_art.py; messages are for reflection, never predictions."""
from __future__ import annotations

import random

from pydantic import BaseModel, Field, field_validator

from .. import oracle_art
from ..niches import NicheProfile
from ..render.raster import pdf_page_count
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register

ROMAN = ["0", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX", "XXI"]

TAROT = [
    ("The Fool", "Beginnings", "A fresh start waits. Step forward with curiosity; you do not need the whole map.", "path"),
    ("The Magician", "Skill", "You already hold the tools you need. Focus your attention and begin.", "infinity"),
    ("The High Priestess", "Intuition", "Be still and listen. The quiet answer is often the true one.", "eye"),
    ("The Empress", "Nurture", "Care for what you are growing, yourself included. Abundance starts with kindness.", "lotus"),
    ("The Emperor", "Structure", "Steady routines and clear boundaries give your plans a strong base.", "mountain"),
    ("The Hierophant", "Learning", "Learn from those who came before you, then make the lesson your own.", "key"),
    ("The Lovers", "Choice", "A meaningful choice asks for honesty. Pick what matches your values.", "lovers"),
    ("The Chariot", "Drive", "Hold your direction and keep going. Focus is what steers you.", "compass"),
    ("Strength", "Courage", "Gentle patience is real strength. Meet the moment with a calm heart.", "heart"),
    ("The Hermit", "Reflection", "Step back and carry your own light. Time alone brings clarity.", "lantern"),
    ("Wheel of Fortune", "Change", "Seasons turn. What is low now will rise; stay ready for the next turn.", "wheel"),
    ("Justice", "Balance", "Weigh things fairly and act with integrity. Honest choices rest easy.", "scales"),
    ("The Hanged Man", "Perspective", "Pause and look from a new angle. Letting go of hurry shows another way.", "hourglass"),
    ("Death", "Renewal", "An ending clears space. Let what is finished go and a new chapter can grow.", "sprout"),
    ("Temperance", "Harmony", "Blend effort and rest in small, steady amounts until you find your pace.", "wave"),
    ("The Devil", "Habits", "Notice what keeps you in place. Seeing a habit clearly is the first step to loosening it.", "door"),
    ("The Tower", "Upheaval", "A sudden shake-up clears weak foundations. Rebuild with what you have learned.", "tower"),
    ("The Star", "Hope", "Hope returns, quietly and steadily. Trust the small light you can see.", "star"),
    ("The Moon", "Mystery", "Not everything is clear yet. Move gently and let the picture come into focus.", "moon"),
    ("The Sun", "Joy", "Warmth and clarity. Celebrate what is going well and share the light.", "sun"),
    ("Judgement", "Awakening", "A call to rise to your best self. Forgive the past and answer it.", "rainbow"),
    ("The World", "Completion", "A cycle is complete. Honour how far you have come before you begin again.", "world"),
]

ORACLE = [
    ("Open Door", "Opportunity", "A new possibility is closer than it looks. Say yes to one small invitation.", "door"),
    ("Fresh Path", "Direction", "Take the next small step; the path appears as you walk.", "path"),
    ("Inner Light", "Guidance", "Trust the steady light inside you. It knows the way home.", "lantern"),
    ("Gentle Strength", "Courage", "You can be soft and strong at once. Move at a pace that keeps you whole.", "heart"),
    ("Deep Roots", "Grounding", "Return to what steadies you. Strong roots let you grow tall.", "tree"),
    ("Rising Sun", "Hope", "Today is a clean page. Begin with something you enjoy.", "sun"),
    ("Quiet Moon", "Rest", "Rest is productive. Let yourself slow down and refill.", "moon"),
    ("Guiding Star", "Purpose", "Remember what you are aiming for and let it light your next choice.", "star"),
    ("Steady Flame", "Passion", "Tend what excites you. A small fire kept warm lasts a long time.", "flame"),
    ("Soft Landing", "Ease", "You are allowed to make this easier. Choose the gentle option.", "feather"),
    ("Clear Sight", "Clarity", "Look closely. What you notice today can simplify tomorrow.", "eye"),
    ("New Sprout", "Growth", "Something small is growing. Water it with patience.", "sprout"),
    ("Fair Balance", "Balance", "Give your energy where it counts and take it back where it does not.", "scales"),
    ("Right Timing", "Patience", "Not too early, not too late. Ready things arrive in their own time.", "hourglass"),
    ("Flowing Water", "Flow", "Stop forcing it. Move around the obstacle like a stream.", "wave"),
    ("Whole Circle", "Wholeness", "You are enough as you are, and still growing.", "world"),
    ("True North", "Alignment", "Check in with your values. Let them be your compass.", "compass"),
    ("Golden Key", "Solution", "The answer you want may already be in your hands. Try the simple fix.", "key"),
    ("Open Bloom", "Self-expression", "Let yourself be seen. Your colours belong here.", "lotus"),
    ("Changing Wings", "Transformation", "Change can be beautiful. Trust the process of becoming.", "butterfly"),
    ("High View", "Perspective", "Climb a little higher and the problem looks smaller.", "mountain"),
    ("After the Rain", "Renewal", "Brighter days follow hard ones. Look for the colours.", "rainbow"),
    ("Turning Wheel", "Cycles", "Everything moves in cycles. This season will pass and another will come.", "wheel"),
    ("Shared Heart", "Connection", "Reach out. A kind word shared makes two people lighter.", "lovers"),
    ("Full Cup", "Gratitude", "Notice what is already full in your life and give thanks for it.", "chalice"),
    ("Own Crown", "Confidence", "Stand tall in your own worth. You do not need anyone's permission.", "crown"),
    ("Strong Walls", "Boundaries", "A clear boundary is a form of care. It is okay to say no.", "tower"),
    ("Gentle Pause", "Mindfulness", "Take three slow breaths before you decide anything.", "feather"),
    ("Brave Step", "Bravery", "Do the thing that scares you a little, and be kind to yourself while you do.", "path"),
    ("Warm Welcome", "Belonging", "You are invited. Find your people and let them find you.", "door"),
    ("Bright Idea", "Inspiration", "Write the idea down before it floats away. It deserves a chance.", "star"),
    ("Soft Heart", "Compassion", "Be as kind to yourself as you would be to a good friend.", "heart"),
    ("Wide Horizon", "Possibility", "There is more room than you think. Dream a little bigger.", "sun"),
    ("Calm Waters", "Peace", "This too can settle. Let the ripples slow and the surface clear.", "wave"),
    ("Sweet Surprise", "Joy", "Make room for something unexpected and delightful today.", "butterfly"),
    ("Home Within", "Safety", "You carry a safe place inside you. Come back to it whenever you need.", "lantern"),
]

SIZES = {"tall": (3, 2, 2.5, 4.5, "Tarot-size cards, 2.5 x 4.5 in"), "poker": (3, 3, 2.5, 3.5, "Poker-size cards, 2.5 x 3.5 in")}   # cols, rows, w in, h in, label


class OracleCard(BaseModel):
    name: str = Field(description="Card name, 1-3 words")
    keyword: str = Field(description="One-word theme")
    message: str = Field(description="A gentle message of one or two sentences, <= 110 characters, never a prediction")
    symbol: str = Field(description="One of: " + ", ".join(oracle_art.SYMBOLS))

    @field_validator("symbol")
    @classmethod
    def _known(cls, v: str) -> str:
        return v if v in oracle_art.SYMBOLS else "star"


class OracleContent(BaseModel):
    title: str
    subtitle: str = "Printable oracle cards"
    tagline: str = Field(description="One short, warm line (<= 70 chars)")
    deck: str = "oracle"
    cards: list[OracleCard] = Field(min_length=12, max_length=44)


def _deck(options: dict) -> str:
    d = str(options.get("deck") or "oracle")
    if d not in ("tarot", "oracle"):
        raise ValueError("deck must be 'tarot' (22 archetype cards) or 'oracle' (gentle message cards)")
    return d


def _size(options: dict) -> str:
    s = str(options.get("card_size") or "tall")
    if s not in SIZES:
        raise ValueError(f"card size must be one of: {', '.join(SIZES)}")
    return s


@register
class OracleDeck(ProductType[OracleContent]):
    key = "oracle_deck"
    label = "Oracle / tarot-style deck"
    description = ("Illustrated tarot-style (22 archetype cards) or oracle (gentle message cards) deck: arched-window art, name, keyword and message, cut guides, "
                   "a how-to-use page and matching card backs. For reflection and entertainment.")
    content_model = OracleContent
    default_sizes = ["letter", "a4"]
    supported_sizes = ["letter", "a4"]
    price_range = (4.0, 12.0)
    typical_formats = "PDF (Letter and A4, printable)"
    niche_in_copy = False
    copy_audience = "journaling and self-care lovers"
    title_suffix = " Card Deck"
    license_faq = ("Q: Are these cards predictions? A: No. The messages are for reflection, inspiration and entertainment only - not predictions, "
                   "and not medical, legal or financial advice. Q: Can I resell or share the files? A: No - personal use only.")
    how_steps = ("Purchase and download your files instantly.", "Print the card pages on cardstock at Actual size, print the back page on the reverse (or on a second sheet), then cut along the dashed guides.",
                 "Shuffle, ask a gentle question and pull a card. The guide page shows one-card and three-card spreads.")

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> OracleContent:
        deck = _deck(options)
        src = TAROT if deck == "tarot" else ORACLE[:max(12, min(int(options.get("cards", 36)), len(ORACLE)))]
        cards = [OracleCard(name=n, keyword=k, message=m, symbol=s) for n, k, m, s in src]
        title = "Tarot-Style Archetype Card Deck" if deck == "tarot" else "Oracle Card Deck"
        return OracleContent(title=title, subtitle=f"{len(cards)} printable {'archetype' if deck == 'tarot' else 'oracle'} cards", deck=deck,
                             tagline="Gentle cards for reflection and calm.", cards=cards)

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        deck = _deck(options)
        n = 22 if deck == "tarot" else max(12, min(int(options.get("cards", 36)), 44))
        if deck == "tarot":
            return ("Write the cards of a TAROT-STYLE archetype deck, exactly 22 cards in the order of the traditional major arcana (The Fool ... The World), using the "
                    "traditional names. For each: a one-word keyword, an ORIGINAL gentle message (<= 110 characters, reflective, never a prediction, no health, money or legal "
                    "claims) and a symbol from the allowed list. Title must end with 'Card Deck'. Do not mention any niche or profession.")
        return (f"Write {n} cards for an ORACLE deck of gentle, encouraging messages. Each card: a unique 2-word name, a one-word keyword, a message (<= 110 characters, "
                "reflective and kind, never a prediction, no health, money or legal claims) and a symbol from the allowed list. Title must end with 'Card Deck'. "
                "Do not mention any niche or profession.")

    def build(self, ctx: BuildContext, content: OracleContent) -> BuildResult:
        deck, size = _deck(ctx.options), _size(ctx.options)
        content = content.model_copy(update={"title": self.unique_title(ctx, content.title), "deck": deck})
        slug = self.slug(content.title)
        cols, rows, cw, ch, size_label = SIZES[size]
        pal = ctx.style.palette
        arts = [oracle_art.card_art(c.symbol, pal, ctx.seed * 31 + i) for i, c in enumerate(content.cards)]
        back = oracle_art.card_back(pal, ctx.seed, ch / cw)
        numerals = [ROMAN[i] if deck == "tarot" and i < len(ROMAN) else "" for i in range(len(content.cards))]
        tctx = {"content": content, "arts": arts, "back": back, "numerals": numerals, "cols": cols, "rows": rows, "cw": cw, "ch": ch, "per": cols * rows,
                "pt": 7.4 if size == "tall" else 6.2, "deck": deck}
        jobs = [(ctx.page(s), ctx.out_dir / f"{slug}-{s}.pdf", tctx) for s in ctx.sizes]
        renderer = self.render_jobs(ctx, "oracle.html.j2", jobs, margin=0)
        files, pages = [], 0
        for page, out, _ in jobs:
            pages = pdf_page_count(out)
            files.append(ProductFile(out, "pdf", f"{page.label} - printable", True, preview_pages=[0, 1, 2]))
        n = len(content.cards)
        features = [f"{n} illustrated {'tarot-style archetype' if deck == 'tarot' else 'oracle'} cards ({size_label})", "Cut guides on every sheet and matching card backs",
                    "How-to-use page with one-card and three-card spreads", "Gentle messages for reflection, never predictions", "Print on cardstock for best results",
                    "Instant download - no physical item shipped"]
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer, meta={"deck": deck, "card_size": size, "cards": n})
