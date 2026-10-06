import pytest

from moneyhub.design import EINK, brand_palette, choose_style, is_hex_colour, style_from_dict
from moneyhub.pipeline import Request, generate
from moneyhub.render.html import PAGE_SIZES
from moneyhub.render.motion import ENGINES, MotionPlan, Scene, builtin_plan


@pytest.mark.parametrize("colour", ["#2F6B57", "#FFD700", "#F4A6C0", "#111111", "#FFFFFF"])
def test_brand_palette_is_readable_for_any_colour(colour):
    assert brand_palette(colour).issues() == []


def test_brand_style_survives_a_save_and_reload():
    s = choose_style(seed=2, brand="#336699")
    assert s.palette.key == "custom" and style_from_dict(s.describe()).palette == s.palette


def test_bad_brand_colour_is_rejected():
    assert not is_hex_colour("blue")
    with pytest.raises(ValueError):
        choose_style(brand="blue")


def test_eink_style_is_black_and_white_with_crisp_lines():
    s = choose_style(seed=1, eink=True)
    assert s.palette == EINK and (s.header, s.radius, s.grid) == ("rule", 0, "solid")
    assert style_from_dict(s.describe()).palette == EINK
    assert "eink" in PAGE_SIZES and PAGE_SIZES["eink"].height_in > PAGE_SIZES["eink"].width_in


def test_eink_planner_is_built_hyperlinked_and_black_and_white():
    r = generate(Request("nurse", "weekly_planner", providers=["builtin"], seed=3, with_images=False, with_video=False,
                         options={"eink": True, "weeks": 4, "no_research": True}))
    names = [p.name for p in (r.folder / "product").glob("*.pdf")]
    assert any("eink-hyperlinked" in n for n in names)


def test_eink_is_refused_for_products_without_an_eink_version():
    with pytest.raises(ValueError, match="no e-ink version"):
        generate(Request("nurse", "budget_tracker", providers=["builtin"], with_images=False, with_video=False, options={"eink": True, "no_research": True}))


def test_listing_images_follow_the_chosen_marketplaces():
    r = generate(Request("nurse", "checklist_pack", providers=["builtin"], seed=4, with_video=False, marketplaces=["gumroad"],
                         options={"no_research": True}))
    made = sorted(p.name for p in (r.folder / "images").iterdir())
    assert made == ["gumroad"]


def test_spelling_flags_typos_but_not_niche_words():
    pytest.importorskip("spellchecker")
    from moneyhub.niches import resolve_niche
    from moneyhub.spellcheck import misspellings
    bad = dict(misspellings(["You will recieve a beutiful planer."]))
    assert "recieve" in bad and bad["recieve"] == "receive"
    assert misspellings(["Printable ADHD planner for nurses on Etsy and Pinterest, ready for GoodNotes."], resolve_niche("nurse")) == []


def test_hyperframes_composition_has_every_scene_and_a_registered_timeline():
    plan = builtin_plan("Nurse Planner", "Undated", ["52 weeks", "Goal pages"], "Plan the week")
    props = {"width": 1000, "height": 1500, "fps": 24, "title": "t", "pages": ["page-0.png"], "fontFiles": [],
             "palette": {k: "#112233" for k in ("paper", "ink", "muted", "line", "accent", "accentInk", "soft", "accent2")},
             "fonts": {"heading": "Lora", "body": "Inter", "script": "Caveat"}}
    html = ENGINES["hyperframes"].composition(plan, props)
    assert html.count("class='clip sc'") == len(plan.scenes)
    assert 'data-composition-id="main"' in html and 'window.__timelines["main"] = tl' in html


@pytest.mark.skipif(not ENGINES["hyperframes"].available(), reason="HyperFrames not installed (moneyhub engines install hyperframes)")
def test_hyperframes_renders_a_video(tmp_path):
    from PIL import Image
    from moneyhub.render import graphics as g
    plan = MotionPlan(scenes=[Scene(kind="title", text="Hello", seconds=1.0), Scene(kind="page", text="Look", seconds=1.0),
                              Scene(kind="cta", text="Buy", seconds=1.0)])
    out = ENGINES["hyperframes"].render(plan, [Image.new("RGB", (400, 500), "white")], g.Brush(choose_style(seed=1)), tmp_path / "v.mp4", (500, 750), "t", 12)
    assert out and out.exists() and out.stat().st_size > 5000
