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


@lru_cache(maxsize=128)
def layout_preview_png(product_type: str, layout: str, palette: str = "", fonts: str = "", brand: str = "", eink: bool = False, seed: int = 7,
                       spec_json: str = "") -> bytes:
    """A real page from a miniature build of the product in the chosen layout (the page that best shows the layout)."""
    import random

    import pypdfium2 as pdfium

    from ..niches import resolve_niche
    from ..products import get_product_type
    from ..products.base import BuildContext

    pt = get_product_type(product_type)
    if not pt.has_layout(layout):
        raise ValueError("unknown layout")
    style = choose_style(seed=seed, palette=palette or None, fonts=fonts or None, brand=brand or None, eink=eink)
    niche = resolve_niche("nurse")
    opts = {"page_layout": layout, "weeks": 4, "days": 7, "no_research": True}
    if spec_json:
        import json
        opts["layout_spec"] = json.loads(spec_json)
    size = "eink" if eink and "eink" in pt.supported_sizes else "a5" if "a5" in pt.supported_sizes else pt.default_sizes[0]
    with tempfile.TemporaryDirectory() as tmp:
        ctx = BuildContext(niche=niche, style=style, out_dir=Path(tmp), sizes=[size], seed=seed, providers=["builtin"], options=opts)
        content = pt.builtin_content(niche, random.Random(seed), opts)
        shown = pt.layout_preview_image(ctx, content)
        if shown is not None:
            buf = io.BytesIO()
            shown.save(buf, "PNG", optimize=True)
            return buf.getvalue()
        res = pt.build(ctx, content)
        pdf = next(f.path for f in res.files if f.kind == "pdf")
        doc = pdfium.PdfDocument(str(pdf))
        index = pt.layout_preview_page
        for i in range(len(doc)):
            if pt.layout_marker and pt.layout_marker in doc[i].get_textpage().get_text_range():
                index = i
                break
        doc.close()
        img = render_pages(pdf, [index], scale=0.9)[0]
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
