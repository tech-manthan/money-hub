"""End-to-end generation: niche + product type -> files, images, listing kit, guides, QA, catalog entry."""
from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .config import get_config
from .design import choose_style
from .listing.guides_render import MARKETPLACES, render_guides
from .listing.images import make_images
from .listing.kit import ListingKit, make_kit
from .llm import get_router
from .niches import NicheProfile, resolve_niche, smart_resolve
from .products import get_product_type
from .products.base import BuildContext, BuildResult
from . import risk as riskmod
from .qa import Check, media_checks, run_checks, summarize
from .startpage import build_start_page
from .store import Store
from .uniqueness import fingerprint_text, most_similar

log = logging.getLogger("moneyhub.pipeline")


@dataclass
class Request:
    niche: str
    product_type: str
    sizes: list[str] | None = None
    seed: int | None = None
    palette: str | None = None
    fonts: str | None = None
    providers: list[str] | None = None        # override LLM chain for this run
    marketplaces: list[str] = field(default_factory=lambda: ["etsy", "gumroad", "payhip", "kofi", "pinterest"])
    options: dict = field(default_factory=dict)
    with_images: bool = True
    with_video: bool = True
    motion: list[str] | None = None            # video engine chain override, e.g. ["remotion", "pillow"]


@dataclass
class Result:
    product_id: int
    folder: Path
    title: str
    qa_status: str
    checks: list[Check]
    similar: tuple[float, int | None, str]
    content_source: str
    listing_source: str


def generate(req: Request, progress: Callable[[str], None] | None = None, store: Store | None = None) -> Result:
    say = progress or (lambda m: None)
    cfg = get_config()
    store = store or Store()
    router = get_router()
    ptype = get_product_type(req.product_type)
    say("Researching niche profile")
    if req.options.get("no_research"):
        niche, niche_source = resolve_niche(req.niche), "generic"
    else:
        niche, niche_source = smart_resolve(req.niche, router, req.providers)
    say(f"Niche profile: {niche.name} ({niche_source})")
    seed = req.seed if req.seed is not None else random.SystemRandom().randrange(1, 10**6)
    style = choose_style(seed=seed, mood=niche.mood, palette=req.palette, fonts=req.fonts)
    sizes = [s for s in (req.sizes or ptype.default_sizes) if s in ptype.supported_sizes] or ptype.default_sizes

    stamp = time.strftime("%Y%m%d-%H%M%S")
    folder = cfg.output_dir / "products" / f"{stamp}-{niche.key}-{ptype.key}"
    pdir = folder / "product"
    pdir.mkdir(parents=True, exist_ok=True)

    ctx = BuildContext(niche=niche, style=style, out_dir=pdir, sizes=sizes, seed=seed, router=router,
                       providers=req.providers, options=req.options)
    say(f"Writing content ({'LLM' if router.status() else 'offline'} chain)")
    content, content_source = ptype.generate_content(ctx)
    say(f"Content from {content_source}; rendering files")
    build: BuildResult = ptype.build(ctx, content)

    start = build_start_page(build, style, pdir, ptype.key, niche.key, req.options.get("gsheet_url"))
    if start:
        build.files.insert(0, start)

    say("Checking for similar existing products")
    fp = fingerprint_text(content.model_dump_json())
    similar = most_similar(fp, store.fingerprints())

    say("Writing listing copy")
    kit: ListingKit = make_kit(niche, ptype, build, router, random.Random(seed), providers=req.providers)
    labels = [ptype.size_label(s) for s in sizes]
    images: dict[str, list[Path]] = {}
    if req.with_images:
        say("Creating listing images and pins")
        images = make_images(build, style, folder, ptype.key, kit.copy_, labels, router=router, niche=niche,
                             providers=req.providers, videos=req.with_video and bool(cfg.get("render.videos", True)),
                             motion_engines=req.motion)
    say("Writing marketplace guides")
    render_guides(folder, kit, build, images, style.palette.key, req.marketplaces)
    (folder / "listing").mkdir(exist_ok=True)
    (folder / "listing" / "listing.json").write_text(kit.model_dump_json(indent=2), encoding="utf-8")
    (folder / "listing" / "etsy-description.txt").write_text(kit.description, encoding="utf-8")
    (folder / "listing" / "etsy-tags.txt").write_text(", ".join(kit.copy_.tags), encoding="utf-8")
    pins = [{"title": t, "headline": h} for t, h in zip(kit.copy_.pin_titles, kit.copy_.pin_headlines)]
    (folder / "listing" / "pins.json").write_text(json.dumps({"description": kit.copy_.pin_description, "pins": pins}, indent=2), encoding="utf-8")

    say("Running quality checks")
    checks = run_checks(build, style, sizes) + media_checks(folder)
    if similar[0] >= 0.6:
        checks.append(Check("Uniqueness", "warn", f"{similar[0]:.0%} similar to existing product #{similar[1]} '{similar[2]}' - change niche angle or regenerate"))
    else:
        checks.append(Check("Uniqueness", "pass", f"closest existing product is {similar[0]:.0%} similar"))
    findings = riskmod.scan_listing(json.loads(kit.model_dump_json()), content.model_dump_json(), req.niche)
    top = riskmod.status(findings)
    checks.append(Check("Risk check (brands, claims, rights language)", top if top != "pass" else "pass",
                        "nothing on the watch list" if not findings else "; ".join(f"{f.where}: '{f.term}' ({f.severity})" for f in findings[:6])))
    if findings:
        (folder / "listing" / "risk.json").write_text(json.dumps([f.to_dict() for f in findings], indent=2), encoding="utf-8")
    qa_status = summarize(checks)

    (folder / "spec.json").write_text(json.dumps({
        "request": {"niche": req.niche, "product_type": req.product_type, "sizes": sizes, "seed": seed, "options": req.options},
        "style": style.describe(), "niche_source": niche_source, "content_source": content_source, "listing_source": kit.source,
        "content": json.loads(content.model_dump_json()),
    }, indent=2), encoding="utf-8")

    pid = store.add_product(
        slug=folder.name, title=build.title, niche=niche.key, niche_name=niche.name, product_type=ptype.key,
        style=style.key, status="draft", folder=str(folder), price=kit.price, qa=[c.to_dict() for c in checks],
        fingerprint=fp, content_source=content_source, listing_source=kit.source,
        spec=json.dumps({"seed": seed, "sizes": sizes, "style": style.describe()}),
    )
    make_package(folder)
    say("Done")
    return Result(pid, folder, build.title, qa_status, checks, similar, content_source, kit.source)


def make_package(folder: Path) -> Path:
    """Zip everything you need to upload (product files, images, guides) into one file."""
    import zipfile

    zpath = folder / "upload-package.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for sub in ("product", "images", "listing"):
            for f in sorted((folder / sub).rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(folder))
    return zpath
