"""Niche x product ideas. LLM-generated hypotheses from training knowledge (not live search data);
validate them with Etsy autocomplete, Pinterest Trends and real listings."""
from __future__ import annotations

import json
import random

from pydantic import BaseModel, Field

from .config import get_config
from .llm import get_router
from .niches import LIBRARY
from .products import all_product_types


class Idea(BaseModel):
    niche: str = Field(description="Niche to pass to the generator, 2-5 words")
    product_type: str = Field(description="One of the allowed product type keys")
    angle: str = Field(description="What makes this specific and different, one sentence")
    why: str = Field(description="Why buyers want it, one sentence")
    keywords: list[str] = Field(min_length=3, max_length=8, description="Buyer search phrases to validate")
    competition: str = Field(description="low, medium or high (best guess)")


class IdeaList(BaseModel):
    ideas: list[Idea] = Field(min_length=5, max_length=40)


def _path():
    return get_config().output_dir / "ideas.json"


def load_ideas() -> dict:
    p = _path()
    return json.loads(p.read_text()) if p.exists() else {"source": None, "ideas": []}


def suggest_ideas(n: int = 15, focus: str | None = None, providers: list[str] | None = None) -> dict:
    types = list(all_product_types())
    router = get_router()
    prompt = (
        f"Suggest {n} specific niche + product ideas for selling digital products on Etsy, Gumroad and Pinterest. "
        f"Allowed product types: {', '.join(types)}. "
        + (f"Focus area: {focus}. " if focus else "Cover a wide range of audiences. ")
        + "Prefer narrow, underserved audiences with real, recurring needs (e.g. a specific profession, life stage, condition-adjacent "
        "routine, hobby or exam) over broad topics. Do not make income claims. Give buyer search phrases for each."
    )
    system = "You are an Etsy/Pinterest market researcher. You reason from general market knowledge and say what to verify."
    out = router.complete_json("research", system, prompt, IdeaList, providers=providers)
    if out is not None:
        ideas = [i for i in out.ideas if i.product_type in types]
        source = router.last_used or "llm"
    else:
        rng = random.Random()
        ideas, source = [], "builtin"
        combos = [(k, t) for k in LIBRARY for t in types]
        rng.shuffle(combos)
        for k, t in combos[:n]:
            nz = LIBRARY[k]
            ideas.append(Idea(niche=nz.name, product_type=t, angle=f"{t.replace('_', ' ')} written for {nz.audience}",
                              why=f"Addresses: {', '.join(nz.pain_points[:2])}", keywords=(nz.seo_keywords + [nz.name.lower()])[:5],
                              competition="medium"))
    data = {"source": source, "focus": focus, "ideas": [i.model_dump() for i in ideas]}
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))
    return data
