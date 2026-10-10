"""Classroom printables: name tags, desk plates, reward / behaviour / chore charts, an undated monthly calendar, a birthday chart and
star-of-the-week posters. Pictures come from the kids library (any theme); names can be pre-printed or left to write in. Letter / A4 PDF."""
from __future__ import annotations

import random
import re

from pydantic import BaseModel, Field

from .. import kidsart
from ..niches import NicheProfile
from ..render.raster import pdf_page_count
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register

MAX_NAMES = 30
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
WEEK = DAYS + ["Sat", "Sun"]


class ClassroomContent(BaseModel):
    title: str
    subtitle: str = "Name tags, charts, calendar and more"
    tagline: str = Field(description="One short, warm line (<= 70 chars)")


def parse_names(raw) -> list[str]:
    """Student names from a comma / semicolon / newline separated string (or list): trimmed, de-duplicated, 20 characters each."""
    parts = raw if isinstance(raw, (list, tuple)) else re.split(r"[,;\n]+", str(raw or ""))
    names = list(dict.fromkeys(re.sub(r"\s+", " ", str(p)).strip()[:20] for p in parts if str(p).strip()))
    if len(names) > MAX_NAMES:
        raise ValueError(f"Too many names ({len(names)}): the most one set can hold is {MAX_NAMES}. Make a second set for the rest.")
    return names


def _theme(options: dict) -> str:
    t = str(options.get("theme") or "mixed")
    if t not in kidsart.THEMES:
        raise ValueError(f"unknown theme '{t}'. Choose one of: {', '.join(kidsart.THEMES)}")
    return t


def _face(mood: int) -> str:
    """A simple face for the behaviour chart: 0 happy, 1 so-so, 2 sad (a 100 x 100 SVG)."""
    mouth = {0: "M30 62 Q50 82 70 62", 1: "M32 68 L68 68", 2: "M30 76 Q50 54 70 76"}[mood]
    return ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='44' fill='white' stroke='#222' stroke-width='5'/>"
            f"<circle cx='36' cy='40' r='5' fill='#222'/><circle cx='64' cy='40' r='5' fill='#222'/><path d='{mouth}' fill='none' stroke='#222' stroke-width='5' stroke-linecap='round'/></svg>")


@register
class ClassroomPack(ProductType[ClassroomContent]):
    key = "classroom_pack"
    label = "Classroom printables"
    description = ("Name tags, desk plates, reward, behaviour and chore charts, a monthly calendar set, a birthday chart and star-of-the-week posters "
                   "with kids-library pictures. Names pre-printed or left to write in (PDF).")
    content_model = ClassroomContent
    default_sizes = ["letter", "a4"]
    supported_sizes = ["letter", "a4"]
    price_range = (3.0, 8.0)
    typical_formats = "PDF (Letter and A4, printable)"
    niche_in_copy = False
    copy_audience = "teachers and homeschool parents"
    title_suffix = " Classroom Printables"
    how_steps = ("Purchase and download your files instantly.", "Print what you need at Actual size (cardstock suits tags and plates), then cut along the dashed lines.",
                 "Write names in with a marker, or make a set with your class list so the names are printed for you. Print as often as you like for your own classroom.")

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> ClassroomContent:
        theme = kidsart.THEMES[_theme(options)][0]
        return ClassroomContent(title=f"{theme} Classroom Printables", subtitle="Name tags, charts, calendar and more",
                                tagline="Everything for a tidy, friendly classroom, ready to print.")

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return (f"Write a short cheerful title and tagline for a set of CLASSROOM PRINTABLES (name tags, desk plates, reward and behaviour charts, calendar, birthday chart), "
                f"picture theme '{kidsart.THEMES[_theme(options)][0]}'. End the title with 'Classroom Printables'. Do not mention any niche or profession.")

    def build(self, ctx: BuildContext, content: ClassroomContent) -> BuildResult:
        theme = _theme(ctx.options)
        names = parse_names(ctx.options.get("names"))
        content = content.model_copy(update={"title": self.unique_title(ctx, content.title)})
        slug = self.slug(content.title)
        pool = list(dict.fromkeys(kidsart.THEMES[theme][1] if theme != "mixed" else kidsart.KINDS))
        random.Random(ctx.seed).shuffle(pool)
        counter = [0]

        def pic() -> str:
            k = pool[counter[0] % len(pool)]
            counter[0] += 1
            return f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 1000'>{kidsart.figure(k, ctx.seed * 811 + counter[0], 14, False)}</svg>"

        sheets: list[dict] = []
        tag_items = [{"svg": pic(), "name": n} for n in names] if names else [{"svg": pic(), "name": ""} for _ in range(24)]
        for i in range(0, len(tag_items), 8):
            sheets.append({"kind": "tags", "items": tag_items[i:i + 8]})
        plate_items = [{"svg": pic(), "name": n} for n in names] if names else [{"svg": pic(), "name": ""} for _ in range(4)]
        for i in range(0, len(plate_items), 2):
            sheets.append({"kind": "plates", "items": plate_items[i:i + 2]})
        for variant in ("stars", "steps", "grid", "tally"):
            sheets.append({"kind": "reward", "variant": variant, "svg": pic()})
        sheets += [{"kind": "behaviour", "svg": pic()}, {"kind": "faces", "svg": pic()}, {"kind": "chores", "svg": pic()}]
        sheets += [{"kind": "calendar", "month": m, "svg": pic()} for m in MONTHS]
        sheets += [{"kind": "birthday", "svg": pic()}, {"kind": "star", "svg": pic()}, {"kind": "star", "svg": pic()}]

        tctx = {"content": content, "sheets": sheets, "weekdays": WEEK, "days": DAYS, "faces": [_face(i) for i in range(3)],
                "named": bool(names), "chips": [f"{len(sheets)} printable pages", "Names printed or written in", "Letter & A4"]}
        jobs = [(ctx.page(s), ctx.out_dir / f"{slug}-{s}.pdf", tctx) for s in ctx.sizes]
        renderer = self.render_jobs(ctx, "classroom.html.j2", jobs, margin=0)
        files, pages = [], 0
        for page, out, _ in jobs:
            pages = pdf_page_count(out)
            files.append(ProductFile(out, "pdf", f"{page.label} - printable", True, preview_pages=[0, 2, 4, 6, 8, 12]))
        who = f"{len(names)} names pre-printed" if names else "Name lines to write in (24 tags, 4 desk plates)"
        features = [f"{pages} printable pages", f"Name tags (8 per sheet) and fold-over desk plates: {who}",
                    "4 reward charts, a weekly behaviour chart, a faces chart and a chore chart", "12 undated monthly calendar pages",
                    "Birthday chart and star-of-the-week posters", "US Letter and A4 PDF", "Instant download - no physical item shipped"]
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer,
                           meta={"pages": pages, "theme": theme, "names": len(names)})
