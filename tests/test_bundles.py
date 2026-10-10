import json
import zipfile

import pytest
from typer.testing import CliRunner

from moneyhub import bundles
from moneyhub.cli import app


def test_theme_bundle_shares_one_look_and_packs_a_listing_kit():
    res = bundles.build_bundle("halloween", ["kids_coloring", "sticker_sheets"], seed=5, providers=["builtin"], sizes=["letter"], with_images=False)
    assert len(res.products) == 2 and all(r.qa_status != "fail" for r in res.products)
    meta = json.loads((res.folder / "bundle.json").read_text())
    assert meta["name"] == "Spooky Halloween Bundle" and len(meta["products"]) == 2
    listing = (res.folder / "listing.md").read_text()
    assert "halloween bundle" in listing and "Coloring Pages + Stickers" in listing and "AI-assisted" in listing and listing.count("sold separately") == 2
    assert (res.folder / "bundle-cover.jpg").exists()
    names = zipfile.ZipFile(next((res.folder / "product").glob("*.zip"))).namelist()
    assert sum(n.endswith(".pdf") for n in names) >= 2
    from moneyhub.store import Store
    styles = {Store().product(r.product_id)["style"] for r in res.products}
    assert len(styles) == 1   # one shared palette and font pair


def test_bundle_rejects_bad_input():
    with pytest.raises(ValueError):
        bundles.build_bundle("halloween", ["kids_coloring"], providers=["builtin"])
    with pytest.raises(ValueError):
        bundles.build_bundle("halloween", ["kids_coloring", "nope"], providers=["builtin"])
    r = CliRunner().invoke(app, ["bundle", "3,4"])
    assert r.exit_code != 0   # ids need --name


def test_make_many_makes_distinct_variations_and_a_summary():
    rows = bundles.make_many("x", "sticker_sheets", 3, ["look", "theme"], seed=9, providers=["builtin"], sizes=["letter"], with_images=False)
    assert len(rows) == 3 and len({r.title for r in rows}) == 3 and all(r.qa != "fail" for r in rows)
    assert len({r.folder for r in rows}) == 3
    with pytest.raises(ValueError):
        bundles.make_many("x", "sticker_sheets", 0)
    with pytest.raises(ValueError):
        bundles.make_many("x", "sticker_sheets", 2, ["bogus"])
    r = CliRunner().invoke(app, ["make-many", "x", "sticker_sheets", "--count", "2", "--vary", "look", "--llm", "builtin", "--no-images", "--sizes", "letter"])
    assert r.exit_code == 0 and "Uniqueness" in r.output and "2 made" in r.output
