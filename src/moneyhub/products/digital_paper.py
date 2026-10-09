"""Digital paper pack: seamless 12 x 12 in patterns (3600 px, 300 DPI JPG) drawn by the pattern engine, with a commercial licence PDF.
Each paper repeats with no visible seam, so buyers can also use it as a tiled background."""
from __future__ import annotations

import io
import random
import zipfile
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image
from pydantic import BaseModel, Field

from ..config import get_config
from ..niches import NicheProfile
from ..patterns import KINDS, paper_svg, seam_excess
from ..render.pdf import render_many
from ..render import mockups
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register
from .wall_art import JPEG_BUDGET, srgb_profile

PATTERN_NAMES = {"dots": "Polka dots", "gingham": "Gingham", "stripes": "Candy stripes", "waves": "Wavy lines", "scallops": "Scallop scales", "arches": "Boho arches",
                 "terrazzo": "Terrazzo", "sparkles": "Sparkles", "leaves": "Leaf scatter", "diamonds": "Harlequin diamonds", "daisies": "Daisy meadow", "checks": "Checkerboard"}
SEAM_CHECKED = ("dots", "waves", "scallops", "arches", "terrazzo", "sparkles", "leaves", "diamonds", "daisies")   # stripes/gingham/checks have hard edges on the tile border by design
PX = 3600   # 12 in at 300 DPI
EACH_MAX = 2_500_000


class PaperContent(BaseModel):
    title: str
    subtitle: str = "12 seamless digital papers, 12 x 12 in"
    tagline: str = Field(description="One short, warm line (<= 70 chars)")
    names: list[str] = Field(min_length=len(KINDS), max_length=len(KINDS), description=f"{len(KINDS)} short pattern names (1-3 words), in the order of the pattern list in the brief")


@register
class DigitalPaper(ProductType[PaperContent]):
    key = "digital_paper"
    label = "Digital paper pack"
    description = "Seamless patterns as 12 x 12 in digital papers: 3600 px JPGs that tile with no visible seam, plus a commercial licence."
    content_model = PaperContent
    default_sizes = ["jpg"]
    supported_sizes = ["jpg"]
    price_range = (4.0, 12.0)
    typical_formats = "JPG 12 x 12 in (3600 px, 300 DPI) + licence PDF"
    niche_in_copy = False
    copy_audience = "scrapbookers, crafters, planner makers and small shops"
    title_suffix = " Digital Paper Pack"
    license_terms = ("Commercial use is included: use the papers as backgrounds and patterns in your own finished designs and products (printables, "
                     "scrapbook pages, cards, packaging, social posts) with no credit needed. You may not resell, share or redistribute the papers themselves "
                     "or include them in other paper packs, backgrounds or texture sets. Full terms are in the Commercial-License PDF inside the download.")
    license_faq = "Q: Can I use it for my business? A: Yes, commercial use is included. You may not resell or share the paper files themselves. See the licence PDF."
    how_steps = ("Purchase and download your files instantly.", "Unzip, then use the JPG papers as backgrounds in Canva, Photoshop, Procreate, scrapbooking and print apps.",
                 "Create and sell your own designs, following the included licence.")

    def size_options(self):
        return [("jpg", "12 x 12 in seamless JPG papers (3600 px) + licence PDF")]

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> PaperContent:
        return PaperContent(title="Seamless Digital Paper Pack", tagline="Patterns that repeat without a seam.", names=[PATTERN_NAMES[k] for k in KINDS])

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return ("Name the papers of a SEAMLESS DIGITAL PAPER pack. Give exactly "
                f"{len(KINDS)} short names (1-3 words) for these patterns, in this order: " + ", ".join(f"{k} ({PATTERN_NAMES[k]})" for k in KINDS)
                + ". Names describe the pattern, not an audience. Write a warm one-line tagline.")

    def build(self, ctx: BuildContext, content: PaperContent) -> BuildResult:
        pal = ctx.style.palette
        content = content.model_copy(update={"title": self.unique_title(ctx, f"{pal.key.replace('_', ' ').title()} Seamless")})   # named after the colour, never the niche
        slug = self.slug(content.title)
        count = max(len(KINDS), min(int(ctx.options.get("papers", len(KINDS))), 24))
        art_dir = ctx.out_dir.parent / "art"
        art_dir.mkdir(exist_ok=True)
        papers = [(KINDS[i % len(KINDS)], i // len(KINDS), content.names[i % len(KINDS)] + (f" {i // len(KINDS) + 1}" if i >= len(KINDS) else "")) for i in range(count)]

        jobs = []
        chunks = [papers[i:i + 6] for i in range(0, count, 6)]
        for n, chunk in enumerate(chunks):
            pages = "".join(f"<div class='p'>{paper_svg(k, pal, ctx.seed, v + n * 7 + KINDS.index(k), 2 + (KINDS.index(k) % 3))}</div>" for k, v, _ in chunk)
            html = ("<style>@page{size:12in 12in;margin:0}html,body{margin:0}.p{width:12in;height:12in;page-break-after:always}"
                    f".p svg{{width:12in;height:12in;display:block}}</style>{pages}")
            jobs.append((html, art_dir / f"{slug}-{n}.pdf", "12in 12in"))
        renderer = render_many(jobs)[0]

        jpgs: list[tuple[str, bytes]] = []
        thumbs: list[Image.Image] = []
        seam = 0.0
        for n, chunk in enumerate(chunks):
            doc = pdfium.PdfDocument(str(jobs[n][1]))
            try:
                for j, (kind, _, name) in enumerate(chunk):
                    im = doc[j].render(scale=PX / 864).to_pil().convert("RGB")
                    if im.size != (PX, PX):   # the rasteriser can round up by a pixel; the listing promises exactly 3600
                        im = im.resize((PX, PX), Image.LANCZOS)
                    if kind in SEAM_CHECKED:
                        seam = max(seam, seam_excess(im))
                    quality = 92
                    while True:
                        buf = io.BytesIO()
                        im.save(buf, "JPEG", quality=quality, dpi=(300, 300), optimize=True, icc_profile=srgb_profile())
                        if buf.tell() < EACH_MAX or quality <= 60:
                            break
                        quality -= 6
                    idx = n * 6 + j + 1
                    jpgs.append((f"{idx:02d}-{name.lower().replace(' ', '-')}.jpg", buf.getvalue()))
                    thumbs.append(im.resize((700, 700), Image.LANCZOS))
            finally:
                doc.close()

        groups: list[list[tuple[str, bytes]]] = []
        sizes: list[int] = []
        for item in jpgs:   # first-fit: each zip stays under Etsy's 20 MB per file
            for g, used in enumerate(sizes):
                if used + len(item[1]) <= JPEG_BUDGET:
                    groups[g].append(item)
                    sizes[g] += len(item[1])
                    break
            else:
                groups.append([item])
                sizes.append(len(item[1]))
        files: list[ProductFile] = []
        readme = (f"{content.title}\n\n{count} seamless papers, 12 x 12 in (3600 x 3600 px) at 300 DPI, JPG, sRGB. Each paper repeats with no visible seam.\n"
                  "See the Commercial-License PDF for what you may and may not do.\n")
        for g, items in enumerate(groups, 1):
            z = ctx.out_dir / (f"{slug}-JPG-12x12.zip" if len(groups) == 1 else f"{slug}-JPG-12x12-part-{g}.zip")
            with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
                for name, data in items:
                    zf.writestr(name, data)
                zf.writestr("READ-ME.txt", readme)
            files.append(ProductFile(z, "zip", f"{len(items)} seamless papers, 12 x 12 in JPG" + (f" (part {g} of {len(groups)})" if len(groups) > 1 else ""), True))

        cfg = get_config()
        license_pdf = ctx.out_dir / "Commercial-License.pdf"
        self.render_jobs(ctx, "clipart_license.html.j2", [(ctx.page("letter"), license_pdf, {
            "title": content.title, "count": count, "noun": "digital papers",
            "uses": "finished designs and products you sell: printables, scrapbook pages, planners, cards, invitations, social posts, websites and packaging",
            "shop": {k: (cfg.get(f"shop.{k}") or "") for k in ("name", "email", "url")}})], margin=3.0)
        files.append(ProductFile(license_pdf, "pdf", "Commercial licence (PDF)", True, preview_pages=[0]))

        features = [f"{count} seamless digital papers", "12 x 12 in, 3600 x 3600 px, 300 DPI JPG", "Each paper repeats with no visible seam",
                    "Commercial use included, no credit needed", "Instant download - works in Canva, Procreate, Photoshop and scrapbook apps"]
        return BuildResult(content.title, content.subtitle, files, features, count, renderer,
                           meta={"art_previews": _previews(art_dir, pal, thumbs), "mockup_tiles": mockups.save_tiles(art_dir, thumbs[::2]), "flat_art": True, "badges": ["Instant download", "Seamless JPG", "Commercial use"],
                                 "delivery_note": "Instant download: seamless 12 x 12 in JPG papers, plus a commercial licence.", "seam_excess": round(seam, 1)})


def _previews(art_dir: Path, pal, thumbs: list[Image.Image]) -> list[Path]:
    """Contact sheets of 6 papers, plus a 2 x 2 repeat of one paper that shows there is no seam."""
    sheets: list[Image.Image] = []
    for start in range(0, len(thumbs), 6):
        sheet = Image.new("RGB", (1200, 1500), pal.paper)
        for k, t in enumerate(thumbs[start:start + 6]):
            sheet.paste(t.resize((440, 440), Image.LANCZOS), (100 + (k % 2) * 520, 110 + (k // 2) * 470))
        sheets.append(sheet)
    for idx in (3, 9):   # repeat demos: the join between copies is invisible
        if idx < len(thumbs):
            demo = Image.new("RGB", (1200, 1500), pal.soft)
            t = thumbs[idx].resize((540, 540), Image.LANCZOS)
            for i in range(2):
                for j in range(2):
                    demo.paste(t, (60 + i * 540, 210 + j * 540))
            sheets.append(demo)
    paths = []
    for n, im in enumerate(sheets[:6], 1):
        p = art_dir / f"preview-{n:02d}.png"
        im.save(p)
        paths.append(p)
    return paths
