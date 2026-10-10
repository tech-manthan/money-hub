"""Whole bundles and variation batches from the command line.

`build_bundle("halloween")` makes a coloring book, activity book, sticker sheets and character clipart that share one look and theme, then packs
them into one zip with a combined listing kit. `build_bundle("nurse")` makes a starter kit of planners and trackers. `make_many` makes N distinct
variations of one product type (a different look and/or theme each) and returns a summary row per product."""
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import kidsart
from .design import FONT_PAIRS, HEADERS, PALETTES
from .pipeline import Request, Result, generate
from .products import all_product_types, get_product_type

THEME_TYPES = {"kids_coloring", "activity_book", "sticker_sheets", "character_clipart", "montessori_cards", "classroom_pack", "visual_schedule"}
THEME_BUNDLE = ["kids_coloring", "activity_book", "sticker_sheets", "character_clipart"]
NICHE_BUNDLE = ["weekly_planner", "habit_tracker", "budget_tracker", "checklist_pack"]
MAX_MANY = 30
VARY = ("look", "theme", "seed")


SHORT = {"kids_coloring": "Coloring Pages", "activity_book": "Activity Book", "sticker_sheets": "Stickers", "character_clipart": "Clipart",
         "weekly_planner": "Weekly Planner", "daily_planner": "Daily Planner", "habit_tracker": "Habit Tracker", "budget_tracker": "Budget Tracker",
         "checklist_pack": "Checklists", "worksheet_pack": "Worksheets", "guided_journal": "Journal", "card_deck": "Cards", "coloring_pages": "Coloring Pages",
         "learning_workbook": "Workbook", "montessori_cards": "Montessori Cards", "classroom_pack": "Classroom Printables", "visual_schedule": "Visual Schedule",
         "digital_paper": "Digital Paper", "clipart_pack": "Clipart", "wall_art": "Wall Art", "oracle_deck": "Oracle Deck", "cut_files": "Cut Files"}


@dataclass
class BundleResult:
    folder: Path
    name: str
    products: list[Result]


@dataclass
class Row:
    product_id: int
    title: str
    qa: str
    uniqueness: str
    folder: Path


def _theme_title(theme: str) -> str:
    return kidsart.THEMES[theme][0]


def check_types(types: list[str]) -> list[str]:
    known = all_product_types()
    bad = [t for t in types if t not in known]
    if bad:
        raise ValueError(f"unknown product type(s): {', '.join(bad)}. Choose from: {', '.join(known)}")
    return types


def shared_look(seed: int, palette: str | None, fonts: str | None) -> tuple[str, str, dict]:
    """One palette, font pair and page look chosen once so every product in a bundle matches."""
    rng = random.Random(seed)
    return (palette or rng.choice([p.key for p in PALETTES]), fonts or rng.choice([f.key for f in FONT_PAIRS]),
            {"header": rng.choice(HEADERS)})


def build_bundle(subject: str, types: list[str] | None = None, name: str | None = None, discount: float = 0.30, seed: int | None = None,
                 palette: str | None = None, fonts: str | None = None, providers: list[str] | None = None, sizes: list[str] | None = None,
                 with_images: bool = True, with_video: bool = False, progress: Callable[[str], None] | None = None) -> BundleResult:
    from .growth import make_bundle
    say = progress or (lambda m: None)
    key = subject.strip().lower()
    theme_mode = key in kidsart.THEMES and key != "mixed"
    types = check_types(types or (THEME_BUNDLE if theme_mode else NICHE_BUNDLE))
    if len(types) < 2:
        raise ValueError("a bundle needs at least two product types (--types a,b,c)")
    seed = seed if seed is not None else random.SystemRandom().randrange(1, 10**6)
    pal, fnt, look = shared_look(seed, palette, fonts)
    say(f"Shared look: {pal} colours, {fnt} fonts")
    results: list[Result] = []
    for i, t in enumerate(types):
        opts: dict = dict(look)
        if theme_mode:
            opts["no_research"] = True
            if t in THEME_TYPES:
                opts["theme"] = key
        elif t in THEME_TYPES:
            opts["no_research"] = True
        say(f"[{i + 1}/{len(types)}] {get_product_type(t).label}")
        res = generate(Request(_theme_title(key) if theme_mode else subject, t, sizes=sizes, seed=seed + i * 11, palette=pal, fonts=fnt,
                               providers=providers, options=opts, with_images=with_images, with_video=with_video))
        results.append(res)
    label = name or (f"{_theme_title(key)} Bundle" if theme_mode else f"{subject.strip().title()} Starter Kit")
    words = " + ".join(SHORT.get(t, get_product_type(t).label) for t in types)
    tags = [f"{key} bundle", f"{key} printables", f"{key} kids"] if theme_mode else [f"{subject.strip().lower()} bundle", f"{subject.strip().lower()} printables"]
    out = make_bundle([r.product_id for r in results], label, discount, title=f"{label} | {words} | Printable Instant Download",
                      extra_tags=[t for t in tags if len(t) <= 20])
    return BundleResult(out, label, results)


def make_many(subject: str, product_type: str, count: int = 10, vary: list[str] | None = None, seed: int | None = None,
              providers: list[str] | None = None, sizes: list[str] | None = None, with_images: bool = True, with_video: bool = False,
              options: dict | None = None, progress: Callable[[str], None] | None = None) -> list[Row]:
    """`count` variations of one product type. vary: look (palette + fonts cycle), theme (kids themes cycle, for types that take a theme)
    and seed (always on, so layouts and art differ)."""
    say = progress or (lambda m: None)
    if not 1 <= count <= MAX_MANY:
        raise ValueError(f"--count must be between 1 and {MAX_MANY}")
    vary = vary or ["look"]
    bad = [v for v in vary if v not in VARY]
    if bad:
        raise ValueError(f"unknown --vary value(s): {', '.join(bad)}. Choose from: {', '.join(VARY)}")
    check_types([product_type])
    base = seed if seed is not None else random.SystemRandom().randrange(1, 10**6)
    palettes = [p.key for p in PALETTES]
    fonts = [f.key for f in FONT_PAIRS]
    themes = [t for t in kidsart.THEMES if t != "mixed"]
    start = random.Random(base).randrange(len(palettes))
    rows: list[Row] = []
    for i in range(count):
        opts = dict(options or {})
        if "theme" in vary and product_type in THEME_TYPES:
            opts["theme"] = themes[(i + base) % len(themes)]
            opts["no_research"] = True
        pal = palettes[(start + i) % len(palettes)] if "look" in vary else None
        fnt = fonts[(start + i * 3) % len(fonts)] if "look" in vary else None
        say(f"[{i + 1}/{count}] variation" + (f" ({opts['theme']})" if "theme" in opts else ""))
        r = generate(Request(subject, product_type, sizes=sizes, seed=base + i * 101, palette=pal, fonts=fnt, providers=providers,
                             options=opts, with_images=with_images, with_video=with_video))
        close = f"{r.similar[0]:.0%} like #{r.similar[1]}" if r.similar[1] else "new"
        rows.append(Row(r.product_id, r.title, r.qa_status, close, r.folder))
    return rows
