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


def test_every_named_object_is_its_own_layer_group(wall):
    """So design apps and PSD export get one layer per object instead of one flat layer."""
    from moneyhub.editable import export_editable
    out = export_editable(wall.folder, wall.product_id)
    pin = minidom.parseString((out / "pins" / "pin-01.svg").read_text()).documentElement
    top = [n for n in pin.childNodes if n.nodeType == n.ELEMENT_NODE]
    groups = [n for n in top if n.tagName == "g" and n.getAttribute("id").startswith("layer-")]
    assert len(groups) >= 6
    for gp in groups:   # each group holds exactly the object it names, with its id unchanged
        inner = [n for n in gp.childNodes if n.nodeType == n.ELEMENT_NODE]
        assert len(inner) == 1 and gp.getAttribute("id") == "layer-" + inner[0].getAttribute("id")
    assert any(g.getAttribute("id") == "layer-headline" for g in groups)


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
