import json
import random
import zipfile

import pytest
from pypdf import PdfReader

from moneyhub.exports import kdp, load, notion
from moneyhub.exports.canva import export_canva
from moneyhub.niches import resolve_niche
from moneyhub.pipeline import Request, generate
from moneyhub.products import all_product_types
from moneyhub.store import Store


@pytest.fixture(scope="module")
def planner():
    r = generate(Request("nurse", "weekly_planner", providers=["builtin"], seed=6, sizes=["letter"], with_images=False, with_video=False,
                         options={"weeks": 4, "no_research": True}))
    return load(r.product_id, Store())


@pytest.mark.parametrize("ptype", notion.SUPPORTED)
def test_notion_pack_has_start_page_and_content_for_every_supported_type(ptype):
    t = all_product_types()[ptype]
    content = t.builtin_content(resolve_niche("nurse"), random.Random(1), {"weeks": 4, "days": 7}).model_dump()
    files = notion.build_pages(ptype, content)
    assert "Start Here.md" in files and len(files) >= 2
    assert all(isinstance(v, str) and v.strip() for v in files.values())


def test_notion_refuses_wall_art():
    with pytest.raises(ValueError, match="no Notion version"):
        notion.build_pages("wall_art", {"title": "x"})


def test_notion_zip_imports_as_markdown_and_csv(planner):
    z = notion.export_notion(planner)
    names = zipfile.ZipFile(z).namelist()
    assert any(n.endswith("Start Here.md") for n in names) and any(n.endswith("Weeks.csv") for n in names)


def test_kdp_numbers_follow_the_published_rules():
    assert [kdp.gutter_in(p) for p in (24, 150, 151, 300, 301, 500, 501, 700, 701)] == [0.375, 0.375, 0.5, 0.5, 0.625, 0.625, 0.75, 0.75, 0.875]
    assert kdp.spine_in(100, "white") == 0.2252 and kdp.spine_in(100, "cream") == 0.25
    c = kdp.cover_size("6x9", 100, "white")
    assert c["full_cover_in"] == [12.4752, 9.25] and c["full_cover_px_300dpi"] == [3743, 2775]


def test_kdp_pack_has_exact_trim_even_pages_and_cover_template(planner):
    spec = kdp.export_kdp(planner, "6x9", "white", progress=lambda m: None)
    d = planner.folder / "exports" / "kdp"
    interior = next(d.glob("*interior-6x9.pdf"))
    r = PdfReader(str(interior))
    assert len(r.pages) == spec["pages"] and spec["pages"] >= 24 and spec["pages"] % 2 == 0
    w, h = (float(x) / 72 for x in r.pages[0].mediabox[2:])
    assert (round(w, 2), round(h, 2)) == (6.0, 9.0)
    assert all(c["ok"] for c in spec["checks"]) and (d / "KDP-GUIDE.md").exists() and next(d.glob("*cover-template*.pdf"))
    assert json.loads((d / "cover-spec.json").read_text())["spine_in"] == spec["spine_in"]


def test_kdp_makes_a_finished_cover_and_can_use_your_own_image(planner, tmp_path):
    from PIL import Image
    spec = kdp.export_kdp(planner, "6x9", "white", progress=lambda m: None)
    d = planner.folder / "exports" / "kdp"
    cover = d / spec["cover_pdf"]
    cw, ch = spec["full_cover_in"]
    w, h = (float(x) / 72 for x in PdfReader(str(cover)).pages[0].mediabox[2:])
    assert abs(w - cw) < 0.02 and abs(h - ch) < 0.02 and spec["cover_image"] is None
    art = tmp_path / "art.png"
    Image.new("RGB", (600, 900), "teal").save(art)
    spec = kdp.export_kdp(planner, "6x9", "white", progress=lambda m: None, cover_image=art, cover_text=False)
    sharp = next(c for c in spec["checks"] if c["name"] == "Cover image sharpness")
    assert not sharp["ok"] and spec["cover_image"]["effective_dpi"] < 250   # a small picture is flagged, not silently used
    bad = tmp_path / "x.png"
    bad.write_text("not a picture")
    with pytest.raises(ValueError, match="cannot read the cover image"):
        kdp.export_kdp(planner, "6x9", "white", progress=lambda m: None, cover_image=bad)


def test_kdp_cover_upload_through_the_web_form():
    from fastapi.testclient import TestClient
    from moneyhub.web.app import app
    res = generate(Request("nurse", "checklist_pack", providers=["builtin"], seed=2, sizes=["letter"], with_images=False, with_video=False, options={"no_research": True}))
    r = TestClient(app).post(f"/product/{res.product_id}/export", data={"kind": "kdp"}, files={"cover_image": ("x.png", b"not a picture", "image/png")})
    assert r.status_code == 422


def test_kdp_rejects_unsupported_products():
    class L:  # only the type is looked at before refusing
        ptype = "wall_art"
    with pytest.raises(ValueError, match="cannot be a KDP paperback"):
        kdp.export_kdp(L())  # type: ignore[arg-type]


def test_canva_pack_has_pages_brand_kit_and_link_page(planner):
    d = export_canva(planner, link="https://www.canva.com/design/example/view")
    assert (d / "brand-kit.json").exists() and (d / "HOW-TO-CANVA.md").exists()
    assert len(list((d / "pages").glob("page-*.png"))) >= 3
    link_pdf = next(d.glob("*canva-template-link.pdf"))
    uris = [a.get_object()["/A"]["/URI"] for p in PdfReader(str(link_pdf)).pages for a in (p.get("/Annots") or []) if "/A" in a.get_object()]
    assert "https://www.canva.com/design/example/view" in uris


def test_each_platform_export_ends_with_one_pack_zip_containing_its_guide(planner):
    import zipfile
    export_canva(planner)
    kdp.export_kdp(planner, "6x9", "white", progress=lambda m: None)
    notion.export_notion(planner)
    for kind, guide in (("canva", "HOW-TO-CANVA.md"), ("kdp", "KDP-GUIDE.md"), ("notion", "-notion-guide.md")):
        z = next((planner.folder / "exports").glob(f"*-{kind}-pack.zip"))
        names = zipfile.ZipFile(z).namelist()
        assert any(n.endswith(guide) for n in names), (kind, names)
        assert not any(n.endswith("-pack.zip") for n in names)   # never nests itself
