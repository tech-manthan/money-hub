"""Extra deliverable files built with the craft tools: editable vector and layered Photoshop-style copies of poster designs, CSV and HTML
copies of spreadsheets, and tidy PDF metadata.

Everything here is optional and OFF by default (settings `craft.outputs.*`, plus the master `craft.enabled`). With everything off nothing
is started and no file changes. With a kind on, each file is written to a temporary name, re-opened with the matching tool (and, for
PSD files, its layer table is read), and only then kept. A file that fails its check is deleted and reported. The report is written to
`craft-build.json` in the product folder; the files go to `product/Editable-files/`, which the upload package already includes."""
from __future__ import annotations

import json
import shutil
import struct
import tempfile
from pathlib import Path

from . import crafttools as ct

KINDS = ("vectors", "sheets", "pdfs")
TOOL_FOR = {"vectors": "vectorcraft", "sheets": "gridcraft", "pdfs": "pdfcraft"}
FOLDER = "Editable-files"
VECTOR_FORMATS = ("ai", "eps", "pdf", "psd")

README = """Editable files
==============

{title}

vector/    each poster design as SVG (open in any vector editor) plus AI, EPS, PDF and PSD copies.
           In the SVG, AI, EPS and PDF files the text is live text and every art piece is a separate object.
           The PSD has one layer per object so you can move, hide or replace them. Its text is live, editable
           text when the fonts below are installed (if a file's text is a picture instead, retype it in the SVG,
           AI or PDF version).
sheets/    CSV and HTML copies of the spreadsheet (first sheet) for tools that cannot open .xlsx.

Fonts: the designs use {fonts}. They are free Google Fonts: install them before opening the files, otherwise your
software shows a replacement font.

These copies were converted by a third-party program. Open one in your own software before you rely on it.
"""


# ---------------------------------------------------------------------------------------------------------- settings
def want(kind: str) -> bool:
    """Is this kind switched on in settings (master switch and its own switch), and is its tool installed?"""
    return ct.master_enabled() and bool(ct._cfg(f"outputs.{kind}", False)) and ct.find_tool(TOOL_FOR[kind]) is not None


def outputs_view() -> dict:
    return {"after_make": bool(ct._cfg("outputs.after_make", False)),
            "kinds": [{"kind": k, "tool": TOOL_FOR[k], "enabled": bool(ct._cfg(f"outputs.{k}", False)), "installed": ct.find_tool(TOOL_FOR[k]) is not None}
                      for k in KINDS]}


def save_outputs(kinds: dict[str, bool] | None = None, after_make: bool | None = None) -> dict:
    from .config import save_local_setting
    for k, on in (kinds or {}).items():
        if k not in KINDS:
            raise ValueError(f"unknown output '{k}'. Choose from: {', '.join(KINDS)}")
        save_local_setting(f"craft.outputs.{k}", bool(on))
    if after_make is not None:
        save_local_setting("craft.outputs.after_make", bool(after_make))
    return outputs_view()


# ---------------------------------------------------------------------------------------------------------- file checks
def psd_layers(path: Path) -> list[str]:
    """Names of the layers in a PSD file (empty list when it is not a readable PSD or has none)."""
    try:
        b = Path(path).read_bytes()
        if b[:4] != b"8BPS":
            return []
        pos = 26
        pos += 4 + struct.unpack(">I", b[pos:pos + 4])[0]     # colour mode data
        pos += 4 + struct.unpack(">I", b[pos:pos + 4])[0]     # image resources
        if struct.unpack(">I", b[pos:pos + 4])[0] == 0:
            return []
        pos += 4
        if struct.unpack(">I", b[pos:pos + 4])[0] == 0:
            return []
        pos += 4
        count = abs(struct.unpack(">h", b[pos:pos + 2])[0])
        pos += 2
        names = []
        for _ in range(count):
            ch = struct.unpack(">H", b[pos + 16:pos + 18])[0]
            pos += 18 + 6 * ch + 8 + 4
            extra = struct.unpack(">I", b[pos:pos + 4])[0]
            pos += 4
            e = b[pos:pos + extra]
            pos += extra
            k = 4 + struct.unpack(">I", e[:4])[0]
            k += 4 + struct.unpack(">I", e[k:k + 4])[0]
            name = e[k + 1:k + 1 + e[k]].decode("latin1")
            i = e.find(b"luni")
            if i > 0:
                n = struct.unpack(">I", e[i + 8:i + 12])[0]
                name = e[i + 12:i + 12 + 2 * n].decode("utf-16-be", errors="replace")
            names.append(name)
        return names
    except (OSError, struct.error, IndexError):
        return []


def _pdf_pages(path: Path) -> int:
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(str(path))
        try:
            return len(doc)
        finally:
            doc.close()
    except Exception:   # noqa: BLE001
        return 0


def _first_page_diff(a: Path, b: Path) -> float:
    """Mean absolute pixel difference (0-255) between page 1 of two PDFs; large when either cannot be rendered."""
    try:
        import numpy as np
        from PIL import Image

        from .render.raster import render_pages
        ia, ib = render_pages(a, [0], 0.4)[0], render_pages(b, [0], 0.4)[0]
        if ia.size != ib.size:
            return 255.0
        return float(np.abs(np.asarray(ia.convert("L"), dtype=np.int16) - np.asarray(ib.convert("L"), dtype=np.int16)).mean())
    except Exception:   # noqa: BLE001
        return 255.0


def _fonts_in(svgs: list[Path]) -> list[str]:
    import re
    found: set[str] = set()
    for s in svgs:
        try:
            found |= {m for m in re.findall(r'font-family="([^"]+)"', s.read_text(encoding="utf-8")) if m.lower() not in ("sans-serif", "serif")}
        except OSError:
            pass
    return sorted(found)


def _short(warn: str) -> str:
    """Shorten converter warnings for display: font notes become 'missing fonts: A, B'; other warnings are kept (trimmed)."""
    import re
    out, fonts = [], []
    for w in [x.strip() for x in warn.split(";") if x.strip()]:
        m = re.search(r"fallback font[^:]*:\s*(.+?)(?:\s*\(|$)", w)
        if m:
            fonts += [f.strip() for f in m.group(1).split(",") if f.strip()]
        else:
            out.append(w.split(":")[0].strip())
    if fonts:
        out.append("fonts not installed: " + ", ".join(dict.fromkeys(fonts)))
    return "; ".join(out)


def _row(kind: str, tool: str, file: str, ok: bool, detail: str = "", warn: str = "") -> dict:
    return {"kind": kind, "tool": tool, "file": file, "ok": ok, "detail": detail[:300], "warn": warn[:300]}


def _convert(tool: str, src: Path, dst: Path, extra: list[str] | None = None, timeout: float = 120.0, min_bytes: int = 200):
    """Run `<tool>-cli convert src dst`. Returns (ok, warnings, message). Never raises."""
    r = ct.run(tool, ["convert", str(src), str(dst), *(extra or [])], timeout)
    warnings = ""
    try:
        data = json.loads(r.out.strip().splitlines()[-1]) if r.out.strip() else {}
        warnings = "; ".join(data.get("warnings") or [])
    except (ValueError, AttributeError, IndexError):
        pass
    return r.ok and dst.exists() and dst.stat().st_size >= min_bytes, warnings, (r.err or r.out).strip().replace("\n", " ")


# ---------------------------------------------------------------------------------------------------------- the builders
def live_text(psd: Path, sidecar: Path, timeout: float) -> tuple[bool, str]:
    """Replace the picture layers for the poster's text with real text layers (photocraft). The PSD is only replaced when the new file has the
    same number of layers, every replaced text is a Type layer, and live text blocks exist; otherwise the original stays."""
    try:
        specs = json.loads(sidecar.read_text(encoding="utf-8"))
        r = ct.run("photocraft", ["info", str(psd), "--compact"], timeout)
        layers = {l["name"]: l for l in json.loads(r.out).get("layers", [])} if r.ok else {}
        todo = [s for s in specs if s["name"] in layers and layers[s["name"]].get("kind") == "Pixel"]
        if not todo:
            return False, "no text layers to replace"
        before = len(layers)
        args = ["run", str(psd)]
        for s in todo:
            args += ["--cmd", "layer.delete", "--params", json.dumps({"layer": layers[s["name"]]["id"]}),
                     "--cmd", "type.create", "--params", json.dumps({k: s[k] for k in ("text", "box", "name", "align", "font", "weight", "size", "color")})]
        tmp = psd.with_suffix(".live.psd")
        r = ct.run("photocraft", [*args, "--out", str(tmp)], timeout)
        if not (r.ok and tmp.exists()):
            tmp.unlink(missing_ok=True)
            return False, (r.err or r.out).strip()[:120]
        r2 = ct.run("photocraft", ["info", str(tmp), "--compact"], timeout)
        new = json.loads(r2.out).get("layers", []) if r2.ok else []
        types = [l for l in new if l.get("kind") == "Type"]
        ok = len(new) == before and len(types) == len(todo) and tmp.read_bytes().count(b"TySh") >= len(todo)
        if ok:
            tmp.replace(psd)
            return True, f"{len(types)} live text layer(s): " + ", ".join(f"{l['name']} ({l.get('text', {}).get('font', '?')})" for l in types)
        tmp.unlink(missing_ok=True)
        return False, f"kept picture text ({len(new)} layers, {len(types)} text layers, expected {before} and {len(todo)})"
    except Exception as e:   # noqa: BLE001
        return False, f"kept picture text ({e})"[:140]


def build_vectors(folder: Path, pid: int | None, out: Path, timeout: float, text: bool = False) -> list[dict]:
    rows: list[dict] = []
    ed = folder / "editable" / "posters"
    first = next(iter(sorted(ed.glob("*.svg"))), None) if ed.exists() else None
    old = first.read_text(encoding="utf-8", errors="ignore") if first else ""
    stale = (first is None or 'id="Background"' not in old or 'font-family="sans-serif"' in old   # made before layers, names and real fonts
             or not first.with_suffix(".text.json").exists() or 'id="motif"' in old)               # or before the live-text layer files
    if stale:
        try:
            from .editable import export_editable
            export_editable(folder, pid)
        except Exception as e:   # noqa: BLE001
            return [_row("vectors", "vectorcraft", "-", False, f"could not prepare the editable designs: {e}")]
    svgs = sorted(ed.glob("*.svg"))
    if not svgs:
        return []
    dest = out / "vector"
    dest.mkdir(parents=True, exist_ok=True)
    for svg in svgs:
        shutil.copy(svg, dest / svg.name)
        for fmt in VECTOR_FORMATS:
            target = dest / f"{svg.stem}.{fmt}"
            ok, warn, msg = _convert("vectorcraft", svg, target, timeout=timeout)
            detail = ""
            if ok and fmt in ("pdf", "ai"):
                n = _pdf_pages(target)
                ok, detail = n == 1, f"{n} page(s)"
            elif ok and fmt == "psd":
                names = psd_layers(target)
                ok, detail = len(names) >= 2, f"{len(names)} layers: {', '.join(names[:6])}"
                if ok and text and svg.with_suffix(".text.json").exists():
                    done, note = live_text(target, svg.with_suffix(".text.json"), timeout)
                    detail += f"; {'LIVE TEXT: ' if done else 'text stays as picture: '}{note}"
            elif ok and fmt == "eps":
                head = target.read_bytes()[:4]
                ok, detail = head[:2] == b"%!" or head == b"\xc5\xd0\xd3\xc6", f"{target.stat().st_size // 1024} KB"
            if not ok:
                target.unlink(missing_ok=True)
            rows.append(_row("vectors", "vectorcraft", target.name, ok, detail or ("" if ok else msg), _short(warn)))
    return rows


def build_sheets(folder: Path, out: Path, timeout: float) -> list[dict]:
    rows: list[dict] = []
    for xlsx in sorted((folder / "product").glob("*.xlsx")):
        dest = out / "sheets"
        dest.mkdir(parents=True, exist_ok=True)
        for ext in ("csv", "html"):
            target = dest / f"{xlsx.stem}.{ext}"
            ok, warn, msg = _convert("gridcraft", xlsx, target, timeout=timeout, min_bytes=5)
            if not ok:
                target.unlink(missing_ok=True)
            rows.append(_row("sheets", "gridcraft", target.name, ok, msg if not ok else f"{target.stat().st_size} bytes", warn))
    return rows


def build_pdfs(folder: Path, spec: dict, timeout: float) -> list[dict]:
    """Title and author metadata on the product PDFs. Each file is only replaced when the new one has the same page count and page 1
    looks the same; otherwise the original stays."""
    from .config import get_config
    rows: list[dict] = []
    title = (spec.get("content") or {}).get("title", "")
    author = str(get_config().get("shop.name") or "").strip()
    if not title:
        return rows
    for pdf in sorted((folder / "product").glob("*.pdf")):
        if pdf.name.startswith("00-"):
            continue
        tmp = pdf.with_suffix(".meta.pdf")
        args = ["edit", str(pdf), "--out", str(tmp), "--title", title] + (["--author", author] if author else [])
        r = ct.run("pdfcraft", args, timeout)
        ok = r.ok and tmp.exists() and _pdf_pages(tmp) == _pdf_pages(pdf) > 0
        diff = _first_page_diff(pdf, tmp) if ok else 255.0
        ok = ok and diff < 3.0
        if ok:
            tmp.replace(pdf)
        else:
            tmp.unlink(missing_ok=True)
        rows.append(_row("pdfs", "pdfcraft", pdf.name, ok, "title/author set, page 1 unchanged" if ok else
                         (f"kept the original ({(r.err or r.out).strip()[:120] or 'the new file did not match'})")))
    return rows


# ---------------------------------------------------------------------------------------------------------- entry points
def build(folder: Path, pid: int | None = None, kinds: list[str] | None = None, force: bool = False) -> list[dict]:
    """Build the extra files. `kinds` None means every kind switched on in settings; force=True (an explicit command) ignores the switches
    but still needs the tool installed. Never raises. Returns one row per file."""
    folder = Path(folder)
    todo = [k for k in (kinds or KINDS) if k in KINDS and (force or want(k)) and ct.find_tool(TOOL_FOR[k])]
    if not todo:
        return []
    timeout = float(ct._cfg("timeout", 120)) if not force else 180.0
    rows: list[dict] = []
    try:
        spec = json.loads((folder / "spec.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        spec = {}
    out = folder / "product" / FOLDER
    try:
        if "vectors" in todo:
            rows += build_vectors(folder, pid, out, timeout, text=bool(ct.find_tool("photocraft")) and (force or ct.is_enabled("photocraft")))
        if "sheets" in todo:
            rows += build_sheets(folder, out, timeout)
        if "pdfs" in todo:
            rows += build_pdfs(folder, spec, timeout)
    except Exception as e:   # noqa: BLE001 - optional extras must never break a product
        rows.append(_row("-", "-", "-", False, f"stopped early: {e}"))
    made = [r for r in rows if r["ok"] and r["kind"] in ("vectors", "sheets")]
    if made and out.exists():
        fonts = _fonts_in(sorted((folder / "editable" / "posters").glob("*.svg")))
        (out / "README.txt").write_text(README.format(title=(spec.get("content") or {}).get("title", ""),
                                                      fonts=", ".join(fonts) or "the fonts named in the design"), encoding="utf-8")
    if rows:
        (folder / "craft-build.json").write_text(json.dumps({"files": rows}, indent=2), encoding="utf-8")
        if any(r["ok"] for r in rows):
            try:
                from .pipeline import make_package
                make_package(folder)
            except Exception:   # noqa: BLE001
                pass
    return rows


def after_make(folder: Path):
    """Called by the pipeline. None when switched off or nothing was built; otherwise one warn-only QA Check."""
    try:
        if not ct._cfg("outputs.after_make", False):
            return None
        from .qa import Check
        rows = build(folder)
        if not rows:
            return None
        bad = [r for r in rows if not r["ok"]]
        if not bad:
            return Check("Editable formats (craft tools)", "pass", f"{len(rows)} extra files built and re-opened cleanly")
        return Check("Editable formats (craft tools)", "warn",
                     f"{len(rows) - len(bad)} of {len(rows)} extra files built; skipped: " + ", ".join(r["file"] for r in bad[:5]) + " (see craft-build.json)")
    except Exception:   # noqa: BLE001
        return None
