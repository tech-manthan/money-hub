"""Amazon KDP paperback pack: print-ready interior PDF at an exact trim size, a full-wrap cover template with the spine width
worked out from the page count, and a step-by-step guide. Rules used (check KDP's current guidelines before publishing):
margins (gutter by page count), 24-page minimum, no bleed needed when content stays inside the safe area, 0.125 in cover bleed,
paper thickness for the spine. KDP's own cover template generator is the final authority on spine width."""
from __future__ import annotations

import dataclasses
import json
import random
import re
import shutil
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from ..design import style_from_dict
from ..niches import resolve_niche
from ..products import get_product_type
from ..products.base import BuildContext
from ..qa import _pdf_fonts_embedded
from ..render.html import KDP_TRIMS, PAGE_SIZES, PageSize, render_html
from ..render.pdf import render_pdf
from . import Loaded, out_dir, pack_zip

SUPPORTED = ("weekly_planner", "daily_planner", "guided_journal", "checklist_pack", "worksheet_pack", "ebook_guide", "habit_tracker", "coloring_pages", "kids_coloring", "activity_book", "learning_workbook")
PAPER = {"white": 0.002252, "cream": 0.0025, "color": 0.0032}   # inches per page (KDP)
BLEED = 0.125
MIN_PAGES, MAX_PAGES = 24, 828


def gutter_in(pages: int) -> float:
    for limit, g in ((150, 0.375), (300, 0.5), (500, 0.625), (700, 0.75)):
        if pages <= limit:
            return g
    return 0.875


def spine_in(pages: int, paper: str) -> float:
    return round(pages * PAPER[paper], 4)


def cover_size(trim: str, pages: int, paper: str) -> dict:
    tw, th = KDP_TRIMS[trim]
    sp = spine_in(pages, paper)
    w, h = round(2 * tw + sp + 2 * BLEED, 4), round(th + 2 * BLEED, 4)
    return {"trim_in": [tw, th], "spine_in": sp, "full_cover_in": [w, h], "full_cover_px_300dpi": [round(w * 300), round(h * 300)],
            "bleed_in": BLEED, "front_cover_in": [tw, th], "back_cover_in": [tw, th]}


def _build_interior(l: Loaded, trim: str, margin_in: float, work: Path) -> Path:
    pt = get_product_type(l.ptype)
    style = style_from_dict(l.spec["style"])
    if style.header == "band":   # a full-width band would run to the page edge, which needs bleed
        style = dataclasses.replace(style, header="rule")
    page = PAGE_SIZES[f"kdp_{trim}"]
    opts = {**l.spec["request"].get("options", {}), "margin_em": round(margin_in * 72 / page.base_pt, 3), "kdp": True}   # coloring pages: no cover page, a blank back for every design
    ctx = BuildContext(niche=resolve_niche(l.spec["request"]["niche"]), style=style, out_dir=work, sizes=[f"kdp_{trim}"],
                       seed=l.spec["request"].get("seed", 1), providers=["builtin"], options=opts)
    res = pt.build(ctx, pt.content_model.model_validate(l.content))
    pdfs = [f.path for f in res.files if f.kind == "pdf" and "hyperlinked" not in f.path.name]
    if not pdfs:
        raise ValueError("this product did not produce a PDF interior")
    return pdfs[0]


def _notes_pdf(l: Loaded, trim: str, count: int, margin_in: float, dst: Path) -> None:
    style = style_from_dict(l.spec["style"])
    if style.header == "band":
        style = dataclasses.replace(style, header="rule")
    page = PAGE_SIZES[f"kdp_{trim}"]
    html = render_html("notes_pages.html.j2", style, page, margin=round(margin_in * 72 / page.base_pt, 3), count=count, title=l.title)
    render_pdf(html, dst, page_css_size=page.css_size)


def _blurb(l: Loaded, listing: dict) -> tuple[str, list[str]]:
    """Back-cover text: the first paragraph of the listing description (or the tagline) and up to three selling points."""
    copy = listing.get("copy_") or listing.get("copy") or {}
    text = re.sub(r"\s+", " ", str(copy.get("description", "")).split("\n\n")[0]).strip() or l.content.get("tagline", "")
    if len(text) > 420:
        text = text[:420].rsplit(" ", 1)[0].rstrip(",;:") + "..."
    feats = [str(x) for x in (listing.get("features") or copy.get("features") or [])][:3]
    return text, feats


def _prepare_cover_image(src: Path, dst: Path, tw: float, th: float, h: float) -> dict:
    """Copy the buyer's cover art in as a JPEG and report how sharp it will be on the front cover (needs ~300 dpi)."""
    from PIL import Image

    try:
        im = Image.open(src)
        im.load()
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"cannot read the cover image: {e}") from e
    im = im.convert("RGB")
    need_w = tw + BLEED   # the art runs from the spine to the right edge, including bleed
    dpi = min(im.width / need_w, im.height / h)
    im.save(dst, "JPEG", quality=95, dpi=(300, 300))
    return {"px": [im.width, im.height], "effective_dpi": round(dpi), "needs_px": [round(need_w * 300), round(h * 300)]}


def export_kdp(l: Loaded, trim: str = "6x9", paper: str = "white", progress=print, cover_image: Path | None = None, cover_text: bool = True) -> dict:
    if l.ptype not in SUPPORTED:
        raise ValueError(f"{l.ptype} cannot be a KDP paperback. Supported: {', '.join(SUPPORTED)}")
    if trim not in KDP_TRIMS:
        raise ValueError(f"trim must be one of: {', '.join(KDP_TRIMS)}")
    if paper not in PAPER:
        raise ValueError(f"paper must be one of: {', '.join(PAPER)}")
    d = out_dir(l, "exports") / "kdp"
    d.mkdir(parents=True, exist_ok=True)
    base = re.sub(r"[^a-z0-9]+", "-", l.title.lower()).strip("-")
    margin = 0.5
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        progress(f"Building the interior at {trim} in")
        src = _build_interior(l, trim, margin, work / "a")
        pages = len(PdfReader(str(src)).pages)
        if gutter_in(max(pages, MIN_PAGES)) > margin:   # more pages need a wider inside margin: rebuild once
            margin = gutter_in(max(pages, MIN_PAGES))
            progress(f"{pages} pages need a {margin} in inside margin; rebuilding")
            src = _build_interior(l, trim, margin, work / "b")
            pages = len(PdfReader(str(src)).pages)
        target = max(pages, MIN_PAGES)
        target += target % 2   # an even page count prints without a stray blank leaf
        if target > MAX_PAGES:
            raise ValueError(f"{pages} pages is more than KDP's {MAX_PAGES}-page paperback limit")
        interior = d / f"{base}-interior-{trim}.pdf"
        w = PdfWriter()
        w.append(str(src))
        if target > pages:
            progress(f"Adding {target - pages} notes pages (KDP needs at least {MIN_PAGES} and an even count)")
            notes = work / "notes.pdf"
            _notes_pdf(l, trim, target - pages, margin, notes)
            w.append(str(notes))
        w.add_metadata({"/Title": l.title})
        with open(interior, "wb") as fh:
            w.write(fh)
    cs = cover_size(trim, target, paper)
    cw, ch = cs["full_cover_in"]
    style = style_from_dict(l.spec["style"])
    cover_page = PageSize("kdp_cover", "KDP cover", cw, ch, 10.0)
    html = render_html("kdp_cover.html.j2", style, cover_page, margin=0, w=cw, h=ch, bleed=BLEED, tw=KDP_TRIMS[trim][0], th=KDP_TRIMS[trim][1],
                       spine=cs["spine_in"], title=l.title, subtitle=l.content.get("tagline", ""))
    render_pdf(html, d / f"{base}-cover-template-{trim}.pdf", page_css_size=cover_page.css_size)
    listing = {}
    lj = l.folder / "listing" / "listing.json"
    if lj.exists():
        listing = json.loads(lj.read_text())
    image_info, image_uri = None, ""
    if cover_image:
        progress("Placing your cover image on the front")
        art = d / "cover-art.jpg"
        image_info = _prepare_cover_image(Path(cover_image), art, KDP_TRIMS[trim][0], KDP_TRIMS[trim][1], ch)
        image_uri = art.as_uri()
    blurb, bullets = _blurb(l, listing)
    progress("Designing the finished full-wrap cover")
    final = render_html("kdp_cover_final.html.j2", style, cover_page, margin=0, w=cw, h=ch, bleed=BLEED, tw=KDP_TRIMS[trim][0], th=KDP_TRIMS[trim][1],
                        spine=cs["spine_in"], title=l.title, subtitle=l.content.get("tagline", ""), image=image_uri, text=cover_text or not cover_image,
                        blurb=blurb, bullets=bullets)
    cover_pdf = d / f"{base}-cover-{trim}.pdf"
    render_pdf(final, cover_pdf, page_css_size=cover_page.css_size)
    total, emb = _pdf_fonts_embedded(interior)
    pw, ph = (float(x) / 72 for x in PdfReader(str(interior)).pages[0].mediabox[2:])
    checks = [("Page count", MIN_PAGES <= target <= MAX_PAGES and target % 2 == 0, f"{target} pages"),
              ("Page size matches trim", abs(pw - KDP_TRIMS[trim][0]) < 0.02 and abs(ph - KDP_TRIMS[trim][1]) < 0.02, f"{pw:.3f} x {ph:.3f} in"),
              ("Fonts embedded", total == emb, f"{emb}/{total}"),
              ("Inside margin", margin >= gutter_in(target), f"{margin} in (needs {gutter_in(target)} in)")]
    cw_pt, ch_pt = (float(x) / 72 for x in PdfReader(str(cover_pdf)).pages[0].mediabox[2:])
    checks.append(("Cover size matches spine and page count", abs(cw_pt - cw) < 0.02 and abs(ch_pt - ch) < 0.02, f"{cw_pt:.3f} x {ch_pt:.3f} in (needs {cw} x {ch})"))
    if image_info:
        checks.append(("Cover image sharpness", image_info["effective_dpi"] >= 250,
                       f"{image_info['px'][0]} x {image_info['px'][1]} px = about {image_info['effective_dpi']} dpi (aim for {image_info['needs_px'][0]} x {image_info['needs_px'][1]})"))
    spec = {"title": l.title, "trim": trim, "paper": paper, "pages": target, "interior_margin_in": margin, **cs, "cover_pdf": cover_pdf.name, "cover_image": image_info,
            "checks": [{"name": n, "ok": ok, "detail": dt} for n, ok, dt in checks]}
    (d / "cover-spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    (d / "KDP-GUIDE.md").write_text(_guide(l, spec, listing, base), encoding="utf-8")
    pack_zip(l, "kdp")
    return spec


def _guide(l: Loaded, s: dict, listing: dict, base: str) -> str:
    tags = (listing.get("copy_") or listing.get("copy") or {}).get("tags", [])[:7]
    return f"""# KDP paperback: {l.title}

Files: `{base}-interior-{s['trim']}.pdf` ({s['pages']} pages), `{base}-cover-{s['trim']}.pdf` (finished full-wrap cover), `{base}-cover-template-{s['trim']}.pdf` (guide lines), `cover-spec.json`.

## Cover
- Full cover (back + spine + front, with {s['bleed_in']} in bleed): **{s['full_cover_in'][0]} x {s['full_cover_in'][1]} in** = {s['full_cover_px_300dpi'][0]} x {s['full_cover_px_300dpi'][1]} px at 300 dpi.
- Spine width: **{s['spine_in']} in** ({s['pages']} pages, {s['paper']} paper). {'Spine text needs at least 79 pages.' if s['pages'] < 79 else 'Spine text is allowed.'}
- Keep text inside the dotted safe lines. Leave the 2 x 1.2 in barcode area empty on the back cover.
- The finished cover PDF is ready to upload as it is. To use your own artwork instead, run the export again with a cover image (CLI `--cover-image`, or the picture box on the product page), or design one in Canva or Photoshop at that exact size and use the template PDF as a guide layer.
- KDP puts the barcode on the back cover itself, so the lower right of the back is kept free of text.
- **Always** confirm the spine width with KDP's own cover template generator (it asks for trim size, paper and page count).

## Interior
- Trim {s['trim']} in, no bleed, all content inside the safe area. Inside margin {s['interior_margin_in']} in (KDP requires more as page count rises).
- Fonts are embedded. Upload the interior PDF as it is.

## On the KDP bookshelf
1. Create a **Paperback**. Paste the title and description below.
2. Keywords (7 allowed): {', '.join(tags) if tags else 'use the search phrases from your Etsy tags'}
3. Pick two categories that match the audience. Look at where similar books sit.
4. Choose a **{s['trim']} in** trim, **{s['paper']}** paper, and **no bleed** for the interior.
5. Upload the interior and cover PDFs, then use KDP's previewer to check every page.
6. Set the price using KDP's print-cost calculator. Printing cost depends on page count and paper.
7. KDP asks whether the content was made with AI tools. Answer honestly. The text and artwork in this product were generated with software.

## Notes
- Planners, journals and logbooks are "low-content books". KDP can supply a free ISBN, and you do not need your own.
- Do not use trademarked names or brand terms in the title, subtitle or keywords.
- A printed book can look different from the on-screen PDF: order a proof copy before you launch.
- These specifications were checked against KDP's help pages when this tool was written. KDP changes them from time to time, so confirm them in KDP.
"""
