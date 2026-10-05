"""PDF -> PNG page previews (pypdfium2)."""
from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image


def pdf_page_count(pdf: Path) -> int:
    doc = pdfium.PdfDocument(str(pdf))
    try:
        return len(doc)
    finally:
        doc.close()


def render_pages(pdf: Path, pages: list[int], scale: float = 1.6) -> list[Image.Image]:
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
