import re
import zipfile

import pytest

from moneyhub import coloring, cutfiles
from moneyhub.design import PALETTES
from moneyhub.exports import kdp, load
from moneyhub.pipeline import Request, generate
from moneyhub.render.raster import pdf_page_count
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
    assert "$INSUNITS" in lines and lines[lines.index("$INSUNITS") + 2] == "1" and lines[-1] == "EOF" and lines.count("POLYLINE") == 2 and lines.count("SEQEND") == 2
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


@pytest.mark.skipif(__import__("shutil").which("inkscape") is None, reason="Inkscape not installed")
def test_inkscape_renders_cut_svgs_like_our_own_renderer(tmp_path):
    import subprocess

    from PIL import Image
    d = cutfiles.heart(hole=True)
    svg = tmp_path / "h.svg"
    svg.write_text(cutfiles.to_svg(d, 6))
    png = tmp_path / "h.png"
    subprocess.run(["inkscape", str(svg), "--export-type=png", f"--export-filename={png}", "-b", "white", "-d", "96"], check=True, capture_output=True, timeout=120)
    im = Image.open(png).convert("L")
    assert im.size == (576, 576)   # 6 in at 96 dpi: real inch size
    ink = sum(1 for v in im.get_flattened_data() if v < 128) / (576 * 576) if hasattr(im, "get_flattened_data") else sum(1 for v in im.getdata() if v < 128) / (576 * 576)
    assert 0.25 < ink < 0.75   # a filled heart with a hole, not blank and not solid


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


# ------------------------------------------------------------------ kids coloring books
def test_every_kids_figure_draws_for_any_seed_and_age():
    from moneyhub import kidsart
    for kind in kidsart.KINDS:
        outlines = {kidsart.figure(kind, s, 10, False) for s in range(6)}
        assert all(len(o) > 400 and "NaN" not in o for o in outlines), kind
    for age in kidsart.AGES:
        for i in range(30):
            kind, svg, caption = kidsart.page_art(i, 3, "mixed", age)
            assert svg.startswith("<svg") and caption.endswith(("!", "!")) and "NaN" not in svg


def test_kids_books_differ_between_seeds_and_figures_do_not_repeat_early():
    from moneyhub import kidsart
    a = [kidsart.page_art(i, 1, "animals")[2] for i in range(10)]
    b = [kidsart.page_art(i, 2, "animals")[2] for i in range(10)]
    assert a != b
    figs = [c for k, (_, _, c) in zip(range(10), (kidsart.page_art(i, 1, "mixed") for i in range(10))) if c.startswith("Color the ")]
    assert len(set(figs)) == len(figs)
    assert kidsart.figure("cat", 1, 10, False) != kidsart.figure("cat", 2, 10, False)   # details change with the seed


def test_kids_coloring_product_is_niche_free_and_kdp_ready():
    res = generate(Request("nurse", "kids_coloring", providers=["builtin"], seed=4, sizes=["letter"], with_video=False, with_images=False,
                           options={"no_research": True, "pages": 12, "theme": "ocean"}))
    assert not [c for c in res.checks if c.status == "fail"]
    assert res.title == "Under the Sea Coloring Pages for Kids"
    listing = (res.folder / "listing" / "etsy-description.txt").read_text().lower()
    assert "nurse" not in listing and "kids" in listing
    pdf = next((res.folder / "product").glob("*.pdf"))
    assert pdf_page_count(pdf) == 13   # a cover plus 12 pages
    from moneyhub.exports import kdp
    assert "kids_coloring" in kdp.SUPPORTED


# ------------------------------------------------------------------ mockups for the other product families
@pytest.mark.parametrize("ptype,opts,expect", [("kids_coloring", {"pages": 10}, 3), ("cut_files", {"designs": 12}, 2), ("clipart_pack", {"colourways": 1}, 3),
                                              ("digital_paper", {}, 3)])
def test_every_product_family_gets_in_use_mockups(ptype, opts, expect):
    res = generate(Request("x", ptype, providers=["builtin"], seed=2, with_video=False, options={"no_research": True, **opts}))
    names = sorted(p.name for p in (res.folder / "images" / "etsy").glob("*mockup*.jpg"))
    assert len(names) == expect
    assert len(list((res.folder / "images" / "etsy").glob("*.jpg"))) <= 10   # Etsy's photo limit
    from PIL import Image
    for n in names:
        assert Image.open(res.folder / "images" / "etsy" / n).size == (2700, 2025)


# ------------------------------------------------------------------ sticker sheets
def test_stickers_are_coloured_with_a_white_die_cut_border():
    from PIL import Image

    from moneyhub import stickers
    pal = PALETTES[0]
    name, svg = stickers.sticker_svg(0, 3, "animals", pal)
    assert "#ffffff" not in svg and pal.ink in svg and name
    im = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    im.paste(Image.new("RGBA", (100, 100), (200, 30, 30, 255)), (100, 100))
    cut = stickers.die_cut(im)
    assert cut.width > 100 + 2 * round(stickers.BORDER_IN * 300) - 4   # grew by the border on every side
    assert cut.getpixel((3, 3))[3] == 0 and cut.getpixel((cut.width // 2, cut.height // 2))[:3] == (200, 30, 30)
    assert cut.getpixel((cut.width // 2, 8))[:3] == (255, 255, 255) and cut.getpixel((cut.width // 2, 8))[3] == 255   # white margin


def test_sticker_sheets_product_has_sheets_png_zip_and_passes_qa():
    res = generate(Request("x", "sticker_sheets", providers=["builtin"], seed=3, sizes=["letter"], with_video=False, with_images=False,
                           options={"no_research": True, "stickers": 14, "theme": "ocean"}))
    assert not [c for c in res.checks if c.status == "fail"]
    assert res.title == "Under the Sea Sticker Sheets"
    assert pdf_page_count(next((res.folder / "product").glob("*-letter.pdf"))) == 2   # 14 stickers: 12 + 2
    z = zipfile.ZipFile(next((res.folder / "product").glob("*PNG-stickers.zip")))
    assert len([n for n in z.namelist() if n.endswith(".png")]) == 14


# ------------------------------------------------------------------ oracle / tarot decks
def test_every_oracle_symbol_draws_and_card_art_differs_by_seed():
    from moneyhub import oracle_art
    pal = PALETTES[0]
    for kind in oracle_art.SYMBOLS:
        svg = oracle_art.card_art(kind, pal, 1)
        assert svg.startswith("<svg") and "NaN" not in svg and len(svg) > 800, kind
    assert oracle_art.card_art("sun", pal, 1) != oracle_art.card_art("sun", pal, 2)   # a different sky
    back = oracle_art.card_back(pal, 1, 1.8)
    assert "viewBox='0 0 600 1080'" in back


def test_built_in_decks_are_complete_and_never_predict():
    from moneyhub import oracle_art
    from moneyhub.products import oracle_deck as od
    assert len(od.TAROT) == 22 and len(od.ORACLE) == 36 and len(od.ROMAN) == 22
    for deck in (od.TAROT, od.ORACLE):
        assert len({c[0] for c in deck}) == len(deck)               # unique names
        assert all(c[3] in oracle_art.SYMBOLS and len(c[2]) <= 110 for c in deck)
        assert not [c for c in deck if any(w in c[2].lower() for w in ("will die", "you will", "guarantee", "cure", "invest"))]


@pytest.mark.parametrize("deck,n", [("tarot", 22), ("oracle", 24)])
def test_oracle_deck_product_pages_and_listing_disclaimer(deck, n):
    res = generate(Request("x", "oracle_deck", providers=["builtin"], seed=2, sizes=["letter"], with_video=False, with_images=False,
                           options={"no_research": True, "deck": deck, "cards": n}))
    assert not [c for c in res.checks if c.status == "fail"]
    pdf = next((res.folder / "product").glob("*-letter.pdf"))
    assert pdf_page_count(pdf) == 2 + -(-n // 6) + 1   # cover + guide + card sheets (6 per sheet) + backs
    assert "not predictions" in (res.folder / "listing" / "etsy-description.txt").read_text().lower()


# ------------------------------------------------------------------ more patterns
def test_all_pattern_kinds_draw_and_scatter_patterns_wrap_seamlessly():
    from PIL import Image

    from moneyhub import patterns
    from moneyhub.products.digital_paper import PATTERN_NAMES, SEAM_CHECKED
    assert len(patterns.KINDS) >= 36 and set(PATTERN_NAMES) == set(patterns.KINDS)
    assert set(SEAM_CHECKED) | set(patterns.HARD_EDGE) == set(patterns.KINDS)
    pal = PALETTES[4]
    for kind in patterns.KINDS:
        assert "NaN" not in patterns.pattern_tile(kind, pal, 3, 0), kind
    import io

    import pypdfium2 as pdfium

    from moneyhub.render.pdf import render_pdf
    import tempfile
    from pathlib import Path
    for kind in [k for k in SEAM_CHECKED if k in patterns.KINDS[12:]]:   # all the newer, non-banded patterns
        with tempfile.TemporaryDirectory() as t:
            html = f"<style>@page{{size:6in 6in;margin:0}}body{{margin:0}}svg{{width:6in;height:6in;display:block}}</style>{patterns.paper_svg(kind, pal, 3, 0, 1)}"
            render_pdf(html, Path(t) / "a.pdf", page_css_size="6in 6in")
            im = pdfium.PdfDocument(str(Path(t) / "a.pdf"))[0].render(scale=2).to_pil().convert("RGB")
        assert patterns.seam_excess(im) <= 12, kind


def test_digital_paper_packs_use_a_seeded_selection_and_coloring_books_walk_through_the_patterns():
    import random

    from moneyhub import coloring
    def names(seed):
        res = generate(Request("x", "digital_paper", providers=["builtin"], seed=seed, with_video=False, with_images=False, options={"no_research": True}))
        z = zipfile.ZipFile(next((res.folder / "product").glob("*JPG*.zip")))
        return sorted(n for n in z.namelist() if n.endswith(".jpg"))
    a, b = names(1), names(2)
    assert len(a) == len(b) == 12 and [n.split("-", 1)[1] for n in a] != [n.split("-", 1)[1] for n in b]   # same size, different patterns
    kinds_seen = set()
    for i in range(60):
        kind, svg, *_ = (*coloring.page_art(i, 7, PALETTES[0]), None)
        assert svg.startswith("<svg") and "NaN" not in svg
        kinds_seen.add(kind)
    assert kinds_seen == {"mandala", "pattern", "motif", "special"}
    order = lambda s: sorted(coloring.PATTERN_KINDS, key=lambda k: random.Random(f"{s}-{k}").random())   # noqa: E731
    assert order(7) != order(8) and len(coloring.PATTERN_KINDS) >= 30


# ------------------------------------------------------------------ bigger libraries: kids figures and wall-art backgrounds
def test_every_kids_figure_theme_and_wall_background_draws():
    from moneyhub import art, kidsart
    assert len(kidsart.KINDS) >= 80 and set(kidsart.KINDS) == set(kidsart._FIGURES) == set(kidsart.NAMES) and len(kidsart.THEMES) >= 20
    for theme, (_, pool) in kidsart.THEMES.items():
        assert pool and all(k in kidsart._FIGURES for k in pool), theme
    pal = PALETTES[4]
    assert len(art.WALL_MOTIFS) > 60 and art.WALL_MOTIFS[:13] == art.MOTIFS
    for kind in art.WALL_MOTIFS:
        for dark in (False, True):
            svg = art.motif_svg(kind, pal, 3, on_dark=dark)
            assert svg.startswith("<svg") and "NaN" not in svg and len(svg) > 300, kind


def test_wall_art_accepts_the_new_backgrounds_and_rejects_unknown_ones():
    res = generate(Request("x", "wall_art", providers=["builtin"], seed=2, with_video=False, with_images=False, options={"no_research": True, "motif": "nursery-bear"}))
    assert not [c for c in res.checks if c.status == "fail"]
    from typer.testing import CliRunner

    from moneyhub.cli import app
    r = CliRunner().invoke(app, ["make", "x", "wall_art", "--motif", "nursery-nope", "--llm", "builtin"])
    assert r.exit_code != 0


# ------------------------------------------------------------------ activity book and learning workbook
def test_mazes_are_always_solvable_and_every_activity_and_learning_page_draws():
    from moneyhub import activities, learning
    for level in activities.LEVELS:
        cols, rows = activities.LEVELS[level]["maze"]
        for seed in range(6):
            passages, path = activities.maze_cells(cols, rows, seed)
            assert path[0] == (0, 0) and path[-1] == (cols - 1, rows - 1)
            assert len(passages) == cols * rows - 1   # a perfect maze: one route between any two cells
            assert all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip(path, path[1:]))
        for i in range(20):
            kind, svg, cap = activities.page_art(i, 3, level)
            assert svg.startswith("<svg") and "NaN" not in svg and cap
    for focus in learning.FOCUS:
        for i in range(14):
            kind, svg, cap = learning.page_art(i, 2, focus)
            assert svg.startswith("<svg") and "NaN" not in svg and cap


def test_activity_book_has_answer_pages_and_learning_workbook_is_niche_free():
    res = generate(Request("nurse", "activity_book", providers=["builtin"], seed=2, sizes=["letter"], with_video=False, with_images=False,
                           options={"no_research": True, "pages": 12, "level": "toddler"}))
    assert not [c for c in res.checks if c.status == "fail"]
    pdf = next((res.folder / "product").glob("*-letter.pdf"))
    mazes = 3   # pages 0, 4 and 10 of the plan are mazes
    assert pdf_page_count(pdf) == 1 + 12 + -(-mazes // 4)   # cover + pages + one answer page
    res2 = generate(Request("nurse", "learning_workbook", providers=["builtin"], seed=2, sizes=["letter"], with_video=False, with_images=False,
                            options={"no_research": True, "pages": 10, "focus": "numbers"}))
    assert not [c for c in res2.checks if c.status == "fail"] and "nurse" not in (res2.folder / "listing" / "etsy-description.txt").read_text().lower()


def test_every_special_coloring_style_draws_and_books_walk_through_them():
    from moneyhub import coloring
    for name, fn in coloring.SPECIALS:
        svg = fn(3)
        assert svg.startswith("<svg") and "NaN" not in svg and len(svg) > 500, name
    seen = {coloring.page_art(i, 4, PALETTES[0])[0] for i in range(60)}
    assert "special" in seen
    from moneyhub.coloring import SPECIALS
    assert len(SPECIALS) >= 7


def test_character_clipart_has_png_svg_licence_and_commercial_terms():
    res = generate(Request("nurse", "character_clipart", providers=["builtin"], seed=3, with_video=False, with_images=False,
                           options={"no_research": True, "theme": "farm", "count": 12}))
    assert not [c for c in res.checks if c.status == "fail"]
    assert res.title == "Farm Friends Clipart Bundle"
    names = {p.name for p in (res.folder / "product").glob("*")}
    assert "Commercial-License.pdf" in names and any(n.endswith("-SVG.zip") for n in names)
    z = zipfile.ZipFile(next((res.folder / "product").glob("*-PNG*.zip")))
    pngs = [n for n in z.namelist() if n.endswith(".png")]
    assert len(pngs) == 12
    from PIL import Image
    import io
    im = Image.open(io.BytesIO(z.read(pngs[0])))
    assert im.size == (2400, 2400) and im.mode == "RGBA" and im.getchannel("A").getextrema()[0] == 0
    text = (res.folder / "listing" / "etsy-description.txt").read_text().lower()
    assert "commercial use" in text and "nurse" not in text


# ------------------------------------------------------------------ open-source icon sets: licence guard, importer, icon stickers
def _fake_icons():
    return {f"{n}.svg": f"<!-- c --><svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor'><path stroke='none' d='M0 0h24v24H0z' fill='none'/><circle cx='12' cy='12' r='{4 + i % 5}'/><path d='M4 20l16 -16'/></svg>"
            for i, n in enumerate(["heart", "heart-off", "star", "home", "sun", "moon", "book", "cup", "bell", "pin", "key", "map", "mail", "tag", "cart", "gift"])}


def test_icon_licence_guard_and_importer_refuse_unsafe_input():
    from moneyhub import svgassets
    for bad in ("CC-BY-SA-4.0", "CC-BY-NC-4.0", "GPL-3.0", "Unknown-1.0"):
        with pytest.raises(ValueError):
            svgassets.install("x", "x", bad, "u", _fake_icons())
    assert svgassets.clean_svg("<svg><script>alert(1)</script></svg>") is None
    assert svgassets.clean_svg("<svg><image href='http://x/y.png'/></svg>") is None
    assert svgassets.clean_svg("<svg><circle cx='1' cy='1' r='1' onclick='x()'/></svg>") is None
    assert svgassets.clean_svg("<svg viewBox='0 0 24 24'><path stroke='none' d='M0 0h24v24H0z'/><circle cx='1' cy='1' r='1'/></svg>") == "<circle cx='1' cy='1' r='1'/>"
    with pytest.raises(ValueError):
        svgassets.load("not-installed")


def test_icon_pack_builds_with_licence_notice_and_prefers_base_icons():
    from moneyhub import svgassets
    svgassets.install("tiny", "Tiny Icons", "MIT", "https://example.org/tiny", _fake_icons(), "MIT License\nCopyright (c) Test\n", "1.0")
    res = generate(Request("x", "icon_pack", providers=["builtin"], seed=2, sizes=["letter"], with_video=False, with_images=False,
                           options={"no_research": True, "collection": "tiny", "count": 12}))
    assert not [c for c in res.checks if c.status == "fail"]
    z = zipfile.ZipFile(next((res.folder / "product").glob("*PNG-and-SVG.zip")))
    names = z.namelist()
    assert "LICENSES.txt" in names and "MIT License" in z.read("LICENSES.txt").decode() and "Tiny Icons" in z.read("LICENSES.txt").decode()
    assert len([n for n in names if n.startswith("png/")]) == 12 and "png/heart-off.png" not in names   # the "-off" variant is last in line
    assert "MIT" in (res.folder / "listing" / "etsy-description.txt").read_text()
