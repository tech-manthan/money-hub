import json
import stat
import zipfile

import pytest
from PIL import Image

from moneyhub import presentations
from moneyhub.design import choose_style
from moneyhub.pipeline import Request, generate

SLIDES = 12


def fake_deckcraft(base, slides=SLIDES, fail=False, no_png=False):
    """A stand-in deckcraft-cli: `run --save` writes a small valid .pptx package, `info` lists the slides, `render --all DIR` writes PNGs."""
    d = base / "deckcraft" / "current" / "deckcraft-cli-0.4.0-macos-universal"
    d.mkdir(parents=True, exist_ok=True)
    exe = d / "deckcraft-cli"
    exe.write_text(f'''#!/usr/bin/env python3
import json, sys, zipfile, os
a = sys.argv[1:]
if a[0] == "run":
    if {fail!r}: sys.exit(1)
    out = a[a.index("--save") + 1]
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("ppt/presentation.xml", "<p/>" + "x" * 3000)
        for i in range({slides}): z.writestr(f"ppt/slides/slide{{i + 1}}.xml", "<s/>")
    print(json.dumps({{"ok": True, "cmds": [x.split("=", 1)[0] for x in a if "=" in x and not x.startswith("/")]}}))
elif a[0] == "info":
    print(json.dumps({{"slides": [{{"index": i}} for i in range({slides})]}}))
elif a[0] == "render":
    from PIL import Image
    d = a[-1]; os.makedirs(d, exist_ok=True)
    if not {no_png!r}:
        for i in range({slides}): Image.new("RGB", (1920, 1080), (40 + i * 10, 90, 70)).save(f"{{d}}/slide-{{i + 1:02d}}.png")
''')
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def tool(tmp_path, monkeypatch):
    monkeypatch.setenv("MONEYHUB_CRAFT_DIR", str(tmp_path / "craft"))
    fake_deckcraft(tmp_path / "craft")
    return tmp_path / "craft"


def test_slide_commands_make_twelve_named_editable_slides_in_the_palette():
    style = choose_style(3, palette="sage")
    cmds, n = presentations.slide_commands(style)
    assert n == SLIDES == [c[0] for c in cmds].count("slide.new")
    text = json.dumps(cmds)
    assert style.palette.accent in text and "Title" in text and "Agenda" in text and "Thank you" in text
    assert all(c[0] != "insert.picture" for c in cmds)           # no embedded art: every object is a text box or a shape
    fams = {p["family"] for c, p in cmds if c == "format.font"}
    assert fams <= {presentations.family(style.fonts.heading), presentations.family(style.fonts.body)}


def test_real_font_family_names_are_used():
    assert presentations.family("DMSans") == "DM Sans" and presentations.family("PlayfairDisplay") == "Playfair Display" and presentations.family("Lora") == "Lora"


def test_build_deck_checks_the_file_and_the_renders(tool, tmp_path):
    ok, n, msg = presentations.build_deck(choose_style(1), tmp_path / "d.pptx", tmp_path / "png")
    assert ok and n == SLIDES and (tmp_path / "d.pptx").exists() and len(list((tmp_path / "png").glob("slide-*.png"))) == SLIDES


def test_build_deck_deletes_a_deck_that_fails_its_checks(tool, tmp_path):
    fake_deckcraft(tool.parent / "craft", slides=5)             # opens, but with the wrong slide count
    ok, n, msg = presentations.build_deck(choose_style(1), tmp_path / "d.pptx", tmp_path / "png")
    assert not ok and "5 slides" in msg and not (tmp_path / "d.pptx").exists()
    fake_deckcraft(tool.parent / "craft", no_png=True)
    assert not presentations.build_deck(choose_style(1), tmp_path / "e.pptx", tmp_path / "png2")[0] and not (tmp_path / "e.pptx").exists()
    fake_deckcraft(tool.parent / "craft", fail=True)
    assert presentations.build_deck(choose_style(1), tmp_path / "f.pptx", tmp_path / "png3")[:2] == (False, 0)


def test_build_deck_without_the_tool_reports_instead_of_raising(tmp_path, monkeypatch):
    monkeypatch.setenv("MONEYHUB_CRAFT_DIR", str(tmp_path / "none"))
    ok, n, msg = presentations.build_deck(choose_style(1), tmp_path / "d.pptx", tmp_path / "png")
    assert not ok and "not installed" in msg


def _make(seed=2, **kw):
    return generate(Request("x", "presentation_template", providers=["builtin"], seed=seed, with_images=kw.pop("with_images", False), with_video=False,
                            options={"no_research": True}))


def test_presentation_template_product_files_listing_and_qa(tool):
    res = _make()
    assert not [c for c in res.checks if c.status == "fail"], [c for c in res.checks if c.status == "fail"]
    names = sorted(p.name for p in (res.folder / "product").iterdir())
    assert any(n.endswith(".pptx") for n in names) and any(n.endswith("-preview.pdf") for n in names) and "Editing-Guide-and-License.pdf" in names
    z = zipfile.ZipFile(next((res.folder / "product").glob("*.pptx")))
    assert "ppt/presentation.xml" in z.namelist()
    desc = (res.folder / "listing" / "etsy-description.txt").read_text()
    assert "(.pptx)" in desc and "classroom" not in desc.lower() and "Presentation Template" in desc
    assert "Which apps" in desc
    assert any(c.name.endswith(": slides") and c.status == "pass" for c in res.checks)


def test_presentation_template_listing_photos_show_the_slides(tool):
    res = _make(seed=4, with_images=True)
    imgs = sorted((res.folder / "images" / "etsy").glob("*.jpg"))
    assert len(imgs) >= 6
    assert all(Image.open(p).size[0] > 800 for p in imgs[:2])


def test_presentation_template_needs_the_tool(tmp_path, monkeypatch):
    monkeypatch.setenv("MONEYHUB_CRAFT_DIR", str(tmp_path / "none"))
    with pytest.raises(Exception) as e:
        _make(seed=6)
    assert "deckcraft" in str(e.value)
