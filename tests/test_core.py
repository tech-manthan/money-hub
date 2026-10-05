import random

import pytest

from moneyhub.design import PALETTES, choose_style
from moneyhub.listing.kit import ListingCopy, sanitize, _builtin_copy
from moneyhub.llm import LLMRouter, extract_json
from moneyhub.llm.base import LLMError, LLMProvider
from moneyhub.niches import LIBRARY, generic_profile, resolve_niche
from moneyhub.products import all_product_types
from moneyhub.uniqueness import fingerprint_text, most_similar, similarity


@pytest.mark.parametrize("pal", PALETTES, ids=lambda p: p.key)
def test_palettes_are_accessible(pal):
    assert pal.issues() == []


def test_style_is_deterministic_per_seed_and_varies():
    assert choose_style(seed=5).describe() == choose_style(seed=5).describe()
    assert len({choose_style(seed=i).key for i in range(1, 40)}) > 8


@pytest.mark.parametrize("niche", [*LIBRARY.values(), generic_profile("knitting for beginners")], ids=lambda n: n.key)
@pytest.mark.parametrize("ptype", all_product_types().values(), ids=lambda t: t.key)
def test_builtin_content_valid_for_every_niche_and_product(niche, ptype):
    content = ptype.builtin_content(niche, random.Random(1), {})
    assert ptype.content_model.model_validate(content.model_dump())


def test_resolve_niche():
    assert resolve_niche("ADHD planner").key == "adhd"
    assert resolve_niche("Nurse").key == "nurse"
    assert resolve_niche("dog training").key == "pet_owner"
    assert resolve_niche("underwater basket weaving").key == "underwater_basket_weaving"


def test_extract_json_handles_fences_and_prose():
    assert extract_json('Sure!\n```json\n{"a": [1, 2]}\n```') == {"a": [1, 2]}
    assert extract_json('here you go {"a": "x}y"} thanks') == {"a": "x}y"}
    with pytest.raises(LLMError):
        extract_json("no json here")


class _Fake(LLMProvider):
    def __init__(self, name, reply=None, fail=False):
        super().__init__({"model": name})
        self.name, self.reply, self.fail, self.calls = name, reply, fail, 0

    def available(self):
        return True

    def complete(self, system, prompt, *, max_tokens=8000):
        self.calls += 1
        if self.fail:
            raise LLMError("boom")
        return self.reply


def _router(providers):
    r = LLMRouter()
    r._providers = {p.name: p for p in providers}
    r.cfg.data["llm"]["tasks"]["content"] = [p.name for p in providers] + ["builtin"]
    return r


def test_router_falls_through_failures_and_invalid_output():
    from pydantic import BaseModel

    class M(BaseModel):
        x: int

    bad, junk, good = _Fake("bad", fail=True), _Fake("junk", reply='{"x": "nope"}'), _Fake("good", reply='{"x": 3}')
    r = _router([bad, junk, good])
    out = r.complete_json("content", "s", "p", M)
    assert out == M(x=3) and r.last_used.startswith("good")
    assert bad.calls >= 1 and junk.calls == 2  # one retry on invalid output


def test_router_returns_none_when_everything_fails():
    from pydantic import BaseModel

    class M(BaseModel):
        x: int

    r = _router([_Fake("a", fail=True)])
    assert r.complete_json("content", "s", "p", M) is None and r.last_used == "builtin"
    assert r.complete_json("content", "s", "p", M, providers=["builtin"]) is None


def test_listing_sanitize_enforces_marketplace_limits():
    ptype = all_product_types()["weekly_planner"]
    niche = resolve_niche("adhd")
    from moneyhub.products.base import BuildResult
    build = BuildResult("T", "S", [], ["a", "b", "c"])
    copy = _builtin_copy(niche, ptype, build, random.Random(1))
    copy = copy.model_copy(update={"title": "x " * 200, "tags": ["a very long tag that is over twenty chars", "ok tag", "OK TAG"] + [f"tag {i}" for i in range(30)]})
    s = sanitize(copy)
    assert len(s.title) <= 140 and len(s.tags) <= 13
    assert all(len(t) <= 20 for t in s.tags) and len(set(s.tags)) == len(s.tags)
    assert all(len(t) <= 100 for t in s.pin_titles) and len(s.pin_description) <= 500


def test_uniqueness_detects_near_duplicates():
    a = fingerprint_text("the quick brown fox jumps over the lazy dog again and again today")
    b = fingerprint_text("the quick brown fox jumps over the lazy dog again and again tomorrow")
    c = fingerprint_text("completely different words about budgeting and savings goals for families")
    assert similarity(a, b) > 0.5 > similarity(a, c)
    assert most_similar(b, [(1, "A", a), (2, "C", c)])[1] == 1
