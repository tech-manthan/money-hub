"""Fill the per-marketplace upload guides with this product's real copy, files and images."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ..paths import GUIDE_DIR
from .kit import ListingKit

_env = Environment(loader=FileSystemLoader(str(GUIDE_DIR)), trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)

MARKETPLACES = ["etsy", "gumroad", "payhip", "kofi", "pinterest"]


def render_guides(out_dir: Path, kit: ListingKit, build, images: dict[str, list[Path]], style_palette: str, marketplaces: list[str]) -> list[Path]:
    rel = lambda p: str(Path(p).relative_to(out_dir))  # noqa: E731
    files = [rel(f.path) for f in build.files if f.primary]
    copy = kit.copy_
    common = dict(title=build.title, copy=copy, description=kit.description, price=kit.price, price_note=kit.price_note, files=files)
    written = []
    for m in marketplaces:
        if m not in MARKETPLACES:
            continue
        ctx = dict(common)
        if m == "etsy":
            ctx.update(video=[rel(p) for p in images.get("video", []) if "listing" in p.name], images=[rel(p) for p in images.get("etsy", [])], has_xlsx=any(f.kind == "xlsx" for f in build.files), colour=style_palette)
        elif m in ("gumroad",):
            gi = images.get("gumroad", [])
            ctx.update(cover=rel(gi[0]) if gi else "", thumb=rel(gi[1]) if len(gi) > 1 else "")
        elif m == "payhip":
            pi = images.get("payhip", [])
            ctx.update(cover=rel(pi[0]) if pi else "")
        elif m == "kofi":
            ki = images.get("kofi", [])
            ctx.update(square=rel(ki[0]) if ki else "")
        elif m == "pinterest":
            pins = [{"image": rel(p), "title": copy.pin_titles[i % len(copy.pin_titles)]} for i, p in enumerate(images.get("pinterest", []))]
            ctx.update(video=[rel(p) for p in images.get("video", []) if "pin" in p.name], pins=pins, pin_description=copy.pin_description, marketplace_hint="Etsy/Gumroad/Payhip")
        path = out_dir / "listing" / f"guide-{m}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_env.get_template(f"{m}.md.j2").render(**ctx), encoding="utf-8")
        written.append(path)
    return written
