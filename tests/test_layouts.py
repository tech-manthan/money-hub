import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from moneyhub.cli import app as cli
from moneyhub.pipeline import Request, generate
from moneyhub.products import all_product_types
from moneyhub.products.base import ProductType
from moneyhub.render.preview import layout_preview_png
from moneyhub.web.app import app

WITH_LAYOUTS = {k: t for k, t in all_product_types().items() if t.layouts}


def test_planners_offer_several_layouts_and_the_first_is_the_default():
    assert {"weekly_planner", "daily_planner"} <= set(WITH_LAYOUTS)
    for t in WITH_LAYOUTS.values():
        assert len(t.layouts) >= 3 and (t.layout_marker or type(t).layout_preview_image is not ProductType.layout_preview_image)


@pytest.mark.parametrize("key", sorted(WITH_LAYOUTS))
def test_every_layout_really_looks_different(key):
    pics = {name: layout_preview_png(key, name, palette="sage") for name in WITH_LAYOUTS[key].layouts if name != "mixed"}   # mixed shows one of the others
    assert len(set(pics.values())) == len(pics)


def test_a_chosen_layout_is_used_and_an_unknown_one_is_refused():
    r = generate(Request("nurse", "weekly_planner", providers=["builtin"], seed=3, sizes=["a5"], with_images=False, with_video=False,
                         options={"page_layout": "minimal", "weeks": 4, "no_research": True}))
    assert r.qa_status in ("pass", "warn")
    with pytest.raises(ValueError, match="no page layout"):
        generate(Request("nurse", "weekly_planner", providers=["builtin"], with_images=False, with_video=False,
                         options={"page_layout": "bogus", "no_research": True}))


def test_cli_and_api_validate_the_layout():
    bad = CliRunner().invoke(cli, ["make", "nurse", "weekly_planner", "--page-layout", "bogus", "--llm", "builtin"])
    assert bad.exit_code != 0 and "grid" in bad.output
    none = CliRunner().invoke(cli, ["make", "nurse", "card_deck", "--page-layout", "grid", "--llm", "builtin"])
    assert none.exit_code != 0 and "only one layout" in none.output
    r = TestClient(app).post("/api/jobs", data={"niche": "nurse", "product_type": "weekly_planner", "page_layout": "bogus"})
    assert r.status_code == 422
    assert TestClient(app).get("/api/layout-preview.png?product_type=weekly_planner&layout=bogus").status_code == 404


# ---------------------------------------------------------------- generated layouts (specs)
import random as _random
import tempfile
from pathlib import Path

from moneyhub import layouts as lay
from moneyhub.design import choose_style
from moneyhub.niches import resolve_niche
from moneyhub.products import get_product_type
from moneyhub.products.base import BuildContext


def test_every_generated_weekly_spec_is_internally_consistent():
    for seed in range(1, 400):
        s = lay.random_weekly_spec(seed)
        assert s == s.normalised()
        assert s.blocks <= 6
        if s.days in ("grid", "columns"):
            assert s.body not in ("right", "left")
        if s.body == "none":
            assert s.blocks == 0
        if s.days == "grid":
            assert "notes" not in s.extras


def test_generated_layouts_are_reproducible_and_varied():
    assert lay.random_weekly_spec(7) == lay.random_weekly_spec(7)
    assert len({lay.random_weekly_spec(n).model_dump_json() for n in range(1, 60)}) > 40
    assert len({lay.random_daily_spec(n).model_dump_json() for n in range(1, 60)}) > 40


def test_resolve_handles_presets_generated_custom_and_unknown():
    assert lay.resolve("weekly_planner", "grid").days == "grid"
    assert lay.resolve("weekly_planner", "auto:12") == lay.random_weekly_spec(12)
    assert lay.resolve("weekly_planner", "auto", default_seed=5) == lay.random_weekly_spec(5)
    custom = lay.resolve("daily_planner", "custom", {"layout_spec": {"schedule": "none", "todo_rows": 16, "boxes": 3, "notes": True}})
    assert custom.schedule == "none" and custom.todo_rows < 16   # trimmed so everything fits one page
    with pytest.raises(Exception):   # out-of-range values are refused, not silently clamped
        lay.resolve("daily_planner", "custom", {"layout_spec": {"todo_rows": 30}})
    with pytest.raises(ValueError):
        lay.resolve("weekly_planner", "nonsense")


def test_description_without_an_ai_helper_gives_a_stable_generated_layout():
    a, how = lay.spec_from_text("weekly_planner", "big priorities on the left", router=None)
    b, _ = lay.spec_from_text("weekly_planner", "big priorities on the left", router=None)
    assert how == "random" and a == b


def test_description_uses_the_ai_helper_when_it_answers():
    class Stub:
        def complete_json(self, task, system, prompt, model, **kw):
            assert "treat as a description" in prompt
            return model(name="stub", body="left", days="columns", boxes=5, extras=["habits", "priorities"])
    spec, how = lay.spec_from_text("weekly_planner", "anything", router=Stub())
    assert how == "ai" and spec.body == "bottom" and spec.blocks <= 6   # repaired: columns cannot have a side column


@pytest.mark.parametrize("ptype,size", [("weekly_planner", "letter"), ("weekly_planner", "tablet"), ("weekly_planner", "eink"), ("daily_planner", "a4"), ("daily_planner", "eink")])
def test_generated_layouts_fit_on_every_page_size(ptype, size):
    pt = get_product_type(ptype)
    for seed in (3, 11, 29):
        niche, opts = resolve_niche("nurse"), {"page_layout": f"auto:{seed}", "weeks": 4, "days": 7}
        with tempfile.TemporaryDirectory() as td:
            ctx = BuildContext(niche=niche, style=choose_style(seed=2), out_dir=Path(td), sizes=[size], seed=2, providers=["builtin"], options=opts)
            res = pt.build(ctx, pt.builtin_content(niche, _random.Random(2), opts))
            assert res.files and res.meta["layout_spec"] and res.meta["layout_notes"] == [], (seed, res.meta["layout_notes"])


def test_api_designs_a_layout_and_rejects_a_bad_one(monkeypatch):
    class NoAI:
        def complete_json(self, *a, **k):
            return None
    monkeypatch.setattr("moneyhub.web.app.get_router", lambda: NoAI())
    local = TestClient(app, base_url="http://127.0.0.1:8766")
    r = local.post("/api/layout-spec", data={"product_type": "weekly_planner", "text": "habit row at the bottom"})
    assert r.status_code == 200 and r.json()["source"] == "random" and r.json()["spec"]["body"]
    assert local.post("/api/layout-spec", data={"product_type": "card_deck", "text": "x"}).status_code == 422
    assert TestClient(app, base_url="http://evil.example").post("/api/layout-spec", data={"product_type": "weekly_planner", "text": "x"}).status_code == 403
    assert local.get('/api/layout-preview.png?product_type=weekly_planner&layout=custom&spec={"days":"nope"}').status_code == 422
    good = '{"body":"top","days":"list","boxes":3}'
    assert local.get(f"/api/layout-preview.png?product_type=weekly_planner&layout=custom&spec={good}").status_code == 200


# ---------------------------------------------------------------- wall art layouts
def test_wall_art_has_layouts_and_every_one_looks_different():
    t = get_product_type("wall_art")
    assert next(iter(t.layouts)) == "stacked" and "mixed" in t.layouts and t.auto_layout
    pics = {name: layout_preview_png("wall_art", name, palette="sage") for name in t.layouts if name != "mixed"}
    assert len(set(pics.values())) == len(pics)


def test_every_generated_wall_art_spec_is_consistent_and_its_text_fits():
    from moneyhub.products.wall_art import fit_text
    for seed in range(1, 300):
        s = lay.random_art_spec(seed)
        assert s == s.normalised()
        b = lay.art_boxes(s)
        for text in ("Rest is part of the work", "x" * 70):
            fs, top = fit_text(text, b)
            assert 2.4 <= fs <= 6 and 0 <= top < 100


def test_wall_art_old_numbers_map_to_presets_and_bad_layouts_are_refused():
    r = CliRunner().invoke(cli, ["make", "nurse", "wall_art", "--page-layout", "bogus", "--llm", "builtin"])
    assert r.exit_code != 0 and "stacked" in r.output
    assert CliRunner().invoke(cli, ["make", "nurse", "wall_art", "--layout", "9", "--llm", "builtin"]).exit_code != 0
    res = generate(Request("nurse", "wall_art", providers=["builtin"], seed=3, sizes=["4x5"], with_images=False, with_video=False,
                           options={"page_layout": "poster"}))
    assert res.qa_status in ("pass", "warn")


def test_wall_art_described_and_generated_layouts_build():
    spec, how = lay.spec_from_text("wall_art", "frame it, no artwork, big text", None)
    assert how == "random"
    for opts in ({"layout_spec": spec.model_dump()}, {"page_layout": "auto:5"}, {"page_layout": "mixed"}):
        res = generate(Request("nurse", "wall_art", providers=["builtin"], seed=3, sizes=["4x5"], with_images=False, with_video=False, options=opts))
        assert res.qa_status in ("pass", "warn")
