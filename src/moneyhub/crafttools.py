"""Optional second opinion from the storytold craft command-line tools (pdfcraft, gridcraft, vectorcraft, ...).

Installed by `scripts/install_craft_tools.sh` into tools/craft/<name>/current/. They are third-party programs, so everything here is
advisory: a missing tool, a crash or a timeout never fails a product, and nothing here is part of the QA gate. `verify_product` opens a
finished product's PDFs, spreadsheets and editable SVGs with the tools and reports whether each one reads cleanly."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

TOOLS = ["vectorcraft", "pdfcraft", "gridcraft", "photocraft", "wordcraft", "deckcraft", "filmcraft", "soundcraft", "lightcraft", "cadcraft",
         "designcraft", "effectcraft"]


def tools_dir() -> Path:
    """tools/craft next to the project, or MONEYHUB_CRAFT_DIR."""
    env = os.environ.get("MONEYHUB_CRAFT_DIR")
    return Path(env) if env else Path(__file__).resolve().parents[2] / "tools" / "craft"


def find_tool(name: str) -> Path | None:
    base = tools_dir() / name
    hits = sorted((base / "current").glob(f"*/{name}-cli")) + sorted((base / "current").glob(f"{name}-cli"))
    for h in hits:
        if h.is_file() and os.access(h, os.X_OK):
            return h
    on_path = shutil.which(f"{name}-cli")
    return Path(on_path) if on_path else None


def version(name: str) -> str:
    v = tools_dir() / name / "VERSION"
    return v.read_text(encoding="utf-8").strip() if v.exists() else ""


def status() -> list[dict]:
    return [{"tool": n, "path": str(p) if (p := find_tool(n)) else "", "version": version(n)} for n in TOOLS]


@dataclass
class Run:
    ok: bool
    code: int
    out: str
    err: str


def run(name: str, args: list[str], timeout: float = 60.0) -> Run:
    """Run `<name>-cli args...`. Never raises: a missing tool, a crash or a timeout comes back as ok=False."""
    exe = find_tool(name)
    if exe is None:
        return Run(False, -1, "", f"{name} is not installed (run scripts/install_craft_tools.sh)")
    try:
        p = subprocess.run([str(exe), *args], capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return Run(False, -2, "", f"{name} timed out after {timeout:g}s")
    except OSError as e:
        return Run(False, -3, "", f"{name} could not start: {e}")
    return Run(p.returncode == 0, p.returncode, p.stdout, p.stderr)


def _finding(file: Path, tool: str, r: Run, what: str) -> dict:
    detail = (r.out if r.ok else (r.err or r.out)).strip().replace("\n", " ")[:300]
    return {"file": file.name, "tool": tool, "check": what, "ok": r.ok, "detail": detail}


def verify_product(folder: Path, timeout: float = 90.0) -> list[dict]:
    """Open each PDF, spreadsheet and editable SVG of a product with the matching tool and report whether it reads cleanly."""
    folder = Path(folder)
    out: list[dict] = []
    pdfs = sorted(p for p in (folder / "product").glob("*.pdf"))
    for f in pdfs:
        out.append(_finding(f, "pdfcraft", run("pdfcraft", ["info", str(f)], timeout), "opens and summarises"))
        with tempfile.TemporaryDirectory() as td:
            png = Path(td) / "p1.png"
            r = run("pdfcraft", ["render", str(f), "--page", "1", "--dpi", "48", "--out", str(png)], timeout)
            r.ok = r.ok and png.exists() and png.stat().st_size > 200
            out.append(_finding(f, "pdfcraft", r, "page 1 renders"))
    for f in sorted((folder / "product").glob("*.xlsx")):
        out.append(_finding(f, "gridcraft", run("gridcraft", ["info", str(f), "--json"], timeout), "opens and lists sheets"))
    for f in sorted((folder / "editable").rglob("*.svg"))[:12]:
        out.append(_finding(f, "vectorcraft", run("vectorcraft", ["info", str(f)], timeout), "opens as a vector document"))
    for f in sorted((folder / "product").glob("*.docx")):
        out.append(_finding(f, "wordcraft", run("wordcraft", ["info", str(f)], timeout), "opens as a document"))
    for f in sorted((folder / "product").glob("*.pptx")):
        out.append(_finding(f, "deckcraft", run("deckcraft", ["info", str(f)], timeout), "opens as a presentation"))
    audio = [p for ext in ("wav", "mp3", "m4a", "flac") for p in sorted(folder.rglob(f"*.{ext}"))][:3]
    for f in audio:
        out.append(_finding(f, "soundcraft", run("soundcraft", ["info", str(f)], timeout), "opens as audio"))
    for z in sorted((folder / "product").glob("*.zip"))[:6]:   # cut files ship their DXF files zipped
        try:
            with zipfile.ZipFile(z) as zf, tempfile.TemporaryDirectory() as td:
                for n in [n for n in zf.namelist() if n.lower().endswith(".dxf")][:3]:
                    dst = Path(td) / Path(n).name
                    dst.write_bytes(zf.read(n))
                    r = _finding(dst, "cadcraft", run("cadcraft", ["info", str(dst)], timeout), "opens as a drawing")
                    r["file"] = f"{z.name}:{Path(n).name}"
                    out.append(r)
        except (zipfile.BadZipFile, OSError):
            out.append({"file": z.name, "tool": "cadcraft", "check": "zip opens", "ok": False, "detail": "not a readable zip file"})
    images = [p for ext in ("jpg", "png") for p in sorted((folder / "images").rglob(f"*.{ext}"))][:6]
    for f in images:
        out.append(_finding(f, "photocraft", run("photocraft", ["info", str(f), "--compact"], timeout), "opens as an image"))
    return out


def passthrough(name: str, args: list[str], timeout: float = 300.0) -> Run:
    """Run any craft tool with your own arguments (with the same timeout and no-crash behaviour as the checks)."""
    if name not in TOOLS:
        return Run(False, -4, "", f"unknown tool '{name}'. Choose from: {', '.join(TOOLS)}")
    return run(name, args, timeout)


def write_report(folder: Path, findings: list[dict]) -> Path:
    p = Path(folder) / "craft-verify.json"
    p.write_text(json.dumps({"tools": status(), "findings": findings}, indent=2), encoding="utf-8")
    return p
