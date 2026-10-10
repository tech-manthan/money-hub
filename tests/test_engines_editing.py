import json
import shutil
import zipfile
from pathlib import Path
from xml.dom import minidom

import pytest
from PIL import Image

from moneyhub.design import choose_style
from moneyhub.pipeline import Request, generate
from moneyhub.render import graphics as g
from moneyhub.render import motion

DOCS = Path(__file__).resolve().parents[1] / "docs"


def _plan():
    return motion.builtin_plan("T", "S", ["a - b", "c", "d", "e"], "Hook")


def test_engine_chain_falls_back_to_pillow_when_others_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(motion.ENGINES["manim"], "available", lambda: False)
    calls = []
    monkeypatch.setattr(motion.ENGINES["pillow"], "render", lambda *a, **k: calls.append("pillow") or Path("x.mp4"))
    monkeypatch.setattr(motion.ENGINES["pillow"], "available", lambda: True)
    out = motion.render_video(_plan(), [Image.new("RGB", (10, 10))], g.Brush(choose_style(seed=1)), tmp_path / "o.mp4", engines=["manim", "nope", "pillow"])
    assert calls == ["pillow"] and out == Path("x.mp4")


def test_engine_failure_falls_through(tmp_path, monkeypatch):
    class Boom(motion.MotionEngine):
        name = "boom"
        def available(self): return True
        def render(self, *a, **k): raise RuntimeError("x")
    monkeypatch.setitem(motion.ENGINES, "boom", Boom())
    monkeypatch.setattr(motion.ENGINES["pillow"], "render", lambda *a, **k: Path("ok.mp4"))
    monkeypatch.setattr(motion.ENGINES["pillow"], "available", lambda: True)
    assert motion.render_video(_plan(), [Image.new("RGB", (10, 10))], g.Brush(choose_style(seed=1)), tmp_path / "o.mp4", engines=["boom", "pillow"]) == Path("ok.mp4")


def test_engine_assets_contain_pages_palette_and_fonts(tmp_path):
    brush = g.Brush(choose_style(seed=2))
    props = motion._engine_assets(_plan(), [Image.new("RGB", (50, 80))], brush, (1000, 1500), "T", 24, tmp_path)
    assert props["pages"] == ["page-0.png"] and (tmp_path / "page-0.png").exists()
    assert props["palette"]["accent"].startswith("#") and props["fontFiles"] and all(Path(p).exists() for p in props["fontPaths"])


@pytest.mark.skipif(not motion.ENGINES["remotion"].available(), reason="run `moneyhub engines install remotion`")
def test_remotion_engine_renders(tmp_path):
    out = motion.ENGINES["remotion"].render(_plan(), [Image.new("RGB", (400, 500), "white")], g.Brush(choose_style(seed=2)),
                                            tmp_path / "r.mp4", (500, 750), "T", 12)
    assert out and out.stat().st_size > 5_000


@pytest.mark.skipif(not motion.ENGINES["manim"].available(), reason="manim not installed")
def test_manim_engine_renders(tmp_path):
    out = motion.ENGINES["manim"].render(_plan(), [Image.new("RGB", (400, 500), "white")], g.Brush(choose_style(seed=2)),
                                         tmp_path / "m.mp4", (500, 750), "T", 12)
    assert out and out.stat().st_size > 5_000


@pytest.fixture(scope="module")
def wall():
    import os, tempfile
    os.environ["MONEYHUB_OUT"] = tempfile.mkdtemp()
    return generate(Request("gardening", "wall_art", sizes=["4x5"], providers=["builtin"], seed=6, with_video=False))


def test_editable_export_is_valid_layered_svg(wall):
    from moneyhub.editable import export_editable
    out = export_editable(wall.folder, wall.product_id)
    svgs = sorted(out.glob("*/*.svg"))
    assert len(svgs) >= 6 + 1 + 6
    for f in svgs:
        doc = minidom.parseString(f.read_text())
        assert doc.documentElement.tagName == "svg"
    pin = (out / "pins" / "pin-01.svg").read_text()
    assert "<text" in pin and 'id="headline"' in pin and "data:image/png;base64" in pin   # live text + image layers
    assert "Palette" in (out / "BRIEF.md").read_text() and list((out / "fonts").glob("*.ttf"))


def test_poster_motif_is_split_into_one_layer_per_art_piece():
    from moneyhub.editable import MAX_MOTIF_LAYERS, _split_motif, poster_svg
    parts = _split_motif("<circle cx='5' cy='5' r='3' fill='#f00'/><path d='M0 0 L9 9' stroke='#000'/><rect width='4' height='4'/>")
    assert len(parts) == 3 and parts[0].startswith("<circle") and "xmlns" not in parts[0]
    assert _split_motif("<circle r='3'/>") == []                                           # one shape stays one group
    assert _split_motif("<defs><linearGradient id='a'/></defs><rect fill='url(#a)'/><rect/>") == []   # shared definitions: keep together
    assert _split_motif("".join("<circle r='1'/>" for _ in range(MAX_MOTIF_LAYERS + 1))) == []
    assert _split_motif("<circle") == []
    one = {"svg": "<svg viewBox='0 0 1000 1000'><circle r='3'/></svg>", "fg": "#111", "bg": "#fff", "fs": 6, "text": "Hi", "text_top": 70, "small": "",
           "b": {"frame": False, "motif": {"l": 10, "t": 10, "w": 80, "h": 50}, "rule": None, "margin": 8, "align": "center", "small": None}}
    assert 'id="Motif"' in poster_svg(one, "#111") and 'id="motif"' not in poster_svg(one, "#111")   # a single shape keeps one, consistently named, layer
    d = {"svg": "<svg viewBox='0 0 1000 1000'><circle cx='5' cy='5' r='3'/><path d='M0 0 L9 9'/></svg>", "fg": "#111", "bg": "#fff", "fs": 6,
         "text": "Hello there", "text_top": 70, "small": "",
         "b": {"frame": False, "motif": {"l": 10, "t": 10, "w": 80, "h": 50}, "rule": None, "margin": 8, "align": "center", "small": None}}
    svg = minidom.parseString(poster_svg(d, "#111")).documentElement
    ids = [n.getAttribute("id") for n in svg.childNodes if n.nodeType == n.ELEMENT_NODE]
    assert ids[:3] == ["Background", "Motif-1", "Motif-2"] and "Quote" in ids


def test_every_top_level_poster_object_is_a_layer_group():
    from moneyhub.editable import poster_svg
    d = {"svg": "<svg viewBox='0 0 1000 1000'><circle r='3'/><path d='M0 0 L9 9'/></svg>", "fg": "#111", "bg": "#fff", "fs": 6,
         "text": "Hello there", "text_top": 70, "small": "by me",
         "b": {"frame": True, "motif": {"l": 10, "t": 10, "w": 80, "h": 50}, "rule": 60, "margin": 8, "align": "center", "small": 5}}
    root = minidom.parseString(poster_svg(d, "#111", heading="Poppins", script="Caveat")).documentElement
    top = [n for n in root.childNodes if n.nodeType == n.ELEMENT_NODE]
    assert top and all(n.tagName == "g" for n in top), [n.tagName for n in top]   # nothing loose at the top level
    ids = [n.getAttribute("id") for n in top]
    assert ids[0] == "Background" and "Frame" in ids and "Rule" in ids and "Quote" in ids and "Small-Text" in ids
    assert sum(i.startswith("Motif-") for i in ids) == 2


def test_poster_text_uses_the_style_fonts_not_a_generic_family():
    from moneyhub.editable import poster_svg
    d = {"svg": "<svg viewBox='0 0 1000 1000'><circle r='3'/><path d='M0 0 L9 9'/></svg>", "fg": "#111", "bg": "#fff", "fs": 6,
         "text": "Hello there", "text_top": 70, "small": "by me",
         "b": {"frame": False, "motif": {"l": 10, "t": 10, "w": 80, "h": 50}, "rule": None, "margin": 8, "align": "center", "small": 5}}
    svg = poster_svg(d, "#111", heading="Poppins", script="Caveat")
    assert 'id="quote"' in svg and 'font-family="Poppins"' in svg and 'font-family="Caveat"' in svg and "sans-serif" not in svg
    assert 'font-family="sans-serif"' in poster_svg(d, "#111")   # without fonts it stays generic


def test_every_named_object_is_its_own_layer_group(wall):
    """So design apps and PSD export get one layer per object instead of one flat layer."""
    from moneyhub.editable import export_editable
    out = export_editable(wall.folder, wall.product_id)
    pin = minidom.parseString((out / "pins" / "pin-01.svg").read_text()).documentElement
    top = [n for n in pin.childNodes if n.nodeType == n.ELEMENT_NODE]
    groups = [n for n in top if n.tagName == "g"]
    assert len(groups) >= 6
    for gp in groups:   # each group holds exactly the object it names, with its id unchanged
        inner = [n for n in gp.childNodes if n.nodeType == n.ELEMENT_NODE]
        assert len(inner) == 1 and gp.getAttribute("id") == inner[0].getAttribute("id").title()
    assert any(g.getAttribute("id") == "Headline" for g in groups)


def test_import_edits_replaces_images_backs_up_and_rebuilds_zip(wall, tmp_path):
    from moneyhub.editable import export_editable, import_edits
    export_editable(wall.folder, wall.product_id)
    src = tmp_path / "edited"
    src.mkdir()
    Image.new("RGB", (500, 750), (250, 0, 0)).save(src / "pin-01.png")        # wrong size on purpose
    Image.new("RGB", (900, 675), (0, 250, 0)).save(src / "01-hero.jpg")
    Image.new("RGB", (100, 100)).save(src / "unrelated.png")
    done = import_edits(wall.folder, src)
    assert sorted(a for a, _ in done) == ["01-hero.jpg", "pin-01.png"]
    pin = next((wall.folder / "images" / "pinterest").glob("pin-01-*.png"))
    assert Image.open(pin).size == (1000, 1500) and Image.open(pin).getpixel((5, 5))[0] > 200
    assert any((wall.folder / "images" / "_original").iterdir())
    with zipfile.ZipFile(wall.folder / "upload-package.zip") as z:
        assert any(n.startswith("images/pinterest/pin-01") for n in z.namelist())


def test_cli_edit_commands_registered():
    from typer.testing import CliRunner
    from moneyhub.cli import app
    r = CliRunner().invoke(app, ["edit", "--help"])
    assert r.exit_code == 0 and "export" in r.output and "import" in r.output
    assert "install" in CliRunner().invoke(app, ["engines", "--help"]).output


def test_licence_notes_record_what_was_checked():
    lines = (DOCS / "licenses.md").read_text().splitlines()
    row = lambda key: next(l for l in lines if key in l)  # noqa: E731
    assert "MIT" in row("mohanrex") and "GPL" in row("georgiastuart")
    text = "\n".join(lines)
    assert "Remotion" in text and "MPL-2.0" in text and "no code" in text.lower()
