"""Canva starter pack. Canva cannot import its own template files from outside, so this prepares what Canva does accept
(PDF and page images), a brand kit, and the buyer-facing page that holds your template link."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from ..design import style_from_dict
from ..render.html import PAGE_SIZES, render_html
from ..render.pdf import render_pdf
from ..render.raster import pdf_page_count, render_pages
from . import Loaded, out_dir, pack_zip

# Canva's font library includes these Google Fonts families.
CANVA_FONTS = {"PlayfairDisplay": "Playfair Display", "DMSans": "DM Sans", "Inter": "Inter", "Nunito": "Nunito", "Lora": "Lora",
               "Poppins": "Poppins", "Fraunces": "Fraunces", "Caveat": "Caveat"}

GUIDE = """# Making a Canva template from {title}

## 1. Bring the design into Canva
1. In Canva choose **Create a design > Import file** and pick `{pdf}` (or drag in the PNG pages from `pages/`).
2. Canva converts each page into an editable page. Check the text, spacing and fonts, because imports are rarely perfect.
3. Fonts: {fonts}. These are in Canva's font library. If Canva swaps one, choose it again from the font list.

## 2. Add the brand kit
Open **Brand** in Canva and add these colours: {colours}. Add the fonts above. Then everything you change stays on-brand.
(Brand kits need Canva Pro; with a free account just type the hex codes into the colour picker.)

## 3. Make the template link
1. Finish the design, then choose **Share > More > Template link**.
2. Copy the link.
3. Re-run `moneyhub export canva <id> --link <your link>` to put it into `{link_pdf}`, or paste it into that file yourself.
4. Sell `{link_pdf}` as your digital file. Buyers click the link and get their own copy.

## 4. Check the rules before you sell
Canva has rules for selling templates and for the elements you use. Read Canva's current Content License Agreement and
template-selling guidelines, and only use elements and fonts you are allowed to include. Listing text must say that buyers
receive a link, not a file, and that they need a Canva account.
"""


def export_canva(l: Loaded, link: str | None = None) -> Path:
    d = out_dir(l, "exports") / "canva"
    d.mkdir(parents=True, exist_ok=True)
    style = style_from_dict(l.spec["style"])
    pdfs = sorted((p for p in (l.folder / "product").glob("*.pdf") if not p.name.startswith("00-")),
                  key=lambda p: ("hyperlinked" in p.name, p.name))   # the product itself, not the one-page Start Here
    if not pdfs:
        raise ValueError("this product has no PDF pages to bring into Canva (Canva works with PDF and image pages)")
    src = pdfs[0]
    base = re.sub(r"[^a-z0-9]+", "-", l.title.lower()).strip("-")
    shutil.copy(src, d / f"{base}-for-canva.pdf")
    pages = d / "pages"
    pages.mkdir(exist_ok=True)
    n = pdf_page_count(src)
    for i, im in enumerate(render_pages(src, list(range(min(n, 12))), scale=2.4), 1):
        im.save(pages / f"page-{i:02d}.png")
    p, f = style.palette, style.fonts
    fonts = {CANVA_FONTS.get(x, x) for x in (f.heading, f.body, f.script)}
    colours = {"paper": p.paper, "ink": p.ink, "muted": p.muted, "line": p.line, "accent": p.accent, "accent_text": p.accent_ink, "soft": p.soft, "accent2": p.accent2}
    (d / "brand-kit.json").write_text(json.dumps({"colours": colours, "fonts": {"headings": CANVA_FONTS.get(f.heading, f.heading), "body": CANVA_FONTS.get(f.body, f.body),
                                                                                   "script": CANVA_FONTS.get(f.script, f.script)}}, indent=2), encoding="utf-8")
    link_pdf = f"{base}-canva-template-link.pdf"
    html = render_html("template_link.html.j2", style, PAGE_SIZES["letter"], margin=3.4, title=l.title, link=link, platform="Canva", fonts=", ".join(sorted(fonts)))
    render_pdf(html, d / link_pdf, page_css_size=PAGE_SIZES["letter"].css_size)
    (d / "HOW-TO-CANVA.md").write_text(GUIDE.format(
        title=l.title, pdf=f"{base}-for-canva.pdf", fonts=", ".join(sorted(fonts)), link_pdf=link_pdf,
        colours=", ".join(f"{k} {v}" for k, v in colours.items() if k in ("accent", "accent2", "soft", "ink"))), encoding="utf-8")
    pack_zip(l, "canva")
    return d
