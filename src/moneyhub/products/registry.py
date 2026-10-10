from __future__ import annotations

from .base import ProductType

PRODUCT_TYPES: dict[str, ProductType] = {}


def register(cls: type[ProductType]) -> type[ProductType]:
    PRODUCT_TYPES[cls.key] = cls()
    return cls


def get_product_type(key: str) -> ProductType:
    _load_all()
    if key not in PRODUCT_TYPES:
        raise KeyError(f"unknown product type '{key}'. Available: {', '.join(sorted(PRODUCT_TYPES))}")
    return PRODUCT_TYPES[key]


def all_product_types() -> dict[str, ProductType]:
    _load_all()
    return PRODUCT_TYPES


def _load_all() -> None:
    from . import (budget_tracker, card_deck, checklist_pack, daily_planner, ebook_guide, habit_tracker, journal,  # noqa: F401
                   wall_art, weekly_planner, worksheet_pack, clipart_pack, digital_paper, coloring_pages, cut_files, kids_coloring, sticker_sheets, oracle_deck, activity_book, learning_workbook, character_clipart, icon_pack, montessori_cards, classroom_pack, visual_schedule)
