"""Create all listing/cover/pin images for a built product."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from ..design import Style
from ..products.base import BuildResult, ProductFile
from ..render import graphics as g
from ..render.html import PAGE_SIZES
from ..render.raster import pdf_page_count, render_pages


def _preview_pages(build: BuildResult, want: int = 6) -> tuple[list[Image.Image], list[Image.Image]]:
    """(main page images, extra pages) from the best printable PDF."""
    pdfs = [f for f in build.files if f.kind == "pdf"]
    pdfs.sort(key=lambda f: (PAGE_SIZES.get(next((k for k in PAGE_SIZES if k in f.path.stem), "letter")).landscape, ))
    if not pdfs:
        return [], []
    f = pdfs[0]
    n = pdf_page_count(f.path)
    idx = [i for i in (f.preview_pages or [0, 1, 2]) if i < n][:6] or [0]
    for extra in range(n):
        if len(idx) >= want:
            break
        if extra not in idx:
            idx.append(extra)
    imgs = render_pages(f.path, idx, scale=2.2)
    return imgs[:3], imgs


def make_images(build: BuildResult, style: Style, out_dir: Path, ptype_key: str, copy, sizes_labels: list[str]) -> dict[str, list[Path]]:
    brush = g.Brush(style)
    main, extra = _preview_pages(build)
    if not main:
        return {}
    badges = ["Instant download", "Printable PDF" if any(f.kind == "pdf" for f in build.files) else "Digital file",
              "Excel & Google Sheets" if any(f.kind == "xlsx" for f in build.files) else "Letter & A4"]
    out: dict[str, list[Path]] = {"etsy": [], "gumroad": [], "payhip": [], "kofi": [], "pinterest": []}

    et = out_dir / "images" / "etsy"
    out["etsy"] += [
        g.save(g.hero(main, build.title, build.subtitle, badges, brush), et / "01-hero.jpg"),
        g.save(g.included(main, build.features, brush), et / "02-whats-included.jpg"),
        g.save(g.page_grid(extra[1:] or main, "A look inside", brush), et / "03-inside.jpg"),
        g.save(g.sizes_image(sizes_labels, "Instant PDF download. " + ("Spreadsheet works in Excel, Google Sheets and Numbers." if any(f.kind == "xlsx" for f in build.files) else "Print at home or at a print shop."), main, brush), et / "04-sizes-formats.jpg"),
        g.save(g.how_it_works([("Buy", "Check out securely on the marketplace."), ("Download", "Get your files instantly after payment."), ("Use it", "Print it or open it on your device.")], brush), et / "05-how-it-works.jpg"),
        g.save(g.detail(extra[min(2, len(extra) - 1)], "Designed to be used, not just admired", brush), et / "06-detail.jpg"),
    ]
    out["gumroad"] += [
        g.save(g.cover_wide(main, build.title, build.subtitle, brush, (1280, 720)), out_dir / "images" / "gumroad" / "cover-1280x720.png"),
        g.save(g.square(main, build.title, build.subtitle, brush, (600, 600)), out_dir / "images" / "gumroad" / "thumbnail-600x600.png"),
    ]
    out["payhip"] += [g.save(g.cover_wide(main, build.title, build.subtitle, brush, (1600, 1067)), out_dir / "images" / "payhip" / "cover-1600x1067.png")]
    out["kofi"] += [g.save(g.square(main, build.title, build.subtitle, brush, (1000, 1000)), out_dir / "images" / "kofi" / "square-1000x1000.png")]
    for i, headline in enumerate(copy.pin_headlines[:6]):
        out["pinterest"].append(g.save(
            g.pin(main + extra[:1], headline, build.title, i, brush), out_dir / "images" / "pinterest" / f"pin-{i + 1:02d}-1000x1500.png"))
    return out
