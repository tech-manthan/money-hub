import re
import zipfile

import pytest

from moneyhub import coloring, cutfiles
from moneyhub.design import PALETTES
from moneyhub.exports import kdp, load
from moneyhub.pipeline import Request, generate
from moneyhub.render import mockups
from moneyhub.store import Store


# ------------------------------------------------------------------ coloring pages
def test_line_art_has_white_fills_ink_strokes_and_outlined_bands():
    out = coloring.lineart("<circle cx='5' cy='5' r='3' fill='#123456'/><path d='M0 0 L9 9' fill='none' stroke='#ff0000' stroke-width='40'/><rect width='4' height='4'/>")
    assert "#123456" not in out and "#ff0000" not in out
    assert out.count("fill='#ffffff'") >= 2 and "stroke='#ffffff' stroke-width='40'" in out   # the circle and rect, and the band's white core
    assert "stroke-width='50.0'" in out        # the band's black outline is wider than the band itself
    assert re.search(r"<rect [^>]*fill='#ffffff'", out)


def test_every_coloring_page_kind_is_black_and_white_line_art():
    for i in range(20):
        kind, svg = coloring.page_art(i, 3, PALETTES[0])
        colours = set(re.findall(r"#[0-9a-fA-F]{6}", svg))
        assert colours <= {"#ffffff", coloring.INK}, (kind, colours)


def test_coloring_pack_and_kdp_coloring_book_interior():
    res = generate(Request("nurse", "coloring_pages", providers=["builtin"], seed=2, sizes=["letter"], with_video=False, options={"no_research": True, "pages": 12}))
    assert not [c for c in res.checks if c.status == "fail"]
    from moneyhub.render.raster import pdf_page_count
    pdf = next((res.folder / "product").glob("*letter.pdf"))
    assert pdf_page_count(pdf) == 13   # a cover and 12 pages
    spec = kdp.export_kdp(load(res.product_id, Store()), "8.5x11", "white", progress=lambda m: None)
    assert all(c["ok"] for c in spec["checks"]) and spec["pages"] % 2 == 0 and spec["pages"] >= 24   # 12 designs, each with a blank back


# ------------------------------------------------------------------ cut files
@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_every_cut_design_is_closed_valid_and_has_cuts_a_mat_can_hold(seed):
    for d in cutfiles.make_designs(40, seed):
        assert d.rings and all(len(r) >= 3 for r in d.rings)
        assert all(0 <= x <= 1000 and 0 <= y <= 1000 for r in d.rings for x, y in r), d.name
        assert cutfiles.thinnest_gap_mm(d, 6) >= cutfiles.MIN_GAP_MM, d.name
    names = [d.name for d in cutfiles.make_designs(40, seed)]
    assert len(set(names)) == len(names)


def test_cut_file_exports_are_well_formed():
    d = cutfiles.heart(hole=True)
    svg, dxf, eps = cutfiles.to_svg(d, 6), cutfiles.to_dxf(d, 6), cutfiles.to_eps(d, 6)
    assert "width='6in'" in svg and "fill-rule='evenodd'" in svg and svg.count(" Z") == 2
    lines = dxf.splitlines()
    assert lines[:4] == ["0", "SECTION", "2", "ENTITIES"] and lines[-1] == "EOF" and lines.count("POLYLINE") == 2 and lines.count("SEQEND") == 2
    xs = [float(lines[i + 1]) for i, v in enumerate(lines) if v == "10"]
    assert 0 <= min(xs) and max(xs) <= 6.0   # inches
    assert eps.startswith("%!PS-Adobe-3.0 EPSF-3.0") and "%%BoundingBox: 0 0 432 432" in eps and eps.count("closepath") == 2 and "eofill" in eps


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_every_cut_design_survives_a_round_trip_through_svg_and_dxf(seed):
    for d in cutfiles.make_designs(40, seed):
        assert cutfiles.validate_exports(d, 6) == [], d.name


def test_round_trip_check_catches_broken_files():
    d = cutfiles.heart(hole=True)
    assert any("not closed" in p for p in cutfiles.validate_exports(d, 6, svg=cutfiles.to_svg(d, 6).replace(" Z", "")))
    assert any("inches" in p for p in cutfiles.validate_exports(d, 6, svg=cutfiles.to_svg(d, 6).replace("6in", "6px")))
    assert any("open polyline" in p for p in cutfiles.validate_exports(d, 6, dxf=cutfiles.to_dxf(d, 6).replace("70\n1", "70\n0")))
    other = cutfiles.star(5, .4, hole=True)
    assert len(other.rings) == 2
    assert any("different shapes" in p for p in cutfiles.validate_exports(d, 6, dxf=cutfiles.to_dxf(other, 6)))


def test_cut_files_bundle_has_four_formats_licence_and_passes_qa():
    res = generate(Request("nurse", "cut_files", providers=["builtin"], seed=2, with_video=False, options={"no_research": True, "designs": 12}))
    assert not [c for c in res.checks if c.status == "fail"] and any(c.name == "Cut-ready" and c.status == "pass" for c in res.checks)
    assert any(c.name == "Opens in cutting software" and c.status == "pass" for c in res.checks)
    names = {p.name: p for p in (res.folder / "product").glob("*")}
    assert len(names) == 5 and "Commercial-License.pdf" in names   # four zips and the licence: Etsy's five-file limit
    for ext in ("svg", "dxf", "eps", "png"):
        z = zipfile.ZipFile(next(p for n, p in names.items() if n.endswith(f"-{ext.upper()}.zip")))
        assert len([n for n in z.namelist() if n.endswith(f".{ext}")]) == 12
    assert "garden" not in (res.folder / "listing" / "etsy-description.txt").read_text().lower()


# ------------------------------------------------------------------ room mockups
def test_room_scenes_render_at_etsy_size_and_differ():
    from PIL import Image
    art = Image.new("RGB", (800, 1000), "#d1495b")
    scenes = {n: mockups.room_scene(n, [art], PALETTES[0]) for n in mockups.SCENES}
    assert all(im.size == (2700, 2025) for im in scenes.values())
    assert len({im.tobytes() for im in scenes.values()}) == len(scenes)
    for im in scenes.values():   # the artwork's colour really appears in the room
        import numpy as np
        a = np.asarray(im.resize((135, 101)), dtype=int)
        assert (np.abs(a - np.array([209, 73, 91])).max(axis=2) < 12).sum() > 50


def test_wall_art_listing_gets_four_room_photos_within_etsys_limits():
    from PIL import Image
    res = generate(Request("nurse", "wall_art", providers=["builtin"], seed=3, sizes=["4x5"], with_video=False, options={"no_research": True}))
    et = sorted((res.folder / "images" / "etsy").glob("*"))
    rooms = [f for f in et if "-room-" in f.name]
    assert len(rooms) == 4 and len(et) <= 10
    for f in rooms:
        assert f.stat().st_size < 1_000_000 and Image.open(f).size == (2700, 2025)
