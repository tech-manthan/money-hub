"""PDF -> PNG page previews (pypdfium2)."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

ISOLATE_ENV = "MONEYHUB_ISOLATE_PDFIUM"   # set by `moneyhub ui`: render page previews in a child process, so a pdfium crash costs one preview, not the server


def isolated() -> bool:
    return os.environ.get(ISOLATE_ENV) == "1"


def _render_in_child(pdf: Path, pages: list[int], scale: float) -> list[Image.Image]:
    """Rasterise in a short-lived Python process. A crash inside pdfium (it has segfaulted on malformed files) then only fails this call."""
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run([sys.executable, "-m", "moneyhub.render.pdfium_worker", str(pdf), str(scale), td, *map(str, pages)],
                           capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        if r.returncode != 0:
            raise RuntimeError(f"could not render {Path(pdf).name} (the PDF reader stopped with code {r.returncode})")
        return [Image.open(Path(td) / f"{i}.png").convert("RGB") for i in map(int, r.stdout.split())]


def pdf_page_count(pdf: Path) -> int:
    doc = pdfium.PdfDocument(str(pdf))
    try:
        return len(doc)
    finally:
        doc.close()


def render_pages(pdf: Path, pages: list[int], scale: float = 1.6) -> list[Image.Image]:
    if isolated():
        return _render_in_child(Path(pdf), pages, scale)
    doc = pdfium.PdfDocument(str(pdf))
    try:
        out = []
        for i in pages:
            if 0 <= i < len(doc):
                out.append(doc[i].render(scale=scale).to_pil().convert("RGB"))
        return out
    finally:
        doc.close()


def save_pages(pdf: Path, pages: list[int], out_dir: Path, prefix: str = "page", scale: float = 1.6) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, img in zip(pages, render_pages(pdf, pages, scale)):
        p = out_dir / f"{prefix}-{i + 1:03d}.png"
        img.save(p, optimize=True)
        paths.append(p)
    return paths
