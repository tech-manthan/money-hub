"""Character clipart: the kids figure library (animals, vehicles, seasonal, fantasy...) filled with a palette's colours as transparent 2400 px PNGs
and SVG vectors with a commercial licence PDF. Pick a theme; every pack uses a different seeded look for each figure."""
from __future__ import annotations

import io
import random
import re
import zipfile

import pypdfium2 as pdfium
from PIL import Image
from pydantic import BaseModel, Field

from .. import kidsart, stickers
from ..config import get_config
from ..niches import NicheProfile
from ..render import mockups
from ..render.pdf import render_many
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register
from .wall_art import JPEG_BUDGET, srgb_profile

PX = 2400


class CharContent(BaseModel):
    title: str
    subtitle: str = "Cute character clipart: transparent PNG + SVG, commercial use"
    tagline: str = Field(description="One short, warm line (<= 70 chars)")
    count: int = Field(default=24, ge=12, le=60, description="Number of characters")


def _theme(options: dict) -> str:
    t = str(options.get("theme") or "mixed")
    if t not in kidsart.THEMES:
        raise ValueError(f"unknown theme '{t}'. Choose one of: {', '.join(kidsart.THEMES)}")
    return t


@register
class CharacterClipart(ProductType[CharContent]):
    key = "character_clipart"
    label = "Character clipart"
    description = "Cute colored character clipart (animals, vehicles, seasonal, fantasy): transparent PNGs, SVG vectors and a commercial licence PDF. Pick a theme."
    content_model = CharContent
    default_sizes = ["png"]
    supported_sizes = ["png"]
    price_range = (4.0, 14.0)
    typical_formats = "Transparent PNG (2400 px, 300 DPI) + SVG + licence PDF"
    niche_in_copy = False
    copy_audience = "teachers, crafters, planner makers and small shops"
    title_suffix = " Clipart Bundle"
    license_terms = ("Commercial use is included: use the clipart in your own finished designs and products (printables, worksheets, stickers, cards, planners, "
                     "social posts, packaging) with no credit needed. You may not resell, share or redistribute the clipart files themselves, include them in other "
                     "clipart packs, or use them to train AI models. Full terms are in the Commercial-License PDF inside the download.")
    license_faq = "Q: Can I use it for my business? A: Yes, commercial use is included. You may not resell or share the clipart files themselves. See the licence PDF."
    how_steps = ("Purchase and download your files instantly.", "Unzip, then place the PNG or SVG files in Canva, Google Slides, Procreate, Cricut Design Space or any design app.",
                 "Create and sell your own designs, following the included licence.")

    def size_options(self):
        return [("png", "Transparent PNG (2400 px) + SVG vectors + licence PDF")]

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> CharContent:
        n = max(12, min(int(options.get("count", 24)), 60))
        return CharContent(title=f"{kidsart.THEMES[_theme(options)][0]} Clipart Bundle", tagline="Cute characters ready to use in your designs.", count=n)

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return (f"Write a short title and warm tagline for a CHARACTER CLIPART bundle with the theme '{kidsart.THEMES[_theme(options)][0]}' "
                f"({int(options.get('count', 24))} cute characters, transparent PNG and SVG, commercial use). End the title with 'Clipart Bundle'. Do not mention any niche or profession.")

    def build(self, ctx: BuildContext, content: CharContent) -> BuildResult:
        theme = _theme(ctx.options)
        content = content.model_copy(update={"title": self.unique_title(ctx, content.title)})
        slug = self.slug(content.title)
        n = max(12, min(int(ctx.options.get("count", content.count)), 60))
        pal = ctx.style.palette
        art_dir = ctx.out_dir.parent / "art"
        art_dir.mkdir(exist_ok=True)

        pool = list(kidsart.THEMES[theme][1])
        order = list(kidsart.KINDS) if theme == "mixed" else pool
        random.Random(ctx.seed).shuffle(order)
        items = []
        for i in range(n):
            kind = order[i % len(order)]
            seed = ctx.seed * 977 + i
            body = stickers.recolor(kidsart.figure(kind, seed, 12, False), pal, seed)
            svg = f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 1000'>{body}</svg>"
            items.append((kidsart.NAMES[kind], svg))
        html = ("<style>@page{size:10in 10in;margin:0}html,body{margin:0;background:none}.p{width:10in;height:10in;page-break-after:always}"
                ".p svg{width:10in;height:10in;display:block}</style>" + "".join(f"<div class='p'>{svg}</div>" for _, svg in items))
        pdf = art_dir / f"{slug}.pdf"
        renderer = render_many([(html, pdf, "10in 10in")])[0]
        pngs: list[tuple[str, bytes, Image.Image]] = []
        doc = pdfium.PdfDocument(str(pdf))
        used = {}
        try:
            for i, (name, _) in enumerate(items):
                im = doc[i].render(scale=PX / 720, fill_color=(255, 255, 255, 0)).to_pil().convert("RGBA")
                if im.size != (PX, PX):
                    im = im.resize((PX, PX), Image.LANCZOS)
                used[name] = used.get(name, 0) + 1
                label = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") + (f"-{used[name]}" if used[name] > 1 else "")
                buf = io.BytesIO()
                im.save(buf, "PNG", dpi=(300, 300), optimize=True, icc_profile=srgb_profile())
                pngs.append((f"{i + 1:02d}-{label}", buf.getvalue(), im))
        finally:
            doc.close()

        groups: list[list[tuple[str, bytes]]] = []
        sizes: list[int] = []
        for name, data, _ in pngs:   # first-fit: each zip stays under Etsy's 20 MB per file
            for g, u in enumerate(sizes):
                if u + len(data) <= JPEG_BUDGET:
                    groups[g].append((name, data))
                    sizes[g] += len(data)
                    break
            else:
                groups.append([(name, data)])
                sizes.append(len(data))
        files: list[ProductFile] = []
        for g, grp in enumerate(groups, 1):
            z = ctx.out_dir / f"{slug}-PNG{'-' + str(g) if len(groups) > 1 else ''}.zip"
            with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
                for name, data in grp:
                    zf.writestr(f"{name}.png", data)
                zf.writestr("READ-ME.txt", f"{content.title}\n\nTransparent PNG clipart, {PX} x {PX} px at 300 DPI, sRGB. See the Commercial-License PDF for the terms.\n")
            files.append(ProductFile(z, "zip", f"Transparent PNG files (part {g})" if len(groups) > 1 else "Transparent PNG files", True))
        svg_zip = ctx.out_dir / f"{slug}-SVG.zip"
        with zipfile.ZipFile(svg_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, ((name, svg), (label, _, _)) in enumerate(zip(items, pngs)):
                zf.writestr(f"{label}.svg", svg.replace("<svg ", "<svg width='1000' height='1000' ", 1))
            zf.writestr("READ-ME.txt", "Vector (SVG) versions. Open in Illustrator, Inkscape, Affinity, Canva or Cricut Design Space. See the Commercial-License PDF for the terms.\n")
        files.append(ProductFile(svg_zip, "zip", "SVG vector files", True))
        license_pdf = ctx.out_dir / "Commercial-License.pdf"
        cfg = get_config()
        self.render_jobs(ctx, "clipart_license.html.j2", [(ctx.page("letter"), license_pdf, {"title": content.title, "count": n, "noun": "clipart designs",
                                                         "shop": {k: (cfg.get(f"shop.{k}") or "") for k in ("name", "email", "url")}})], margin=3.0)
        files.append(ProductFile(license_pdf, "pdf", "Commercial licence (PDF)", True, preview_pages=[0]))

        previews = []
        for k in range(6):   # contact sheets: 3 x 4 characters on light, soft and accent backgrounds
            bg = (pal.paper, pal.soft, pal.accent2, pal.paper, pal.soft, pal.accent)[k]
            sheet = Image.new("RGB", (1200, 1500), bg)
            for j in range(12):
                t = pngs[(k * 12 + j) % len(pngs)][2].resize((340, 340), Image.LANCZOS)
                sheet.paste(t, (40 + (j % 3) * 385, 60 + (j // 3) * 360), t)
            pth = art_dir / f"preview-{k + 1:02d}.png"
            sheet.save(pth)
            previews.append(pth)
        features = [f"{n} cute colored characters ({kidsart.THEMES[theme][0].lower()})", f"{n} transparent PNG files, {PX} x {PX} px, 300 DPI", f"{n} editable SVG vector files",
                    "Commercial use included, no credit needed", "Instant download - works in Canva, Procreate, Google Slides and Cricut Design Space"]
        return BuildResult(content.title, content.subtitle, files, features, n, renderer,
                           meta={"art_previews": previews, "mockup_tiles": mockups.save_tiles(art_dir, [t[2] for t in pngs][::max(1, n // 4)]), "flat_art": True,
                                 "badges": ["Instant download", "PNG + SVG", "Commercial use"], "delivery_note": "Instant download: transparent PNG and SVG files, plus a commercial licence.",
                                 "theme": theme})
