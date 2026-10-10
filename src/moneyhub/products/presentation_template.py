"""Editable slide-deck template (.pptx): 12 widescreen slides built with the deckcraft tool, plus a PDF preview and an editing guide.
Niche-free: the deck is the same set of slide types in a different palette and font pair each time. Needs deckcraft installed
(scripts/install_craft_tools.sh); the craft on/off switches do not matter because making this product is the explicit request."""
from __future__ import annotations

import random

from PIL import Image
from pydantic import BaseModel, Field

from .. import presentations
from ..config import get_config
from ..niches import NicheProfile
from ..render import mockups
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register

SLIDE_NAMES = "title, agenda, section, two columns, quote, key numbers, process, image gallery, before and after, team, pricing and thank you"


class DeckContent(BaseModel):
    title: str
    subtitle: str = "Editable slide template: 12 widescreen slides"
    tagline: str = Field(description="One short line (<= 70 chars)")


def _previews(art_dir, pal, ims: list[Image.Image]) -> list:
    """Portrait overview sheets for the listing photos (the slides themselves are landscape): two sheets of six slides, one big sheet of two."""
    sheets = []
    for idx in ((0, 1, 2, 3, 4, 5), (6, 7, 8, 9, 10, 11)):
        sh = Image.new("RGB", (1200, 1500), pal.soft)
        for k, i in enumerate(idx):
            sh.paste(ims[i].resize((520, 292), Image.LANCZOS), (60 + (k % 2) * 560, 240 + (k // 2) * 360))
        sheets.append(sh)
    big = Image.new("RGB", (1200, 1500), pal.soft)
    for k, i in enumerate((0, 6)):
        big.paste(ims[i].resize((1000, 562), Image.LANCZOS), (100, 160 + k * 640))
    sheets.append(big)
    paths = []
    for n, sh in enumerate(sheets, 1):
        p = art_dir / f"preview-{n:02d}.png"
        sh.save(p)
        paths.append(p)
    return paths


@register
class PresentationTemplate(ProductType[DeckContent]):
    key = "presentation_template"
    label = "Presentation template"
    description = "Editable 12-slide widescreen deck (.pptx) for PowerPoint, Keynote and Google Slides, with a PDF preview and an editing guide."
    content_model = DeckContent
    default_sizes = ["deck"]
    supported_sizes = ["deck"]
    price_range = (5.0, 15.0)
    typical_formats = "PPTX (16:9, 12 slides) + PDF preview"
    niche_in_copy = False
    copy_audience = "small businesses, teachers, students, freelancers and creators"
    title_suffix = " Presentation Template"
    license_terms = ("Use the template for your own presentations. You may not resell, share or redistribute the template file or edited copies of it as a template. "
                     "Fonts are free Google Fonts and are not included.")
    license_faq = "Q: Can I edit everything? A: Yes. Every text box, shape and colour is editable. Q: Does it work in Google Slides? A: Yes, upload the .pptx."
    extra_tags = ("business template", "small business", "presentation")
    use_faq = "Q: Which apps can I use? A: Any app that opens .pptx files: PowerPoint, Keynote, Google Slides and LibreOffice Impress."
    how_steps = ("Purchase and download your files instantly.", "Install the free fonts named in the Editing Guide PDF, then open the .pptx in PowerPoint, Keynote or Google Slides.",
                 "Replace the sample text and pictures with your own. Personal and own-business use.")

    def size_options(self):
        return [("deck", "Widescreen 16:9 slides (.pptx) + PDF preview")]

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> DeckContent:
        return DeckContent(title="Clean Minimal Presentation Template", tagline="Twelve slides you can edit in minutes.")

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return ("Write a short title and one-line tagline for an editable PRESENTATION TEMPLATE (12 widescreen slides: title, agenda, section, columns, quote, numbers, process, "
                "gallery, comparison, team, pricing, thank you). End the title with 'Presentation Template'. Do not mention any niche, profession or software brand.")

    def build(self, ctx: BuildContext, content: DeckContent) -> BuildResult:
        pal = ctx.style.palette
        content = content.model_copy(update={"title": self.unique_title(ctx, f"{pal.key.replace('_', ' ').title()} Clean")})   # named after the colour, never the niche
        slug = self.slug(content.title)
        art_dir = ctx.out_dir.parent / "art"
        art_dir.mkdir(exist_ok=True)
        pptx = ctx.out_dir / f"{slug}.pptx"
        ok, n, msg = presentations.build_deck(ctx.style, pptx, art_dir / "slides")
        if not ok:
            raise ValueError(f"Could not build the slide deck: {msg}")
        pngs = sorted((art_dir / "slides").glob("slide-*.png"))
        ims = [Image.open(p).convert("RGB") for p in pngs]
        preview = ctx.out_dir / f"{slug}-preview.pdf"
        pages = [im.resize((1280, 720), Image.LANCZOS) for im in ims]
        pages[0].save(preview, "PDF", resolution=96, save_all=True, append_images=pages[1:])

        cfg = get_config()
        start = ctx.out_dir / "Editing-Guide-and-License.pdf"
        self.render_jobs(ctx, "presentation_start.html.j2", [(ctx.page("letter"), start, {
            "title": content.title, "slides": n, "names": SLIDE_NAMES, "heading": presentations.family(ctx.style.fonts.heading), "body": presentations.family(ctx.style.fonts.body),
            "shop": {k: (cfg.get(f"shop.{k}") or "") for k in ("name", "email", "url")}})], margin=3.0)
        files = [ProductFile(pptx, "pptx", f"Editable slides, {n} widescreen slides (.pptx)", True),
                 ProductFile(preview, "pdf", "PDF preview of all slides", True, preview_pages=[0, 1, 5, 6, 8, 10]),
                 ProductFile(start, "pdf", "Editing guide and licence (fonts, how to edit)", True, preview_pages=[0])]
        features = [f"{n} editable widescreen (16:9) slides", f"Slide types: {SLIDE_NAMES}", "Every text box, shape and colour is editable",
                    "Works in PowerPoint, Keynote and Google Slides (.pptx)", f"Free Google Fonts ({presentations.family(ctx.style.fonts.heading)} and {presentations.family(ctx.style.fonts.body)}), not included",
                    "PDF preview and an editing guide", "Instant download - no physical item shipped"]
        return BuildResult(content.title, content.subtitle, files, features, n, "deckcraft",
                           meta={"min_pages": 3, "flat_art": True, "art_previews": _previews(art_dir, pal, ims), "slides": n, "pptx": pptx.name, "etsy_category": "an editable slide template is not a printable: search Etsy for your closest match (digital templates are usually found under **Paper & Party Supplies** or **Craft Supplies & Tools**) and copy the category of similar best-selling slide-deck listings.", "badges": ["Instant download", "Editable PPTX", "16:9 widescreen"],
                                 "delivery_note": "Instant download: an editable .pptx deck, a PDF preview and an editing guide.",
                                 "mockup_tiles": mockups.save_tiles(art_dir, [ims[i] for i in (0, 5, 6, 10)], 4)})
