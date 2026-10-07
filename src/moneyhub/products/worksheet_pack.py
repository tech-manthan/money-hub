"""Worksheet pack: printable worksheets with answer key (teacher/homeschool or self-guided exercises)."""
from __future__ import annotations

import random

from pydantic import BaseModel, Field

from ..niches import NicheProfile
from ..render.raster import pdf_page_count
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register


class Item(BaseModel):
    question: str
    choices: list[str] = Field(default_factory=list, description="Provide for multiple-choice items, else empty")
    answer: str = Field(description="The correct answer (or 'Answers will vary' for reflective items)")


class Sheet(BaseModel):
    title: str
    instructions: str
    items: list[Item] = Field(min_length=4, max_length=10)


class WorksheetContent(BaseModel):
    title: str
    subtitle: str = "Printable worksheet pack"
    tagline: str
    topic: str
    level: str = Field(description="e.g. 'Grades 2-3' or 'Self-guided'")
    sheets: list[Sheet] = Field(min_length=4, max_length=20)


_NOUNS = ["dog", "river", "teacher", "happiness", "city", "bicycle", "garden", "idea"]
_VERBS = ["run", "whisper", "build", "laugh", "carry", "paint", "jump", "explore"]
_ADJ = ["bright", "gentle", "enormous", "quiet", "sticky", "ancient", "clever", "cold"]


def _mult(rng: random.Random) -> Sheet:
    items = []
    for _ in range(8):
        a, b = rng.randint(2, 12), rng.randint(2, 12)
        items.append(Item(question=f"{a} x {b} = ____", answer=str(a * b)))
    return Sheet(title="Multiplication facts", instructions="Solve each multiplication fact. Work quickly but carefully.", items=items)


def _place_value(rng: random.Random) -> Sheet:
    items = []
    names = {0: "ones", 1: "tens", 2: "hundreds", 3: "thousands"}
    for _ in range(6):
        n = rng.randint(1000, 9999)
        pos = rng.randint(0, 3)
        digit = str(n)[-(pos + 1)]
        items.append(Item(question=f"What digit is in the {names[pos]} place of {n:,}?", answer=digit))
    return Sheet(title="Place value to 9,999", instructions="Read each number and write the digit in the place named.", items=items)


def _rounding(rng: random.Random) -> Sheet:
    items = []
    for _ in range(6):
        n = rng.randint(11, 989)
        to = rng.choice([10, 100])
        r = int(round(n / to + 1e-9)) * to
        if n % to == to // 2:  # round half up
            r = (n // to + 1) * to
        items.append(Item(question=f"Round {n} to the nearest {to}.", answer=str(r)))
    return Sheet(title="Rounding numbers", instructions="Round each number to the place shown. Remember: 5 or more rounds up.", items=items)


def _addition(rng: random.Random) -> Sheet:
    items = []
    for _ in range(8):
        a, b = rng.randint(120, 899), rng.randint(120, 899)
        items.append(Item(question=f"{a} + {b} = ____", answer=str(a + b)))
    return Sheet(title="Addition with regrouping", instructions="Add the numbers. Carry when you need to.", items=items)


def _fractions(rng: random.Random) -> Sheet:
    items = []
    for _ in range(6):
        d = rng.choice([2, 3, 4, 5, 6, 8])
        a, b = rng.sample(range(1, d), 2) if d > 2 else (1, 1)
        if a == b:
            b = a % (d - 1) + 1
        big = f"{max(a, b)}/{d}"
        items.append(Item(question=f"Which fraction is greater: {a}/{d} or {b}/{d}?", choices=[f"{a}/{d}", f"{b}/{d}"], answer=big))
    return Sheet(title="Comparing fractions", instructions="Tick the greater fraction in each pair. Same denominators: compare the numerators.", items=items)


def _parts_of_speech(rng: random.Random) -> Sheet:
    pool = [(w, "noun") for w in _NOUNS] + [(w, "verb") for w in _VERBS] + [(w, "adjective") for w in _ADJ]
    rng.shuffle(pool)
    items = [Item(question=f"'{w}' is a ...", choices=["noun", "verb", "adjective"], answer=k) for w, k in pool[:8]]
    return Sheet(title="Parts of speech", instructions="Tick whether each word is a noun, verb or adjective.", items=items)


_MATH = [_mult, _place_value, _rounding, _addition, _fractions, _parts_of_speech]


def _reflective(topic: str, niche: NicheProfile, rng: random.Random) -> Sheet:
    qs = [
        f"What does '{topic.lower()}' mean to me right now?",
        "What is one thing that is already working?",
        "What is getting in the way?",
        "What is the smallest next step I can take this week?",
        "Who or what could help me?",
        "How will I know I'm making progress?",
    ]
    return Sheet(title=topic, instructions="Take your time. There are no wrong answers - write what is true for you.",
                 items=[Item(question=q, answer="Answers will vary.") for q in qs])


@register
class WorksheetPack(ProductType[WorksheetContent]):
    key = "worksheet_pack"
    layouts = {"classic": "Classic: numbered boxes, directions card, two answer lines",
               "two_column": "Two columns: more questions side by side",
               "clean": "Clean: no boxes, plain numbers and generous answer lines",
               "roomy": "Roomy: four answer lines and one choice per line"}
    auto_layout = True
    layout_preview_page = 1
    label = "Worksheet pack"
    description = "Printable worksheets with directions and an answer key (classroom/homeschool or self-guided exercises)."
    content_model = WorksheetContent
    supported_sizes = ["letter", "a4", "eink"]
    price_range = (3.0, 9.0)
    typical_formats = "PDF"

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> WorksheetContent:
        if niche.key == "teacher":
            sheets = [fn(rng) for fn in _MATH]
            level, topic = "Grades 2-4", "Math & language practice"
        else:
            sheets = [_reflective(t, niche, rng) for t in niche.worksheet_topics[:6]]
            level, topic = "Self-guided", f"{niche.name} exercises"
        return WorksheetContent(title=f"{niche.name} Worksheet Pack", tagline=niche.tagline[:70], topic=topic, level=level, sheets=sheets)

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        grade = options.get("level")
        return (
            "Write a pack of 8 printable WORKSHEETS for this niche. Each sheet has a title, clear directions and 6-8 items "
            "with a correct answer for each (use 'Answers will vary' for reflective items). Mix multiple-choice (give choices) "
            "and open items. For school topics, every answer MUST be factually correct and age-appropriate"
            + (f" for {grade}." if grade else ".")
            + " Do not repeat questions."
        )

    def build(self, ctx: BuildContext, content: WorksheetContent) -> BuildResult:
        slug = self.slug(content.title)
        files, renderer, pages = [], "", 0
        jobs = [(ctx.page(s), ctx.out_dir / f"{slug}-{s}.pdf", {"content": content}) for s in ctx.sizes]
        renderer, lmeta = self.render_layout(ctx, "worksheets.html.j2", [(s, j[1]) for s, j in zip(ctx.sizes, jobs)], {"content": content}, _ws_css, margin=3.0)
        for page, out, _ in jobs:
            pages = pdf_page_count(out)
            files.append(ProductFile(out, "pdf", f"{page.label} - printable", True, preview_pages=[0, 1, 2, len(content.sheets) + 1]))
        features = [f"{len(content.sheets)} ready-to-print worksheets", "Complete answer key", f"Level: {content.level}",
                    "Print as many copies as you need", f"Created for {ctx.niche.audience}"]
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer, meta=lmeta)


def _ws_css(spec, page) -> str:
    q = 2.2 + spec.answer_lines * 1.9
    css = f".ws-q {{ min-height:{q:.1f}em; }}\n.ws-q.plain {{ border-bottom:1px solid var(--line); padding:.3em 0; }}\n"
    if spec.columns == 2:
        css += ".ws-grid { display:grid; grid-template-columns:1fr 1fr; grid-auto-rows:1fr; gap:.55em .9em; }\n"
    return css
