"""Digital wall art prints: affirmation/quote posters in multiple print ratios, delivered as high-res JPG packs."""
from __future__ import annotations

import io
import random
import zipfile
from pathlib import Path

from pydantic import BaseModel, Field

from ..art import MOTIFS, generate_art, motif_svg
from ..niches import NicheProfile
from ..render.html import PageSize
from ..render.raster import render_pages
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register


class Quote(BaseModel):
    text: str = Field(description="Original affirmation/quote for the poster, 3-14 words, no famous quotes")
    small: str = Field(default="", description="Optional small script line under it (<= 5 words)")


class WallArtContent(BaseModel):
    title: str
    subtitle: str = "Printable wall art set"
    tagline: str
    quotes: list[Quote] = Field(min_length=4, max_length=12)


# name -> (inches wide, inches tall, pixel width, pixel height, sizes included)
RATIOS = {
    "2x3": (12, 18, 3600, 5400, "4x6, 8x12, 10x15, 12x18, 16x24, 20x30, 24x36 in"),
    "3x4": (12, 16, 3600, 4800, "6x8, 9x12, 12x16, 15x20, 18x24 in"),
    "4x5": (8, 10, 3200, 4000, "4x5, 8x10, 16x20 in"),
    "5x7": (10, 14, 3000, 4200, "5x7, 10x14, 15x21 in"),
    "ISO-A": (8.268, 11.693, 3508, 4961, "A5, A4, A3, A2, A1 (also 50x70 cm)"),
}


@register
class WallArt(ProductType[WallArtContent]):
    key = "wall_art"
    label = "Wall art set"
    description = "Set of typographic wall art prints with procedural artwork (optional AI backgrounds), as high-res JPG packs in 5 print ratios."
    content_model = WallArtContent
    default_sizes = list(RATIOS)
    supported_sizes = list(RATIOS)
    price_range = (4.0, 12.0)
    typical_formats = "High-resolution JPG (5 ratio packs, 300 DPI at A4)"

    def size_options(self):
        return [(k, f"{k.replace('x', ':')} ratio - {v[4]}") for k, v in RATIOS.items()]

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> WallArtContent:
        qs = list(niche.affirmations)
        rng.shuffle(qs)
        qs = (qs * 2)[:8]
        return WallArtContent(
            title=f"{niche.name} Wall Art Set", tagline=niche.tagline[:70],
            quotes=[Quote(text=q, small=niche.name.lower()) for q in qs],
        )

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return (
            "Write 8 ORIGINAL short poster texts (3-14 words each) for a printable wall art set aimed at this audience. "
            "They should feel like something this person would proudly hang in their space. Never use famous quotes or "
            "song lyrics. Optional small script line (<= 5 words)."
        )

    def build(self, ctx: BuildContext, content: WallArtContent) -> BuildResult:
        slug = self.slug(content.title)
        pal = ctx.style.palette
        rng = ctx.rng
        schemes = [(pal.paper, pal.ink, False), (pal.soft, pal.ink, False), (pal.accent, pal.accent_ink, True),
                   (pal.paper, pal.ink, False), (pal.soft, pal.ink, False), (pal.ink, pal.paper, True)]
        use_ai = bool(ctx.options.get("ai_art"))
        designs = []
        ai_used = ""
        for i, q in enumerate(content.quotes):
            bg, fg, dark = schemes[i % len(schemes)]
            motif = MOTIFS[(ctx.seed + i) % len(MOTIFS)]
            n = len(q.text)
            ai_bg = None
            if use_ai:
                made = generate_art(f"minimal abstract background art, soft shapes, {pal.key} colour palette, "
                                    "no text, no people, flat illustration, lots of empty space", (1024, 1536))
                if made:
                    p = ctx.out_dir.parent / "art" / f"ai-{i + 1}.png"
                    p.parent.mkdir(exist_ok=True)
                    made[0].save(p)
                    ai_bg, ai_used = p.as_uri(), made[1]
            designs.append({
                "text": q.text, "small": q.small, "bg": bg, "fg": fg, "layout": (i + ctx.seed) % 5,
                "svg": motif_svg(motif, pal, ctx.seed * 31 + i, on_dark=dark), "ai_bg": ai_bg,
                "fs": 5.4 if n <= 26 else 4.4 if n <= 56 else 3.6,
            })
        files: list[ProductFile] = []
        previews: list[Path] = []
        renderer = ""
        for ratio in ctx.sizes:
            if ratio not in RATIOS:
                continue
            w_in, h_in, px_w, px_h, _ = RATIOS[ratio]
            page = PageSize(ratio, ratio, w_in, h_in, 10.0 * w_in / 8.5)
            pdf = ctx.out_dir.parent / "art" / f"{slug}-{ratio}.pdf"
            pdf.parent.mkdir(exist_ok=True)
            renderer = self.render_jobs(ctx, "wall_art.html.j2", [(page, pdf, {"designs": designs})], extra_css=_css(designs), margin=0)
            scale = px_w / (w_in * 72)
            imgs = render_pages(pdf, list(range(len(designs))), scale=scale)
            zpath = ctx.out_dir / f"{slug}-{ratio}.zip"
            with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
                for i, im in enumerate(imgs):
                    quality = 92
                    while True:
                        buf = io.BytesIO()
                        im.save(buf, "JPEG", quality=quality, dpi=(300, 300), optimize=True)
                        if buf.tell() < 3_400_000 or quality <= 70:
                            break
                        quality -= 6
                    z.writestr(f"{slug}-{ratio}-{i + 1:02d}.jpg", buf.getvalue())
                    if ratio == "4x5":
                        pv = ctx.out_dir.parent / "art" / f"preview-{i + 1:02d}.png"
                        im.resize((1200, round(1200 * im.height / im.width))).save(pv)
                        previews.append(pv)
                z.writestr("READ-ME.txt",
                           f"{content.title}\nRatio {ratio.replace('x', ':')}: print at {RATIOS[ratio][4]}.\n"
                           "High-resolution JPG files, for personal use only. Colours vary by screen and printer.\n")
            files.append(ProductFile(zpath, "zip", f"{ratio.replace('x', ':')} ratio pack - {RATIOS[ratio][4]}", True))
        features = [
            f"{len(designs)} typographic art prints", "5 print ratios in one purchase", "Sizes: " + ", ".join(RATIOS[r][4].split(" in")[0] for r in list(RATIOS)[:2]) + " and more",
            "High-resolution JPG files (300 DPI at A4)", f"Made for {ctx.niche.audience}", "Instant download - no physical item shipped",
        ]
        return BuildResult(content.title, content.subtitle, files, features, len(designs), renderer,
                           meta={"art_previews": previews, "ai_provider": ai_used if use_ai else ""})


def _css(designs) -> str:
    rules = [
        ".page.art { display:block; padding:0; }",
        ".art .motif { position:absolute; display:block; }",
        ".art .motif svg { width:100%; height:100%; }",
        ".art .txt { position:absolute; text-align:center; font-family:var(--font-h); font-weight:700; line-height:1.14; }",
        ".art .txt.big { font-size:5.6em; }",
        ".art .small-t { position:absolute; text-align:center; font-family:var(--font-s); font-size:3em; opacity:.85; }",
        ".art .frame { position:absolute; left:6%; right:6%; top:4.5%; bottom:4.5%; border:3px solid; border-radius:var(--radius); opacity:.7; }",
        ".art .rule { position:absolute; left:44%; right:44%; height:4px; }",
    ]
    # font size per design (can't style by index in the template without inline CSS)
    for i, d in enumerate(designs):
        rules.append(f".page.art:nth-child({i + 1}) .txt:not(.big) {{ font-size:{d['fs']}em; }}")
    return "\n".join(rules)
