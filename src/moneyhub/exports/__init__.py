"""Exports of a finished product for other platforms: Amazon KDP, Notion, Canva."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..store import Store


@dataclass
class Loaded:
    folder: Path
    product: dict
    spec: dict

    @property
    def ptype(self) -> str:
        return self.spec["request"]["product_type"]

    @property
    def content(self) -> dict:
        return self.spec["content"]

    @property
    def title(self) -> str:
        return self.product["title"]


def load(product_id: int, store: Store | None = None) -> Loaded:
    p = (store or Store()).product(product_id)
    if not p:
        raise ValueError(f"no product #{product_id}")
    folder = Path(p["folder"])
    spec_file = folder / "spec.json"
    if not spec_file.exists():
        raise ValueError("this product has no spec.json, so it cannot be exported")
    return Loaded(folder, p, json.loads(spec_file.read_text()))


def pack_zip(l: Loaded, kind: str) -> Path:
    """One download for a platform: everything in exports/<kind>/ zipped as exports/<name>-<kind>-pack.zip (the guide is inside it)."""
    import re
    import zipfile
    src = l.folder / "exports" / kind
    base = re.sub(r"[^a-z0-9]+", "-", l.title.lower()).strip("-") or "product"
    z = l.folder / "exports" / f"{base}-{kind}-pack.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(src.rglob("*")):
            if f.is_file():
                zf.write(f, f"{base}-{kind}/{f.relative_to(src)}")
    return z


def out_dir(l: Loaded, name: str) -> Path:
    d = l.folder / name
    d.mkdir(exist_ok=True)
    return d
