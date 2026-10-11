"""Plain-language data for the guided start page: idea cards, product descriptions, look presets, progress steps."""
from __future__ import annotations

from ..niches import LIBRARY

# What to make first for each built-in niche, with a card icon.
BEST_FIRST = {
    "adhd": ("daily_planner", "🧠"), "teacher": ("worksheet_pack", "🍎"), "personal_finance": ("budget_tracker", "💰"),
    "wedding": ("checklist_pack", "💍"), "student": ("weekly_planner", "🎓"), "nurse": ("weekly_planner", "🩺"),
    "small_business": ("budget_tracker", "🛍️"), "fitness": ("habit_tracker", "💪"), "mindfulness": ("guided_journal", "🧘"),
    "new_mom": ("checklist_pack", "🍼"), "pet_owner": ("checklist_pack", "🐾"), "gardening": ("weekly_planner", "🌱"),
    "faith": ("guided_journal", "🙏"), "home": ("checklist_pack", "🏠"), "meal_planning": ("weekly_planner", "🥗"),
}

# Which products suit which audience. Not every product belongs to every audience (a wedding couple has no use for classroom charts), so the
# wizard shows these first and keeps the rest behind "Show all". A typed audience gets the audience-specific types (see default_fits).
_SELF = ["weekly_planner", "daily_planner", "habit_tracker", "guided_journal", "checklist_pack", "card_deck", "ebook_guide", "wall_art"]
FIT = {
    "adhd": _SELF + ["worksheet_pack", "visual_schedule", "sticker_sheets", "icon_pack"],
    "teacher": ["worksheet_pack", "classroom_pack", "visual_schedule", "montessori_cards", "learning_workbook", "activity_book", "coloring_pages", "kids_coloring",
                "sticker_sheets", "character_clipart", "clipart_pack", "digital_paper", "cut_files", "presentation_template", "checklist_pack", "weekly_planner", "daily_planner", "wall_art", "card_deck"],
    "personal_finance": ["budget_tracker", "ebook_guide", "checklist_pack", "worksheet_pack", "habit_tracker", "weekly_planner", "guided_journal", "wall_art", "card_deck"],
    "wedding": ["checklist_pack", "budget_tracker", "guided_journal", "ebook_guide", "card_deck", "wall_art", "weekly_planner", "digital_paper", "clipart_pack", "cut_files"],
    "student": ["weekly_planner", "daily_planner", "habit_tracker", "checklist_pack", "worksheet_pack", "guided_journal", "ebook_guide", "wall_art", "card_deck",
                "sticker_sheets", "icon_pack", "presentation_template"],
    "nurse": _SELF + ["sticker_sheets", "icon_pack", "worksheet_pack"],
    "small_business": ["budget_tracker", "weekly_planner", "daily_planner", "checklist_pack", "ebook_guide", "habit_tracker", "wall_art", "worksheet_pack", "card_deck",
                       "presentation_template", "clipart_pack", "digital_paper", "icon_pack", "cut_files", "sticker_sheets"],
    "fitness": _SELF + ["sticker_sheets", "icon_pack"],
    "mindfulness": ["guided_journal", "card_deck", "oracle_deck", "coloring_pages", "habit_tracker", "ebook_guide", "wall_art", "weekly_planner", "daily_planner", "checklist_pack", "digital_paper"],
    "new_mom": ["checklist_pack", "weekly_planner", "daily_planner", "habit_tracker", "guided_journal", "ebook_guide", "wall_art", "card_deck", "budget_tracker",
                "kids_coloring", "learning_workbook", "activity_book", "montessori_cards", "visual_schedule", "sticker_sheets", "character_clipart"],
    "pet_owner": ["checklist_pack", "weekly_planner", "habit_tracker", "ebook_guide", "wall_art", "guided_journal", "sticker_sheets", "icon_pack", "clipart_pack", "character_clipart", "cut_files"],
    "gardening": ["weekly_planner", "checklist_pack", "habit_tracker", "ebook_guide", "guided_journal", "wall_art", "coloring_pages", "clipart_pack", "worksheet_pack", "icon_pack"],
    "faith": ["guided_journal", "card_deck", "oracle_deck", "habit_tracker", "weekly_planner", "daily_planner", "ebook_guide", "wall_art", "coloring_pages", "checklist_pack", "kids_coloring", "digital_paper"],
    "home": ["checklist_pack", "weekly_planner", "daily_planner", "budget_tracker", "habit_tracker", "ebook_guide", "wall_art", "visual_schedule", "icon_pack", "sticker_sheets", "cut_files"],
    "meal_planning": ["weekly_planner", "checklist_pack", "budget_tracker", "ebook_guide", "habit_tracker", "daily_planner", "worksheet_pack", "wall_art", "icon_pack", "sticker_sheets"],
}


def default_fits(types: dict) -> list[str]:
    """Products shown first for a typed audience: the ones whose content is written for an audience."""
    return [k for k, t in types.items() if t.niche_in_copy]


# product key -> (what you get, in one plain sentence)
PRODUCT_PLAIN = {
    "weekly_planner": "A printable year of weekly planning pages (PDF).",
    "daily_planner": "One page per day with a schedule, priorities and a to-do list (PDF).",
    "habit_tracker": "A spreadsheet with tick-boxes and charts, plus printable monthly trackers.",
    "budget_tracker": "A spreadsheet that tracks spending, savings goals and debt payoff.",
    "guided_journal": "30 days of writing prompts with mood and gratitude boxes (PDF).",
    "checklist_pack": "A bundle of ready-to-print checklists for this audience (PDF).",
    "worksheet_pack": "Printable worksheets with directions and an answer key (PDF).",
    "card_deck": "A printable deck of cards (affirmations, prompts or flashcards) with cut guides.",
    "ebook_guide": "A short beginner guide with chapters and action steps. Review the text before selling.",
    "wall_art": "A set of printable quote posters in several print sizes (JPG).",
    "clipart_pack": "Abstract boho clipart: transparent PNGs, SVG vectors and a commercial licence.",
    "cut_files": "Clean cut-file shapes for Cricut and Silhouette: SVG, DXF, EPS and PNG, with a commercial licence.",
    "classroom_pack": "Name tags, desk plates, reward, behaviour and chore charts, a calendar, birthday chart and star-of-the-week posters; names printed or written in (PDF).",
    "visual_schedule": "Daily routine boards, first-then, now/next/later, choice and feelings boards with picture cards and hook-and-loop dot guides (PDF).",
    "montessori_cards": "Three-part Montessori matching cards (control, picture, name), English or bilingual Spanish / French / German (PDF).",
    "icon_pack": "Planner icon stickers from open-source line icons (MIT/ISC): printable sheets, PNG and SVG, licence notice included.",
    "character_clipart": "Cute colored character clipart (animals, vehicles, seasonal, fantasy): transparent PNG, SVG and a commercial licence.",
    "learning_workbook": "Preschool learning workbook: colors, opposites, days, seasons, feelings, telling time, counting, shadows, patterns, word tracing (PDF).",
    "activity_book": "Kids activity book: mazes with answers, dot-to-dot, letter and number tracing, odd-one-out puzzles (PDF).",
    "oracle_deck": "Illustrated tarot-style or oracle card deck with gentle messages, cut guides, a how-to page and card backs (PDF).",
    "sticker_sheets": "Colourful stickers with a die-cut border: printable sheets plus transparent PNGs for digital planners.",
    "kids_coloring": "Children's coloring pages: friendly animals, vehicles and treats plus shape, counting and tracing pages (PDF). New figures every time.",
    "coloring_pages": "Printable mandala and pattern coloring pages as clean line art (PDF).",
    "presentation_template": "Editable 12-slide widescreen deck (.pptx) with a PDF preview and an editing guide. Needs the deckcraft tool installed.",
    "digital_paper": "Seamless 12 x 12 in patterns as JPG papers, with a commercial licence.",
}

FONT_PLAIN = {
    "editorial": "Elegant serif headings, clean body text",
    "modern": "Soft modern headings, very readable body",
    "friendly": "Rounded and friendly throughout",
    "classic": "Traditional book-style headings",
    "clean": "Bold geometric headings, crisp body",
    "warm": "Soft serif headings, cosy feel",
}

HEADER_PLAIN = {"band": "Coloured band across the top", "rule": "Simple line under the title", "box": "Title in a box"}
GRID_PLAIN = {"solid": "Solid lines", "dotted": "Dotted lines", "dashed": "Dashed lines"}
RADIUS_PLAIN = {0: "Sharp corners", 6: "Slightly rounded", 12: "Rounded", 18: "Very rounded"}

# Progress shown to the user, matched against the pipeline's log lines.
STEPS = [
    ("Researching", "Learning about your audience"),
    ("Writing content", "Writing the product content"),
    ("Checking for similar", "Making sure it is original"),
    ("Writing listing copy", "Writing the shop listing text"),
    ("Creating listing images", "Making listing photos and Pinterest pins"),
    ("Writing marketplace guides", "Writing upload instructions"),
    ("Running quality checks", "Checking quality"),
    ("Done", "Finished"),
]


def idea_cards(types: dict) -> list[dict]:
    cards = []
    for key, nz in LIBRARY.items():
        ptype, icon = BEST_FIRST.get(key, ("weekly_planner", "✨"))
        t = types.get(ptype)
        cards.append({
            "niche": nz.name, "icon": icon, "audience": nz.audience, "tagline": nz.tagline,
            "problem": nz.pain_points[0] if nz.pain_points else "", "product_type": ptype,
            "theme": __import__("moneyhub.decor", fromlist=["theme_for"]).theme_for(key, nz.audience),
            "fits": ",".join(k for k in FIT.get(key, []) if k in types) or ",".join(default_fits(types)),
            "product_label": t.label if t else ptype,
        })
    return cards
