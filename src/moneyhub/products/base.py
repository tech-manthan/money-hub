"""Product-type framework."""
from __future__ import annotations

import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel

from ..design import Style
from ..llm import LLMRouter, get_router
from ..niches import NicheProfile
from ..render.html import PAGE_SIZES, PageSize, render_html
from ..render.pdf import render_many, render_pdf

log = logging.getLogger("moneyhub.products")
C = TypeVar("C", bound=BaseModel)


@dataclass
class ProductFile:
    path: Path
    kind: str          # pdf | xlsx | png | zip ...
    label: str         # shown in UI / listing ("US Letter PDF")
    primary: bool = True   # a deliverable the buyer receives
    preview_pages: list[int] = field(default_factory=list)  # page indexes good for mockups


@dataclass
class BuildResult:
    title: str
    subtitle: str
    files: list[ProductFile]
    features: list[str]          # bullets for listing / mockups
    page_count: int = 0
    renderer: str = ""
    meta: dict = field(default_factory=dict)


@dataclass
class BuildContext:
    niche: NicheProfile
    style: Style
    out_dir: Path
    sizes: list[str]
    seed: int
    router: LLMRouter = field(default_factory=get_router)
    providers: list[str] | None = None
    options: dict = field(default_factory=dict)

    @property
    def rng(self) -> random.Random:
        return random.Random(self.seed)

    def page(self, key: str) -> PageSize:
        return PAGE_SIZES[key]


class ProductType(ABC, Generic[C]):
    key: ClassVar[str]
    label: ClassVar[str]
    description: ClassVar[str]
    content_model: ClassVar[type[BaseModel]]
    default_sizes: ClassVar[list[str]] = ["letter", "a4"]
    supported_sizes: ClassVar[list[str]] = ["letter", "a4"]
    price_range: ClassVar[tuple[float, float]] = (4.0, 12.0)
    typical_formats: ClassVar[str] = "PDF"

    def size_options(self) -> list[tuple[str, str]]:
        """(key, label) choices offered in the UI/CLI for this product type."""
        return [(k, PAGE_SIZES[k].label) for k in self.supported_sizes if k in PAGE_SIZES]

    def size_label(self, key: str) -> str:
        return dict(self.size_options()).get(key, key).split(" (")[0]

    # --- content -----------------------------------------------------
    @abstractmethod
    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> C: ...

    @abstractmethod
    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        """Describe the content to generate (the router appends the JSON schema)."""

    def system_prompt(self, niche: NicheProfile) -> str:
        return (
            "You are a senior designer-copywriter who makes best-selling digital products for Etsy and Gumroad. "
            "Your content is specific, original and genuinely useful to the buyer; it never reads like generic filler. "
            f"Audience: {niche.audience}. Tone: {niche.tone}. Keep labels short enough to fit on a printed page."
        )

    def generate_content(self, ctx: BuildContext) -> tuple[C, str]:
        brief = self.llm_brief(ctx.niche, ctx.options)
        prompt = f"Niche profile (JSON):\n{ctx.niche.model_dump_json(indent=1)}\n\n{brief}"
        obj = ctx.router.complete_json(
            "content", self.system_prompt(ctx.niche), prompt, self.content_model, providers=ctx.providers,
        )
        if obj is not None:
            return obj, ctx.router.last_used or "llm"  # type: ignore[return-value]
        return self.builtin_content(ctx.niche, ctx.rng, ctx.options), "builtin"

    # --- build -------------------------------------------------------
    @abstractmethod
    def build(self, ctx: BuildContext, content: C) -> BuildResult: ...

    # --- helpers -----------------------------------------------------
    def pdf_from_template(self, ctx: BuildContext, template: str, page: PageSize, out: Path,
                          extra_css: str = "", margin: float = 3.4, **tctx) -> str:
        html = render_html(template, ctx.style, page, extra_css=extra_css, margin=margin, **tctx)
        return render_pdf(html, out, page_css_size=page.css_size)

    def render_jobs(self, ctx: BuildContext, template: str, jobs: list[tuple[PageSize, Path, dict]],
                    extra_css=None, margin: float = 3.4) -> str:
        """Render one PDF per (page, out_path, template_context) job, in parallel. extra_css may be a str or f(page)."""
        built = []
        for page, out, tctx in jobs:
            css = extra_css(page) if callable(extra_css) else (extra_css or "")
            built.append((render_html(template, ctx.style, page, extra_css=css, margin=margin, **tctx), out, page.css_size))
        names = render_many(built)
        return names[0] if names else ""

    @staticmethod
    def slug(text: str) -> str:
        import re
        return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
