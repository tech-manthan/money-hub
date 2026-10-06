"""Digital wall art prints: affirmation/quote posters in multiple print ratios, delivered as high-res JPG packs."""
from __future__ import annotations

import io
import math
import random
import tempfile
import zipfile
from pathlib import Path

from pydantic import BaseModel, Field

from .. import layouts as lay
from ..config import get_config
from ..art import MOTIFS, SVG_PROVIDERS, generate_art, motif_svg
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
    layouts = {"stacked": "Stacked: big artwork on top, text underneath",
               "headline": "Headline: text first, artwork along the bottom",
               "framed": "Framed: a thin border, small artwork, centred text",
               "poster": "Poster: artwork bleeding off the top, big left-aligned text",
               "divided": "Divided: small artwork, a divider line, then the text",
               "mixed": "Mixed: a different layout on each poster"}
    auto_layout = True
    layout_marker = ""

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

    def layout_preview_image(self, ctx: BuildContext, content: WallArtContent):
        """One poster in the chosen layout, for the wizard thumbnails (the real build makes zip packs, not a PDF)."""
        designs, _ = make_designs(content.model_copy(update={"quotes": content.quotes[:1] * 4}), ctx.style, ctx.seed, layout=self.layout_of(ctx),
                                  layout_spec=ctx.options.get("layout_spec"))
        w_in, h_in = RATIOS["4x5"][:2]
        page = PageSize("4x5", "4x5", w_in, h_in, 10.0 * w_in / 8.5)
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "p.pdf"
            self.render_jobs(ctx, "wall_art.html.j2", [(page, pdf, {"designs": designs[:1]})], extra_css=_css(), margin=0)
            return render_pages(pdf, [0], scale=0.9)[0]

    def build(self, ctx: BuildContext, content: WallArtContent) -> BuildResult:
        slug = self.slug(content.title)
        pal = ctx.style.palette
        use_ai = bool(ctx.options.get("ai_art"))
        designs, ai_used = make_designs(content, ctx.style, ctx.seed, use_ai, ctx.out_dir.parent / "art",
                                        motif=ctx.options.get("motif"), layout=self.layout_of(ctx),
                                        layout_spec=ctx.options.get("layout_spec"), art_providers=ctx.options.get("art_providers"))
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
            renderer = self.render_jobs(ctx, "wall_art.html.j2", [(page, pdf, {"designs": designs})], extra_css=_css(), margin=0)
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


def style_audience(style) -> str:
    return "people who love printable art"


def style_mood(pal) -> str:
    return ", ".join(pal.mood)


def make_designs(content: "WallArtContent", style, seed: int, use_ai: bool = False, art_dir: Path | None = None,
                 motif: str | None = None, layout: str | None = None, layout_spec: dict | None = None,
                 art_providers: list[str] | None = None) -> tuple[list[dict], str]:
    """Colour scheme, motif and layout for every poster. Deterministic for a given seed.
    layout is a key from WallArt.layouts, "auto:<n>" or "custom" (with layout_spec); the default is the first preset."""
    pal = style.palette
    schemes = [(pal.paper, pal.ink, False), (pal.soft, pal.ink, False), (pal.accent, pal.accent_ink, True),
               (pal.paper, pal.ink, False), (pal.soft, pal.ink, False), (pal.ink, pal.paper, True)]
    designs, ai_used = [], ""
    chain = list(art_providers or get_config().get("render.art") or ["claude_svg"]) if use_ai else []
    presets = list(lay.ART_PRESETS.values())
    fixed = None if layout == "mixed" else lay.resolve("wall_art", layout, {"layout_spec": layout_spec} if layout_spec else None, seed)
    drawn: list[str] = []   # motifs drawn by the writing model, reused across the posters
    if "claude_svg" in chain and SVG_PROVIDERS["claude_svg"].available():
        drawn = SVG_PROVIDERS["claude_svg"].motifs(pal, style_audience(style), style_mood(pal))
        ai_used = "claude_svg" if drawn else ai_used
    image_chain = [n for n in chain if n != "claude_svg"]
    for i, q in enumerate(content.quotes):
        bg, fg, dark = schemes[i % len(schemes)]
        kind = motif or MOTIFS[(seed + i) % len(MOTIFS)]
        spec = fixed or presets[(i + seed) % len(presets)]
        boxes = lay.art_boxes(spec)
        fs, text_top = fit_text(q.text, boxes)
        ai_bg = None
        if image_chain and art_dir is not None:
            made = generate_art(f"minimal abstract background art, soft shapes, {pal.key} colour palette, "
                                "no text, no people, flat illustration, lots of empty space", (1024, 1536), image_chain)
            if made:
                art_dir.mkdir(exist_ok=True)
                p = art_dir / f"ai-{i + 1}.png"
                made[0].save(p)
                ai_bg, ai_used = p.as_uri(), made[1]
        designs.append({
            "text": q.text, "small": q.small, "bg": bg, "fg": fg, "b": boxes, "text_top": text_top, "layout": spec.name,
            "svg": drawn[i % len(drawn)] if drawn else motif_svg(kind, pal, seed * 31 + i, on_dark=dark), "ai_bg": ai_bg,
            "fs": fs,
        })
    return designs, ai_used


PAGE_EM_W = 61.2   # page width in em: the page's base font is 10 * width_in / 8.5 pt
MIN_ASPECT = 1.25   # the squattest print ratio (4:5); text that fits there fits on every taller one


def fit_text(text: str, boxes: dict) -> tuple[float, float]:
    """Font size (em) and top (percent of page height) that keep the text inside its region on every print ratio."""
    n, region = len(text), boxes["text"]
    big = boxes["align"] == "left" and region["anchor"] == "bottom"
    fs = (5.6 if n <= 26 else 4.6 if n <= 56 else 3.8) if big else (5.4 if n <= 26 else 4.4 if n <= 56 else 3.6)
    width_em = PAGE_EM_W * (100 - 2 * boxes["margin"]) / 100
    room = region["t1"] - region["t0"]
    while True:
        lines = math.ceil(n * fs * 0.55 * 1.1 / width_em)
        height = lines * fs * 1.14 / (PAGE_EM_W * MIN_ASPECT) * 100
        if height <= room or fs <= 2.4:
            break
        fs = round(fs - 0.2, 1)
    top = {"top": region["t0"], "bottom": region["t1"] - height, "middle": (region["t0"] + region["t1"] - height) / 2}[region["anchor"]]
    return fs, round(top, 1)


def _css() -> str:
    return "\n".join([
        ".page.art { display:block; padding:0; }",
        ".art .motif { position:absolute; display:block; }",
        ".art .motif svg { width:100%; height:100%; }",
        ".art .txt { position:absolute; font-family:var(--font-h); font-weight:700; line-height:1.14; }",
        ".art .small-t { position:absolute; text-align:center; font-family:var(--font-s); font-size:3em; opacity:.85; }",
        ".art .frame { position:absolute; left:6%; right:6%; top:4.5%; bottom:4.5%; border:3px solid; border-radius:var(--radius); opacity:.7; }",
        ".art .rule { position:absolute; left:44%; right:44%; height:4px; }",
    ])
