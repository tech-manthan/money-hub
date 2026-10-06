"""Quick sample page in a chosen look, so people can see colours, fonts and shapes before making a whole product."""
from __future__ import annotations

import io
import tempfile
from functools import lru_cache
from pathlib import Path

from ..design import choose_style
from .html import PAGE_SIZES, render_html
from .pdf import render_pdf
from .raster import render_pages


@lru_cache(maxsize=64)
def look_preview_png(palette: str = "", fonts: str = "", header: str = "", radius: str = "", grid: str = "",
                     brand: str = "", eink: bool = False, seed: int = 7) -> bytes:
    style = choose_style(seed=seed, palette=palette or None, fonts=fonts or None, header=header or None,
                         radius=int(radius) if radius.isdigit() else None, grid=grid or None, brand=brand or None, eink=eink)
    page = PAGE_SIZES["eink" if eink else "a5"]
    html = render_html("look_preview.html.j2", style, page, margin=3.2, title="Weekly planner", tagline="Plan the week you have.")
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "p.pdf"
        render_pdf(html, pdf, page_css_size=page.css_size)
        img = render_pages(pdf, [0], scale=1.1)[0]
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
