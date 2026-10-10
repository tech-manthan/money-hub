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
    "icon_pack": "Planner icon stickers from open-source line icons (MIT/ISC): printable sheets, PNG and SVG, licence notice included.",
    "character_clipart": "Cute colored character clipart (animals, vehicles, seasonal, fantasy): transparent PNG, SVG and a commercial licence.",
    "learning_workbook": "Preschool learning workbook: colors, opposites, days, seasons, feelings, telling time, counting, shadows, patterns, word tracing (PDF).",
    "activity_book": "Kids activity book: mazes with answers, dot-to-dot, letter and number tracing, odd-one-out puzzles (PDF).",
    "oracle_deck": "Illustrated tarot-style or oracle card deck with gentle messages, cut guides, a how-to page and card backs (PDF).",
    "sticker_sheets": "Colourful stickers with a die-cut border: printable sheets plus transparent PNGs for digital planners.",
    "kids_coloring": "Children's coloring pages: friendly animals, vehicles and treats plus shape, counting and tracing pages (PDF). New figures every time.",
    "coloring_pages": "Printable mandala and pattern coloring pages as clean line art (PDF).",
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
            "product_label": t.label if t else ptype,
        })
    return cards
