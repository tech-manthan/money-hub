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
    if build.meta.get("art_previews"):  # image products (wall art): previews are already rendered
        imgs = [Image.open(p).convert("RGB") for p in build.meta["art_previews"]]
        return imgs[:3], imgs
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


def make_images(build: BuildResult, style: Style, out_dir: Path, ptype_key: str, copy, sizes_labels: list[str],
                router=None, niche=None, providers=None, videos: bool = False) -> dict[str, list[Path]]:
    brush = g.Brush(style)
    main, extra = _preview_pages(build)
    if not main:
        return {}
    is_art = bool(build.meta.get("art_previews"))
    badges = ["Instant download", "Printable PDF" if any(f.kind == "pdf" for f in build.files) else "Digital file",
              "Excel & Google Sheets" if any(f.kind == "xlsx" for f in build.files) else "Letter & A4"]
    sheet_imgs: list[Image.Image] = []
    if build.meta.get("sheet_kind"):
        from ..render import sheetshots
        title = build.title
        if build.meta["sheet_kind"] == "habit":
            sheet_imgs = [sheetshots.habit_shot(build.meta["habits"], title, brush, style.seed)]
        else:
            sheet_imgs = [sheetshots.budget_shot(build.meta["groups"], title, brush, style.seed)]
    if is_art:
        badges = ["Instant download", "High-res JPG", "5 print ratios"]
    out: dict[str, list[Path]] = {"etsy": [], "gumroad": [], "payhip": [], "kofi": [], "pinterest": [], "video": []}

    et = out_dir / "images" / "etsy"
    out["etsy"] += [
        g.save(g.gallery_wall(main, build.title, build.subtitle, brush) if is_art else g.hero(main, build.title, build.subtitle, badges, brush), et / "01-hero.jpg"),
        g.save(g.included(main, build.features, brush), et / "02-whats-included.jpg"),
        g.save(g.page_grid(extra[1:] or main, "A look inside", brush), et / "03-inside.jpg"),
        g.save(g.sizes_image(sizes_labels, ("Instant JPG download. Print at home or at any print shop." if is_art else "Instant PDF download. " + ("Spreadsheet works in Excel, Google Sheets and Numbers." if any(f.kind == "xlsx" for f in build.files) else "Print at home or at a print shop.")), main, brush), et / "04-sizes-formats.jpg"),
        g.save(g.how_it_works([("Buy", "Check out securely on the marketplace."), ("Download", "Get your files instantly after payment."), ("Use it", "Print it or open it on your device.")], brush), et / "05-how-it-works.jpg"),
        g.save(g.detail(extra[min(2, len(extra) - 1)], "Designed to be used, not just admired", brush), et / "06-detail.jpg"),
    ]
    for n, im in enumerate(sheet_imgs):
        out["etsy"].append(g.save(im, et / f"{7 + n:02d}-spreadsheet-illustration.jpg"))
    out["gumroad"] += [
        g.save(g.cover_wide(main, build.title, build.subtitle, brush, (1280, 720)), out_dir / "images" / "gumroad" / "cover-1280x720.png"),
        g.save(g.square(main, build.title, build.subtitle, brush, (600, 600)), out_dir / "images" / "gumroad" / "thumbnail-600x600.png"),
    ]
    out["payhip"] += [g.save(g.cover_wide(main, build.title, build.subtitle, brush, (1600, 1067)), out_dir / "images" / "payhip" / "cover-1600x1067.png")]
    out["kofi"] += [g.save(g.square(main, build.title, build.subtitle, brush, (1000, 1000)), out_dir / "images" / "kofi" / "square-1000x1000.png")]
    for i, headline in enumerate(copy.pin_headlines[:6]):
        out["pinterest"].append(g.save(
            g.pin(main + extra[:1], headline, build.title, i, brush), out_dir / "images" / "pinterest" / f"pin-{i + 1:02d}-1000x1500.png"))
    if videos:
        out["video"] = _videos(build, brush, out_dir, copy, main + extra[:2], router, niche, providers)
    return out


def _videos(build, brush, out_dir, copy, pages, router, niche, providers) -> list[Path]:
    from ..render import motion

    if not motion.available():
        return []
    plan = None
    if router is not None and niche is not None:
        plan = motion.llm_plan(router, build.title, build.subtitle, build.features, niche.audience, providers)
    if plan is None:
        plan = motion.builtin_plan(build.title, build.subtitle, build.features, copy.pin_headlines[0] if copy.pin_headlines else build.title)
    vids = []
    for name, size in (("pin-video-1000x1500.mp4", (1000, 1500)), ("listing-video-1920x1080.mp4", (1920, 1080))):
        v = motion.render_video(plan, pages, brush, out_dir / "images" / "video" / name, size, build.title)
        if v:
            vids.append(v)
    return vids
