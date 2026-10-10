import json
import stat
import struct
import zipfile
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from moneyhub import craftbuild, crafttools
from moneyhub.cli import app
from moneyhub.pipeline import Request, generate


# ------------------------------------------------------------------------------------------------ stand-ins
def make_psd(path: Path, names: list[str]) -> None:
    """A tiny but structurally valid PSD whose layer table lists `names` (enough for the layer reader)."""
    head = b"8BPS" + struct.pack(">H", 1) + b"\0" * 6 + struct.pack(">HIIHH", 3, 8, 8, 8, 3)
    recs = b""
    for n in names:
        nm = n.encode()
        pascal = bytes([len(nm)]) + nm
        pascal += b"\0" * ((-len(pascal)) % 4)
        extra = struct.pack(">I", 0) + struct.pack(">I", 0) + pascal
        recs += struct.pack(">iiiiH", 0, 0, 8, 8, 0) + b"8BIM" + b"norm" + bytes([255, 0, 0, 0]) + struct.pack(">I", len(extra)) + extra
    layer_info = struct.pack(">h", len(names)) + recs
    layer_info += b"\0" * ((-len(layer_info)) % 2)
    layer_section = struct.pack(">I", len(layer_info)) + layer_info
    body = struct.pack(">I", 0) + struct.pack(">I", 0) + struct.pack(">I", len(layer_section) + 4) + layer_section + struct.pack(">I", 0)
    path.write_bytes(head + body + b"\0" * 300)


def make_pdf(path: Path, colour="white", size=(300, 400)) -> None:
    Image.new("RGB", size, colour).save(path, "PDF")


def fake(base: Path, name: str, body: str) -> None:
    d = base / name / "current" / f"{name}-cli-1.0-macos-universal"
    d.mkdir(parents=True, exist_ok=True)
    exe = d / f"{name}-cli"
    exe.write_text("#!/bin/bash\n" + body)
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def tools(tmp_path, monkeypatch):
    """Stand-in vectorcraft, gridcraft and pdfcraft that write plausible, valid files."""
    base = tmp_path / "craft"
    assets = tmp_path / "assets"
    assets.mkdir()
    make_psd(assets / "good.psd", ["background", "headline", "art"])
    make_psd(assets / "flat.psd", ["Layer 1"])
    make_pdf(assets / "page.pdf")
    make_pdf(assets / "other.pdf", colour="black", size=(300, 400))
    (assets / "pic.eps").write_bytes(b"%!PS-Adobe-3.0 EPSF-3.0\n" + b"% padding\n" * 40)
    monkeypatch.setenv("MONEYHUB_CRAFT_DIR", str(base))
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    fake(base, "vectorcraft", f'''out="$3"; ext="${{out##*.}}"
case "$ext" in
  psd) cp "${{VC_PSD:-{assets}/good.psd}}" "$out";;
  pdf|ai) cp {assets}/page.pdf "$out";;
  eps) cp {assets}/pic.eps "$out";;
esac
echo '{{"format":"'$ext'","warnings":["fonts missing: Foo"]}}'
''')
    fake(base, "gridcraft", 'out="$3"; case "$out" in *.csv) printf "a,b\\n1,2\\n3,4\\n" > "$out";; *.html) printf "<html><table><tr><td>1</td></tr></table></html>" > "$out";; esac\n')
    fake(base, "pdfcraft", f'''if [ "$1" = edit ]; then
  out=""; while [ $# -gt 0 ]; do [ "$1" = "--out" ] && out="$2"; shift; done
  cp "${{PC_SOURCE:-{assets}/page.pdf}}" "$out"
fi
''')
    return assets


def settings(monkeypatch, **over):
    cfg = {"enabled": True, "verify_after_make": False, "timeout": 30, "tools": {},
           "outputs": {"vectors": True, "sheets": True, "pdfs": True, "after_make": False}}
    for k, v in over.items():
        cfg[k] = {**cfg[k], **v} if isinstance(v, dict) else v

    def get(key, default=None):
        cur = cfg
        for part in key.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur
    monkeypatch.setattr(crafttools, "_cfg", get)


def wall(seed=3):
    return generate(Request("x", "wall_art", providers=["builtin"], seed=seed, sizes=["4x5"], with_images=False, with_video=False,
                            options={"no_research": True}))


# ------------------------------------------------------------------------------------------------ tests
def test_psd_layer_reader_reads_names_and_rejects_other_files(tmp_path):
    p = tmp_path / "a.psd"
    make_psd(p, ["background", "headline", "page-1"])
    assert craftbuild.psd_layers(p) == ["background", "headline", "page-1"]
    (tmp_path / "b.psd").write_bytes(b"not a psd")
    assert craftbuild.psd_layers(tmp_path / "b.psd") == [] and craftbuild.psd_layers(tmp_path / "missing.psd") == []


def test_everything_off_builds_nothing_and_changes_nothing(tools, monkeypatch):
    settings(monkeypatch, enabled=False)
    res = wall()
    assert craftbuild.build(res.folder) == [] and craftbuild.after_make(res.folder) is None
    assert not (res.folder / "product" / craftbuild.FOLDER).exists() and not (res.folder / "craft-build.json").exists()
    assert not any("Editable-files" in n for n in zipfile.ZipFile(res.folder / "upload-package.zip").namelist())
    settings(monkeypatch, outputs={"vectors": False, "sheets": False, "pdfs": False})   # master on, no kind chosen
    assert craftbuild.build(res.folder) == []


def test_vectors_are_built_checked_and_packaged(tools, monkeypatch):
    settings(monkeypatch)
    res = wall()
    rows = craftbuild.build(res.folder, kinds=["vectors"])
    assert rows and all(r["ok"] for r in rows), rows
    d = res.folder / "product" / craftbuild.FOLDER / "vector"
    for ext in ("svg", "ai", "eps", "pdf", "psd"):
        assert (d / f"design-01.{ext}").exists(), ext
    psd_row = next(r for r in rows if r["file"] == "design-01.psd")
    assert "3 layers" in psd_row["detail"] and "fonts missing" in psd_row["warn"]
    assert "design-01.psd" in (res.folder / "product" / craftbuild.FOLDER / "README.txt").read_text() or "vector/" in (
        res.folder / "product" / craftbuild.FOLDER / "README.txt").read_text()
    report = json.loads((res.folder / "craft-build.json").read_text())
    assert len(report["files"]) == len(rows)
    names = zipfile.ZipFile(res.folder / "upload-package.zip").namelist()
    assert any(n.endswith("Editable-files/vector/design-01.psd") for n in names)


def test_old_editable_files_are_re_exported_before_converting(tools, monkeypatch):
    """Editable posters made before layers and real fonts existed are rebuilt, so the PSD gets its layers."""
    settings(monkeypatch)
    res = wall()
    from moneyhub.editable import export_editable
    export_editable(res.folder, res.product_id)
    svg = res.folder / "editable" / "posters" / "design-01.svg"
    text = svg.read_text()
    assert 'id="Background"' in text and 'font-family="sans-serif"' not in text
    svg.write_text(text.replace('id="Background"', 'id="background"').replace("<svg ", "<svg data-old='1' ", 1))   # pretend it is an old file
    rows = craftbuild.build(res.folder, kinds=["vectors"])
    assert rows and all(r["ok"] for r in rows)
    assert 'data-old' not in svg.read_text() and 'id="Background"' in svg.read_text()
    assert not any(" " in r["detail"] and r["detail"].startswith("{") for r in rows)   # no raw JSON in the report
    side = svg.with_suffix(".text.json")
    assert side.exists()
    side.unlink()   # editable files from before the live-text step are rebuilt too
    craftbuild.build(res.folder, kinds=["vectors"])
    assert side.exists()
    assert craftbuild._short("fonts that aren't available were written in the fallback font, Source Sans 3: DMSans, Poppins (install them)") == \
        "fonts not installed: DMSans, Poppins"


def test_a_flat_psd_is_rejected_and_removed(tools, monkeypatch):
    settings(monkeypatch)
    monkeypatch.setenv("VC_PSD", str(tools / "flat.psd"))
    res = wall()
    rows = craftbuild.build(res.folder, kinds=["vectors"])
    bad = [r for r in rows if r["file"].endswith(".psd")]
    assert bad and not any(r["ok"] for r in bad)
    assert not list((res.folder / "product" / craftbuild.FOLDER / "vector").glob("*.psd"))
    assert any(r["ok"] for r in rows if r["file"].endswith(".pdf"))   # the good formats are kept


def test_pdf_metadata_replaces_only_when_the_file_is_unchanged(tools, monkeypatch):
    settings(monkeypatch)
    res = wall()
    pdf = next(p for p in (res.folder / "product").glob("*.pdf") if not p.name.startswith("00-")) if list(
        p for p in (res.folder / "product").glob("*.pdf") if not p.name.startswith("00-")) else None
    if pdf is None:   # wall art ships zips; use a product that has a PDF
        res = generate(Request("x", "card_deck", providers=["builtin"], seed=3, sizes=["letter"], with_images=False, with_video=False,
                               options={"no_research": True}))
        pdf = next(p for p in (res.folder / "product").glob("*.pdf") if not p.name.startswith("00-"))
    pages = craftbuild._pdf_pages(pdf)
    monkeypatch.setenv("PC_SOURCE", str(tools / "other.pdf"))   # a result that looks different: must be refused
    rows = craftbuild.build(res.folder, kinds=["pdfs"])
    assert rows and not rows[0]["ok"] and craftbuild._pdf_pages(pdf) == pages
    assert not list((res.folder / "product").glob("*.meta.pdf"))   # no leftovers


def test_sheets_write_csv_and_html(tools, monkeypatch):
    settings(monkeypatch)
    res = generate(Request("x", "budget_tracker", providers=["builtin"], seed=3, sizes=["letter"], with_images=False, with_video=False,
                           options={"no_research": True}))
    rows = craftbuild.build(res.folder, kinds=["sheets"])
    assert {r["file"].rsplit(".", 1)[1] for r in rows if r["ok"]} == {"csv", "html"}
    d = res.folder / "product" / craftbuild.FOLDER / "sheets"
    assert next(d.glob("*.csv")).read_text().startswith("a,b")


def test_after_make_adds_a_warn_only_line_and_survives_a_broken_tool(tools, monkeypatch):
    settings(monkeypatch, outputs={"after_make": True, "sheets": False, "pdfs": False})
    res = wall()   # generated while the switch is on: the pipeline hook builds the files
    assert (res.folder / "product" / craftbuild.FOLDER / "vector" / "design-01.pdf").exists()
    line = [c for c in res.checks if c.name.startswith("Editable formats")]
    assert line and line[0].status in ("pass", "warn") and res.qa_status != "fail"
    fake(Path(crafttools.tools_dir()), "vectorcraft", "exit 7\n")   # a tool that always fails
    res2 = wall(seed=4)
    assert res2.qa_status != "fail"
    assert not list((res2.folder / "product").glob(f"{craftbuild.FOLDER}/vector/*.psd"))


def test_settings_cli_and_export_command(tools, monkeypatch, tmp_path):
    from moneyhub import config
    monkeypatch.setenv("MONEYHUB_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    config.reload_config()
    try:
        crafttools.save_settings(True, None, {})
        r = CliRunner().invoke(app, ["tools", "--outputs", "vectors,pdfs", "--outputs-after-make"])
        assert r.exit_code == 0, r.output
        view = craftbuild.outputs_view()
        assert {k["kind"]: k["enabled"] for k in view["kinds"]} == {"vectors": True, "sheets": False, "pdfs": True} and view["after_make"]
        assert CliRunner().invoke(app, ["tools", "--outputs", "bogus"]).exit_code != 0
        with pytest.raises(ValueError):
            craftbuild.save_outputs({"nonsense": True})
    finally:
        monkeypatch.delenv("MONEYHUB_HOME")
        config.reload_config()


def test_export_craft_command_forces_a_build_and_validates_kinds(tools, monkeypatch):
    settings(monkeypatch, enabled=False)   # switches off: an explicit command still works
    res = wall()
    r = CliRunner().invoke(app, ["export", "craft", str(res.product_id), "--kinds", "vectors"])
    assert r.exit_code == 0 and "design-01.psd" in r.output, r.output
    assert CliRunner().invoke(app, ["export", "craft", str(res.product_id), "--kinds", "bogus"]).exit_code != 0
    assert CliRunner().invoke(app, ["export", "craft", "99999"]).exit_code != 0


# ------------------------------------------------------------------------------------------------ live text
def fake_photocraft(tools_dir, assets, layers_after=3, fail=False):
    """Reports Background/Motif-1/Quote as Pixel layers; after `run` the Quote layer is a Type layer (marker bytes TySh appended)."""
    body = f'''if [ "$1" = info ]; then
  if grep -q TySh "$2"; then K=Type; else K=Pixel; fi
  extra=""; [ "{layers_after}" != "3" ] && [ "$K" = Type ] && extra=',{{"id":9,"kind":"Pixel","name":"Extra"}}'
  echo '{{"layers":[{{"id":2,"kind":"Pixel","name":"Background"}},{{"id":3,"kind":"Pixel","name":"Motif-1"}},{{"id":4,"kind":"'$K'","name":"Quote","text":{{"font":"Poppins","text":"x"}}}}'$extra']}}'
  exit 0
fi
if [ "$1" = run ]; then
  {"exit 1" if fail else ""}
  in="$2"; out=""; while [ $# -gt 0 ]; do [ "$1" = "--out" ] && out="$2"; shift; done
  cp "$in" "$out"; printf TySh >> "$out"; echo '{{"command":"type.create"}}'
fi
'''
    fake(tools_dir, "photocraft", body)


def test_poster_text_layers_describe_the_live_text(tmp_path):
    from moneyhub.editable import poster_text_layers
    d = {"svg": "<svg/>", "fg": "#112233", "bg": "#fff", "fs": 6, "text": "Care for others", "text_top": 70, "small": "by me",
         "b": {"frame": False, "motif": None, "rule": None, "margin": 8, "align": "center", "small": 5}}
    q, s = poster_text_layers(d, heading="Poppins", script="Caveat")
    assert q["name"] == "Quote" and q["text"] == "Care for others" and q["align"] == "center" and q["font"] == "Poppins" and q["weight"] == 700
    assert q["color"] == "#112233" and len(q["box"]) == 4 and q["box"][2] == 840 and q["size"] > 10
    assert s["name"] == "Small-Text" and s["font"] == "Caveat"
    d["b"]["align"] = "left"
    assert poster_text_layers(d)[0]["box"][0] == 80   # left aligned: starts at the margin


def test_live_text_replaces_picture_text_only_when_verified(tools, monkeypatch, tmp_path):
    base = Path(crafttools.tools_dir())
    make_psd(tools / "three.psd", ["Background", "Motif-1", "Quote"])
    monkeypatch.setenv("VC_PSD", str(tools / "three.psd"))
    settings(monkeypatch, tools={"photocraft": True})
    fake_photocraft(base, tools)
    res = wall()
    rows = craftbuild.build(res.folder, kinds=["vectors"])
    psd = next(r for r in rows if r["file"] == "design-01.psd")
    assert psd["ok"] and "LIVE TEXT" in psd["detail"] and "Quote (Poppins)" in psd["detail"]
    f = res.folder / "product" / craftbuild.FOLDER / "vector" / "design-01.psd"
    assert f.read_bytes().count(b"TySh") == 1 and craftbuild.psd_layers(f)   # replaced, still a readable PSD with its layers

    # the tool fails: the picture-text PSD is kept and the build still succeeds
    fake_photocraft(base, tools, fail=True)
    rows = craftbuild.build(res.folder, kinds=["vectors"])
    psd = next(r for r in rows if r["file"] == "design-01.psd")
    assert psd["ok"] and "stays as picture" in psd["detail"]
    assert (res.folder / "product" / craftbuild.FOLDER / "vector" / "design-01.psd").read_bytes().count(b"TySh") == 0

    # the result has a different layer count: refused
    fake_photocraft(base, tools, layers_after=4)
    rows = craftbuild.build(res.folder, kinds=["vectors"])
    psd = next(r for r in rows if r["file"] == "design-01.psd")
    assert psd["ok"] and "kept picture text" in psd["detail"]
    assert not list((res.folder / "product" / craftbuild.FOLDER / "vector").glob("*.live.psd"))


def test_live_text_is_skipped_when_photocraft_is_off(tools, monkeypatch):
    base = Path(crafttools.tools_dir())
    make_psd(tools / "three.psd", ["Background", "Motif-1", "Quote"])
    monkeypatch.setenv("VC_PSD", str(tools / "three.psd"))
    settings(monkeypatch, tools={"photocraft": False})
    fake_photocraft(base, tools)
    rows = craftbuild.build(wall().folder, kinds=["vectors"])
    assert rows and all("LIVE TEXT" not in r["detail"] and "stays as picture" not in r["detail"] for r in rows)
