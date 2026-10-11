import re
import xml.etree.ElementTree as ET

import pytest
from typer.testing import CliRunner

from moneyhub import decor
from moneyhub.cli import app
from moneyhub.design import PALETTES, choose_style, contrast
from moneyhub.pipeline import Request, generate
from moneyhub.render.html import PAGE_SIZES, render_html
from moneyhub.render.raster import pdf_page_count, render_pages


def styled(**kw):
    st = choose_style(seed=5, palette="sage")
    st.extra["decor"] = decor.make(**kw).as_dict()
    return st


def svgs_in(css_text):
    import base64
    return [base64.b64decode(m).decode() for m in re.findall(r"base64,([A-Za-z0-9+/=]+)", css_text)]


# ------------------------------------------------------------------------------------------------ settings
def test_everything_is_off_by_default_and_nothing_is_added_to_the_page():
    st = choose_style(seed=5, palette="sage")
    assert decor.of(st) is None and decor.css(st) == ""
    html = render_html("look_preview.html.j2", st, PAGE_SIZES["a5"], title="x", tagline="y")
    assert "hdr-art" not in html and "::before" not in html and "::after" not in html and "base64" not in html
    assert not decor.make().active and decor.make().strength == "light" and decor.make().corner_at == "bottom-right"


def test_wrong_values_are_refused_with_the_allowed_ones():
    for kw in ({"corner": "bogus"}, {"header": "x"}, {"background": "plaid"}, {"strength": "huge"}, {"corner_at": "middle"}, {"theme": "space"}):
        with pytest.raises(ValueError) as e:
            decor.make(**kw)
        assert "Choose from" in str(e.value)
    assert decor.make(corner="none", header="NONE").corner == "none"


def test_yaml_defaults_fill_the_blanks_and_options_win():
    d = decor.make(defaults={"corner": "waves", "strength": "bold"})
    assert (d.corner, d.strength, d.header) == ("waves", "bold", "none")
    assert decor.make(corner="floral", defaults={"corner": "waves"}).corner == "floral"
    assert decor.from_options({"decor_header": "hearts", "decor_strength": "medium"}).header == "hearts"


def test_theme_follows_the_audience():
    assert decor.theme_for("nurse") == "medical" and decor.theme_for("gardening") == "garden" and decor.theme_for("teacher") == "school"
    assert decor.theme_for("custom", "dog trainers who love puppies") == "pets" and decor.theme_for("custom", "wedding florists") == "wedding"
    assert decor.theme_for("custom", "origami collectors") == "general"
    from moneyhub.niches import LIBRARY
    assert all(decor.theme_for(k) in decor.THEMES for k in LIBRARY) and all(k in decor.NICHE_THEME for k in LIBRARY)
    assert decor.make(niche_key="nurse").theme == "medical" and decor.make(niche_key="nurse", theme="pets").theme == "pets"


# ------------------------------------------------------------------------------------------------ drawing
def test_every_style_draws_valid_svg_in_every_palette():
    for pal in PALETTES:
        st = choose_style(seed=3, palette=pal.key)
        for corner in decor.CORNER_STYLES:
            for at in decor.CORNER_AT:
                st.extra["decor"] = decor.make(corner=corner, corner_at=at, theme="garden").as_dict()
                for s in svgs_in(decor.css(st)):
                    ET.fromstring(s)
    d = decor.make(header="themed", theme="medical")
    for h in decor.HEADER_STYLES:
        ET.fromstring(decor.header_art(decor.make(header=h, theme="medical"), "#123456"))
    for b in decor.BACKGROUND_STYLES:
        st = styled(background=b, theme="food")
        out = svgs_in(decor.css(st))
        assert len(out) == 1
        ET.fromstring(out[0])
    assert d.theme == "medical"
    for name, body in decor.M.items():                       # every picture is well formed
        ET.fromstring(f"<svg xmlns='http://www.w3.org/2000/svg'>{body}</svg>")
    assert all(p in decor.M for pics in decor.THEMES.values() for p in pics)


def test_layers_are_independent_and_strength_changes_the_opacity():
    only_header = decor.css(styled(header="themed"))
    assert ".hdr-art" in only_header and "::before" not in only_header and "::after" not in only_header
    only_bg = decor.css(styled(background="dots"))
    assert "::before" in only_bg and "::after" not in only_bg and ".hdr-art" not in only_bg
    only_corner = decor.css(styled(corner="floral"))
    assert "::after" in only_corner and "::before" not in only_corner
    both = decor.css(styled(corner="floral", corner_at="opposite"))
    assert len(svgs_in(both)) == 2
    light = svgs_in(decor.css(styled(corner="waves", strength="light")))[0]
    bold = svgs_in(decor.css(styled(corner="waves", strength="bold")))[0]
    op = lambda s: float(re.search(r"opacity='([0-9.]+)'", s).group(1))   # noqa: E731
    assert op(light) < op(bold) <= .32 + 1e-9


def test_the_strongest_background_never_hurts_readability():
    """Ink text must still have strong contrast on the darkest tint the background can make, for every palette and strength."""
    for pal in PALETTES:
        for strength in decor.STRENGTHS:
            d = decor.make(background="dots", strength=strength)
            assert contrast(pal.ink, decor.tint(pal, d)) >= 7, (pal.key, strength)
            assert contrast(pal.muted, decor.tint(pal, d)) >= 4.5, (pal.key, strength)


def test_ink_note_only_for_a_background():
    assert decor.ink_note(None) == "" and decor.ink_note(decor.make(corner="waves")) == ""
    assert "ink" in decor.ink_note(decor.make(background="dots"))
    assert "title bar" in decor.describe(decor.make(header="themed")) and decor.describe(decor.make()) == ""


# ------------------------------------------------------------------------------------------------ products
def make_planner(**opts):
    return generate(Request("nurse", "weekly_planner", providers=["builtin"], seed=3, sizes=["letter"], with_images=False, with_video=False,
                            options={"no_research": True, **opts}))


def test_a_decorated_planner_keeps_its_pages_and_says_so_in_the_listing():
    plain, deco = make_planner(), make_planner(decor_corner="themed", decor_header="themed", decor_background="dots", decor_strength="medium")
    pp, dp = (next((r.folder / "product").glob("*letter.pdf")) for r in (plain, deco))
    assert pdf_page_count(pp) == pdf_page_count(dp)                        # decoration never adds pages
    a, b = render_pages(pp, [2], 0.5)[0].convert("L"), render_pages(dp, [2], 0.5)[0].convert("L")
    import numpy as np
    assert np.asarray(b, dtype=float).mean() < np.asarray(a, dtype=float).mean()      # it does use ink
    desc = (deco.folder / "listing" / "etsy-description.txt").read_text()
    assert "Decorated pages" in desc and "more ink" in desc
    assert "more ink" not in (plain.folder / "listing" / "etsy-description.txt").read_text()
    assert not [c for c in deco.checks if c.status == "fail"]
    import json
    assert json.loads((deco.folder / "spec.json").read_text())["style"]["extra"]["decor"]["corner"] == "themed" if "extra" in json.loads((deco.folder / "spec.json").read_text()).get("style", {}) else True


def test_without_options_the_pdf_is_the_same_as_before():
    a, b = make_planner(), make_planner(decor_corner="none")
    pa, pb = (next((r.folder / "product").glob("*letter.pdf")) for r in (a, b))
    assert pdf_page_count(pa) == pdf_page_count(pb)
    import numpy as np
    assert np.array_equal(np.asarray(render_pages(pa, [3], 0.5)[0]), np.asarray(render_pages(pb, [3], 0.5)[0]))


def test_unsupported_products_refuse_decoration_but_ignore_yaml_defaults():
    with pytest.raises(ValueError) as e:
        generate(Request("x", "digital_paper", providers=["builtin"], seed=2, with_images=False, with_video=False, options={"no_research": True, "decor_corner": "waves"}))
    assert "no page decoration" in str(e.value) and "weekly_planner" in str(e.value)
    assert all(t.decor_ok for k, t in __import__("moneyhub.products", fromlist=["x"]).all_product_types().items()
               if k in ("weekly_planner", "daily_planner", "guided_journal", "habit_tracker", "budget_tracker", "checklist_pack", "worksheet_pack", "ebook_guide"))


def test_eink_versions_stay_plain():
    res = generate(Request("nurse", "weekly_planner", providers=["builtin"], seed=3, with_images=False, with_video=False,
                           options={"no_research": True, "eink": True, "decor_corner": "waves", "decor_background": "dots"}))
    assert "Decorated pages" not in (res.folder / "listing" / "etsy-description.txt").read_text()


# ------------------------------------------------------------------------------------------------ command line and web
def test_cli_flags_validate_and_styles_lists_the_options():
    r = CliRunner().invoke(app, ["make", "nurse", "weekly_planner", "--decor-corner", "bogus"])
    assert r.exit_code != 0 and "Choose from" in r.output
    r = CliRunner().invoke(app, ["make", "nurse", "weekly_planner", "--decor", "sideways"])
    assert r.exit_code != 0
    out = CliRunner().invoke(app, ["styles"]).output
    assert "--decor-corner" in out and "watercolor" in out and "medical" in out


def test_preview_and_job_endpoints_check_decoration_values():
    from fastapi.testclient import TestClient
    from moneyhub.web.app import app as web
    c = TestClient(web)
    assert c.get("/api/preview.png", params={"decor_corner": "bogus"}).status_code == 422
    ok = c.get("/api/preview.png", params={"decor_corner": "floral", "decor_header": "hearts", "decor_strength": "medium"})
    assert ok.status_code == 200 and ok.content[:4] == b"\x89PNG"
    assert c.post("/api/jobs", data={"niche": "nurse", "product_type": "weekly_planner", "decor_strength": "huge"}).status_code == 422
    page = c.get("/make").text
    assert 'id="decor-opts"' in page and 'name="decor_corner"' in page and 'data-decor="1"' in page and 'data-theme="medical"' in page
