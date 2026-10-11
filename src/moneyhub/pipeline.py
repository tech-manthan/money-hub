"""End-to-end generation: niche + product type -> files, images, listing kit, guides, QA, catalog entry."""
from __future__ import annotations

import json
import logging
import random
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .config import get_config
from . import decor
from .design import choose_style
from .listing.guides_render import MARKETPLACES, render_guides
from .listing.images import make_images
from .listing.kit import ListingKit, make_kit
from .llm import get_router
from .niches import NicheProfile, resolve_niche, smart_resolve
from .products import all_product_types, get_product_type
from .products.base import BuildContext, BuildResult
from . import risk as riskmod
from .qa import Check, media_checks, run_checks, summarize
from .startpage import build_start_page
from .store import Store
from .uniqueness import CROSS_TYPE_THRESHOLD, content_signature, cross_type_match, most_similar

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


def _decoration(req, niche, ptype, style, say):
    """Apply the optional page decoration to the look. Explicit options on an unsupported product are an error; defaults from moneyhub.yaml
    are simply skipped there. E-ink pages stay plain."""
    given = {k: v for k, v in req.options.items() if k.startswith("decor_") and v}
    d = decor.from_options(req.options, niche.key, f"{niche.name} {niche.audience}", get_config().get("decor") or {})
    if not d.active:
        return None
    if not ptype.decor_ok:
        if given:
            raise ValueError(f"{ptype.label} has no page decoration. It works with: " + ", ".join(k for k, t in all_product_types().items() if t.decor_ok))
        return None
    if req.options.get("eink"):
        say("E-ink pages are black and white, so the decoration is left off")
        return None
    style.extra["decor"] = d.as_dict()
    say("Decorating the pages: " + (decor.describe(d) or "on").lower().replace("decorated pages: ", ""))
    return d


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
    style = choose_style(seed=seed, mood=niche.mood, palette=req.palette, fonts=req.fonts,
                         header=req.options.get("header"), radius=req.options.get("radius"), grid=req.options.get("grid"),
                         brand=req.options.get("brand"), eink=bool(req.options.get("eink")))
    sizes = [s for s in (req.sizes or ptype.default_sizes) if s in ptype.supported_sizes] or ptype.default_sizes
    if req.options.get("eink"):
        if "eink" not in ptype.supported_sizes:
            raise ValueError(f"{ptype.label} has no e-ink version. E-ink works with: weekly_planner, daily_planner, guided_journal, "
                             "checklist_pack, worksheet_pack, ebook_guide")
        sizes = ["eink"]

    dec = _decoration(req, niche, ptype, style, say)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    base = f"{stamp}-{niche.key}-{ptype.key}"
    folder, n = cfg.output_dir / "products" / base, 1
    while folder.exists():  # same-second runs must not share (and overwrite) a folder
        n += 1
        folder = cfg.output_dir / "products" / f"{base}-{n}"
    pdir = folder / "product"
    pdir.mkdir(parents=True, exist_ok=True)

    try:
        ctx = BuildContext(niche=niche, style=style, out_dir=pdir, sizes=sizes, seed=seed, router=router,
                           providers=req.providers, options=req.options,
                           taken_titles=frozenset(t.lower() for _, t, _ in store.fingerprints()))
        say(f"Writing content ({'LLM' if router.status() else 'offline'} chain)")
        content, content_source = ptype.generate_content(ctx)
        say(f"Content from {content_source}; rendering files")
        build: BuildResult = ptype.build(ctx, content)
        if dec:
            build.meta["decor"] = dec.as_dict()
            note = decor.ink_note(dec)
            if note:
                build.meta["decor_ink_note"] = note
            if decor.describe(dec):
                build.features.insert(min(2, len(build.features)), decor.describe(dec))

        start = build_start_page(build, style, pdir, ptype.key, niche.key, req.options.get("gsheet_url"))
        if start:
            build.files.insert(0, start)

        say("Checking for similar existing products")
        fp = ptype.fingerprint(ctx, content)
        similar = most_similar(fp, store.fingerprints())

        say("Writing listing copy")
        kit: ListingKit = make_kit(niche, ptype, build, router, random.Random(seed), providers=req.providers)
        labels = [ptype.size_label(s) for s in sizes]
        images: dict[str, list[Path]] = {}
        if req.with_images:
            say("Creating listing images and pins")
            images = make_images(build, style, folder, ptype.key, kit.copy_, labels, router=router, niche=niche,
                                 providers=req.providers, videos=req.with_video and bool(cfg.get("render.videos", True)),
                                 motion_engines=req.motion, marketplaces=req.marketplaces)
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
        sig = content_signature(style.palette.key, req.options, build.meta) if not ptype.niche_in_copy else []
        if sig:
            near = cross_type_match(sig, ptype.key, _signatures(store))
            if near[0] >= CROSS_TYPE_THRESHOLD:
                checks.append(Check("Uniqueness across types", "warn", f"{near[0]:.0%} of its colours, theme and pictures match {near[3]} #{near[1]} '{near[2]}': "
                                    "buyers may see them as the same pack; change the theme or look"))
        from .crafttools import second_opinion
        opinion = second_opinion(folder)
        if opinion is not None:
            checks.append(opinion)
        findings = riskmod.scan_listing(json.loads(kit.model_dump_json()), content.model_dump_json(), req.niche)
        top = riskmod.status(findings)
        checks.append(Check("Risk check (brands, claims, rights language)", top if top != "pass" else "pass",
                            "nothing on the watch list" if not findings else "; ".join(f"{f.where}: '{f.term}' ({f.severity})" for f in findings[:6])))
        from .spellcheck import spelling_check
        checks.append(spelling_check(content.model_dump_json(), json.loads(kit.model_dump_json()), niche))
        if findings:
            (folder / "listing" / "risk.json").write_text(json.dumps([f.to_dict() for f in findings], indent=2), encoding="utf-8")
        qa_status = summarize(checks)

        (folder / "spec.json").write_text(json.dumps({
            "request": {"niche": req.niche, "product_type": req.product_type, "sizes": sizes, "seed": seed, "options": req.options},
            "signature": sig, "style": style.describe(), "niche_source": niche_source, "content_source": content_source, "listing_source": kit.source,
            "content": json.loads(content.model_dump_json()),
        }, indent=2), encoding="utf-8")

        from .craftbuild import after_make
        extras = after_make(folder)   # optional extra file formats; None unless switched on in settings
        if extras is not None:
            checks.append(extras)
            qa_status = summarize(checks)

        pid = store.add_product(
            slug=folder.name, title=build.title, niche=niche.key, niche_name=niche.name, product_type=ptype.key,
            style=style.key, status="draft", folder=str(folder), price=kit.price, qa=[c.to_dict() for c in checks],
            fingerprint=fp, content_source=content_source, listing_source=kit.source,
            spec=json.dumps({"seed": seed, "sizes": sizes, "style": style.describe()}),
        )
        make_package(folder)
        say("Done")
        return Result(pid, folder, build.title, qa_status, checks, similar, content_source, kit.source)
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)  # a failed run must not leave an empty product folder
        raise


def _signatures(store: Store) -> list[tuple[int, str, str, list[str]]]:
    """(id, title, type, content signature) of catalogued products that recorded one."""
    out = []
    with store.conn() as c:
        rows = c.execute("SELECT id, title, product_type, folder FROM products").fetchall()
    for r in rows:
        try:
            sig = json.loads((Path(r["folder"]) / "spec.json").read_text(encoding="utf-8")).get("signature", [])
        except (OSError, ValueError):
            continue
        out.append((r["id"], r["title"], r["product_type"], sig))
    return out


def delete_product(pid: int, store: Store | None = None) -> bool:
    """Remove a product from the catalogue and delete its folder, but only a folder inside the output directory."""
    st = store or Store()
    p = st.product(pid)
    if not p:
        return False
    folder = Path(p["folder"]).resolve()
    root = (get_config().output_dir / "products").resolve()
    if folder != root and root in folder.parents:
        shutil.rmtree(folder, ignore_errors=True)
    st.delete_product(pid)
    return True


def make_package(folder: Path) -> Path:
    """Zip everything you need to upload (product files, images, guides) into one file."""
    import zipfile

    zpath = folder / "upload-package.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for sub in ("product", "images", "listing", "brag"):
            for f in sorted((folder / sub).rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(folder))
    return zpath
