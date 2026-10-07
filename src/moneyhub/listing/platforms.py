"""Per-marketplace upload packs: which of a product's files go where, whether they fit that platform's limits, and a zip with
everything for that one platform (the download the buyer gets, the listing images, the copy and the guide).

Limits are the ones the upload guides already state. Check them on the platform before relying on them: they change."""
from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

MB = 1_000_000


@dataclass(frozen=True)
class Platform:
    key: str
    label: str
    max_files: int | None      # files a buyer can be given per listing (None = no stated limit)
    max_file_mb: int           # per file
    max_total_mb: int | None
    note: str


PLATFORMS: dict[str, Platform] = {
    "etsy": Platform("etsy", "Etsy", 5, 20, 100, "Up to 5 files, 20 MB each, 100 MB in total. Bigger sets are split into zips of 20 MB or less."),
    "gumroad": Platform("gumroad", "Gumroad", None, 16_000, None, "Paid items can have files up to 16 GB. Free or pay-what-you-want-from-$0 items are limited to 25 MB per file."),
    "payhip": Platform("payhip", "Payhip", None, 5_000, None, "Each file can be up to 5 GB."),
    "kofi": Platform("kofi", "Ko-fi", None, 1_000, None, "Each product file can be up to 1 GB (confirm in Ko-fi's help: this figure is from a secondary source)."),
}
IMAGE_DIRS = {"etsy": ("etsy", "video"), "gumroad": ("gumroad",), "payhip": ("payhip",), "kofi": ("kofi",)}


def _files(folder: Path, sub: str) -> list[Path]:
    d = folder / sub
    return sorted(f for f in d.rglob("*") if f.is_file()) if d.exists() else []


def _slug(folder: Path) -> str:
    return re.sub(r"^\d{8}-\d{6}-", "", folder.name)


def _split_into_zips(files: list[Path], limit: int) -> list[list[Path]]:
    """Greedy first-fit-decreasing groups of files whose sizes add up to at most limit (a file over the limit gets its own group)."""
    groups: list[list[Path]] = []
    sizes: list[int] = []
    for f in sorted(files, key=lambda p: -p.stat().st_size):
        s = f.stat().st_size
        for i, used in enumerate(sizes):
            if used + s <= limit:
                groups[i].append(f)
                sizes[i] += s
                break
        else:
            groups.append([f])
            sizes.append(s)
    return groups


def plan(folder: Path, platform: str) -> dict:
    """What would be sold on this platform: the download files (with fit status), listing images, text files and warnings."""
    if platform not in PLATFORMS:
        raise ValueError(f"unknown platform '{platform}'. Choose one of: {', '.join(PLATFORMS)}")
    pf = PLATFORMS[platform]
    limit = pf.max_file_mb * MB
    product = _files(folder, "product")
    warnings: list[str] = []
    over = [f for f in product if f.stat().st_size > limit]
    total = sum(f.stat().st_size for f in product)
    fits_as_is = (not over and (pf.max_files is None or len(product) <= pf.max_files)
                  and (pf.max_total_mb is None or total <= pf.max_total_mb * MB))
    if fits_as_is:
        downloads = [{"name": f.name, "size": f.stat().st_size, "from": [f.name], "ok": True} for f in product]
        strategy = "as they are"
    else:
        groups = _split_into_zips([f for f in product if f not in over], limit - 200_000) + [[f] for f in over]
        downloads = []
        for i, g in enumerate(groups, 1):
            name = g[0].name if len(g) == 1 and g[0] in over else f"{_slug(folder)}-part-{i}.zip"
            size = sum(f.stat().st_size for f in g)
            downloads.append({"name": name, "size": size, "from": [f.name for f in g], "ok": size <= limit})
        strategy = "grouped into zips"
        if pf.max_files is not None and len(downloads) > pf.max_files:
            warnings.append(f"{len(downloads)} files are needed but {pf.label} allows {pf.max_files} per listing. Sell it as two listings, or use another platform.")
    for f in over:
        warnings.append(f"{f.name} is {f.stat().st_size / MB:.1f} MB, over {pf.label}'s {pf.max_file_mb} MB per-file limit. "
                        "Use a platform with a bigger limit, lower the image quality, or deliver a small PDF that links to the file.")
    if not product:
        warnings.append("This product has no files in product/ yet.")
    images = [str(f.relative_to(folder)) for d in IMAGE_DIRS[platform] for f in _files(folder, f"images/{d}")]
    if not images:
        warnings.append("No listing images were made for this platform (the product was made without images).")
    text = [str(f.relative_to(folder)) for f in _files(folder, "listing") if f.name == f"guide-{platform}.md"
            or (platform == "etsy" and f.name in ("etsy-description.txt", "etsy-tags.txt"))]
    return {"platform": platform, "label": pf.label, "note": pf.note, "strategy": strategy, "downloads": downloads, "images": images,
            "text": text, "warnings": warnings, "ok": not warnings, "total": total}


def build_pack(folder: Path, platform: str) -> Path:
    """Zip for one platform: 1-DOWNLOAD (what buyers receive), 2-LISTING-IMAGES, 3-LISTING-TEXT, README."""
    p = plan(folder, platform)
    out_dir = folder / "packs"
    out_dir.mkdir(exist_ok=True)
    dest = out_dir / f"{_slug(folder)}-{platform}.zip"
    product = {f.name: f for f in _files(folder, "product")}
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for d in p["downloads"]:
            members = [product[n] for n in d["from"]]
            if len(members) == 1 and members[0].name == d["name"]:
                z.write(members[0], f"1-DOWNLOAD/{d['name']}")
            else:   # a group: build the inner zip (already-compressed files, so store them) and add it
                import io
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as inner:
                    for m in members:
                        inner.write(m, m.name)
                z.writestr(f"1-DOWNLOAD/{d['name']}", buf.getvalue())
        for rel in p["images"]:
            z.write(folder / rel, f"2-LISTING-IMAGES/{Path(rel).name}")
        for rel in p["text"]:
            z.write(folder / rel, f"3-LISTING-TEXT/{Path(rel).name}")
        lj = folder / "listing" / "listing.json"
        if lj.exists():
            data = json.loads(lj.read_text())
            lines = [f"Price: ${data.get('price', 0):.2f}  {data.get('price_note', '')}".strip()]
            z.writestr("3-LISTING-TEXT/price.txt", "\n".join(lines) + "\n")
        z.writestr("README.txt", _readme(p))
    return dest


def _readme(p: dict) -> str:
    lines = [f"{p['label']} pack", "", p["note"], "",
             "1-DOWNLOAD      The file(s) buyers receive. Upload these as the listing's digital files.",
             "2-LISTING-IMAGES The listing photos, in upload order.",
             "3-LISTING-TEXT   Step-by-step guide, title/description/tags where the platform uses them, and the price.", "",
             f"Download files ({p['strategy']}):"]
    lines += [f"  - {d['name']}  ({d['size'] / MB:.1f} MB){'' if d['ok'] else '  <-- TOO BIG'}" for d in p["downloads"]]
    if p["warnings"]:
        lines += ["", "Check before you upload:"] + [f"  ! {w}" for w in p["warnings"]]
    return "\n".join(lines) + "\n"
