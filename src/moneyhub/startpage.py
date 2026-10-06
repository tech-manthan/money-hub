"""'Start Here' PDF included in every download: what you have, how to print/open it, personal-use licence, support."""
from __future__ import annotations

from pathlib import Path

from .config import get_config
from .design import Style
from .products.base import BuildResult, ProductFile
from .render.html import PAGE_SIZES, render_html
from .render.pdf import render_pdf


def _gsheet_copy_link(url: str | None) -> str | None:
    if not url:
        return None
    return url.replace("/edit", "/copy").split("#")[0] if "/edit" in url else url


def build_start_page(build: BuildResult, style: Style, out_dir: Path, ptype_key: str, niche_key: str, gsheet_url: str | None = None) -> ProductFile | None:
    prim = [f for f in build.files if f.primary]
    if ptype_key == "wall_art" or len(prim) >= 5:   # wall art packs include READ-ME.txt; Etsy allows 5 files
        return None
    cfg = get_config()
    shop = {k: (cfg.get(f"shop.{k}") or "") for k in ("name", "email", "url")}
    css = ".steps div { margin:.35em 0; max-width:40em; } .cl-item { display:flex; align-items:center; margin:.25em 0; font-size:.95em; } .cl-item .sq { margin-right:.6em; }"
    html = render_html(
        "startpage.html.j2", style, PAGE_SIZES["letter"], extra_css=css, margin=3.0, title=build.title, shop=shop,
        files=[f.label if f.kind != "pdf" else f.path.name for f in prim],
        has_print=any(f.kind == "pdf" and "hyperlinked" not in f.path.name for f in prim),
        has_tablet=any("hyperlinked" in f.path.name for f in prim),
        has_xlsx=any(f.kind == "xlsx" for f in prim), has_a5=any("a5" in f.path.name for f in prim),
        gsheet=_gsheet_copy_link(gsheet_url), classroom=niche_key == "teacher")
    out = out_dir / "00-Start-Here.pdf"
    render_pdf(html, out, page_css_size=PAGE_SIZES["letter"].css_size)
    return ProductFile(out, "pdf", "Start Here: how to print/open and licence", True, preview_pages=[0])
