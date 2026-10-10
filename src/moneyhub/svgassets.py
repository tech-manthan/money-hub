"""Open-source SVG icon libraries as raw material: a license guard, a safe importer and a downloader for two permissively licensed sets (Tabler, MIT;
Lucide, ISC). Files live in <output dir>/assets/svg/<collection>/ with a collection.json that records where they came from and under which licence.
Only licences that allow reuse and redistribution with a notice are accepted; share-alike (CC BY-SA), non-commercial, GPL and unknown licences are refused."""
from __future__ import annotations

import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .config import get_config

# SPDX id -> what the buyer-facing LICENSES.txt must carry
ALLOWED = {"CC0-1.0": "no attribution needed", "MIT": "keep the copyright and licence notice", "ISC": "keep the copyright and licence notice",
           "Apache-2.0": "keep the licence and notices", "PD": "public domain", "CC-BY-4.0": "credit the author"}
REFUSED = {"CC-BY-SA-4.0": "share-alike would force the same licence onto your products", "CC-BY-SA-3.0": "share-alike", "CC-BY-NC-4.0": "non-commercial",
           "GPL-3.0": "copyleft", "GPL-2.0": "copyleft", "LGPL-3.0": "copyleft"}
ALLOWED_TAGS = {"svg", "g", "path", "circle", "ellipse", "rect", "line", "polyline", "polygon", "title"}
KNOWN = {
    "tabler": dict(name="Tabler Icons (outline)", license="MIT", package="@tabler/icons", prefix="/icons/outline/", home="https://tabler.io/icons",
                   license_url="https://raw.githubusercontent.com/tabler/tabler-icons/main/LICENSE"),
    "tabler-filled": dict(name="Tabler Icons (filled)", license="MIT", package="@tabler/icons", prefix="/icons/filled/", home="https://tabler.io/icons",
                          license_url="https://raw.githubusercontent.com/tabler/tabler-icons/main/LICENSE"),
    "lucide": dict(name="Lucide", license="ISC", package="lucide-static", prefix="/icons/", home="https://lucide.dev",
                   license_url="https://raw.githubusercontent.com/lucide-icons/lucide/main/LICENSE"),
}


def root() -> Path:
    return get_config().output_dir / "assets" / "svg"


def check_license(spdx: str) -> None:
    if spdx in REFUSED:
        raise ValueError(f"licence {spdx} is refused: {REFUSED[spdx]}")
    if spdx not in ALLOWED:
        raise ValueError(f"licence '{spdx}' is not on the allowed list ({', '.join(ALLOWED)}). Check the source's licence and use one of those, or ask first.")


def _http(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "MoneyHub/1.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf8", "replace")


def clean_svg(text: str) -> str | None:
    """The inner shapes of a 24-unit icon (comments, background boxes and scripts removed), or None if the file uses anything beyond simple shapes."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    m = re.search(r"<svg\b[^>]*>(.*)</svg>", text, flags=re.S)
    if not m:
        return None
    inner = re.sub(r"<path[^>]*stroke=[\"']none[\"'][^>]*/>", "", m.group(1)).strip()
    tags = set(re.findall(r"<\s*([A-Za-z][\w:-]*)", inner))
    if not tags or tags - ALLOWED_TAGS or re.search(r"(on\w+\s*=|javascript:|href\s*=|<!ENTITY)", inner, flags=re.I):
        return None
    return re.sub(r"\s+", " ", inner)


def install(key: str, name: str, spdx: str, source: str, files: dict[str, str], license_text: str = "", version: str = "", style: str = "stroke") -> Path:
    """Write a collection (file name -> raw svg text). Refuses disallowed licences and skips files that are not plain shapes."""
    check_license(spdx)
    d = root() / key
    (d / "icons").mkdir(parents=True, exist_ok=True)
    kept = 0
    for fname, raw in files.items():
        inner = clean_svg(raw)
        if inner is None:
            continue
        (d / "icons" / f"{re.sub(r'[^a-z0-9-]+', '-', fname.lower().removesuffix('.svg'))}.svg").write_text(inner, encoding="utf-8")
        kept += 1
    (d / "LICENSE.txt").write_text(license_text or f"{name}: licensed under {spdx}. Source: {source}\n", encoding="utf-8")
    (d / "collection.json").write_text(json.dumps({"key": key, "name": name, "license": spdx, "source": source, "version": version, "style": style, "icons": kept,
                                                   "fetched": time.strftime("%Y-%m-%d")}, indent=2), encoding="utf-8")
    if not kept:
        raise ValueError("no usable icons in that set (only plain shapes are accepted)")
    return d


def fetch(key: str, limit: int = 600, progress=print) -> Path:
    """Download an evenly spaced selection of up to `limit` icons from a known set through the jsDelivr CDN and install it."""
    if key not in KNOWN:
        raise ValueError(f"unknown set '{key}'. Known: {', '.join(KNOWN)}")
    k = KNOWN[key]
    meta = json.loads(_http(f"https://data.jsdelivr.com/v1/package/npm/{k['package']}"))
    ver = meta["tags"]["latest"]
    flat = json.loads(_http(f"https://data.jsdelivr.com/v1/package/npm/{k['package']}@{ver}/flat"))
    names = sorted(f["name"] for f in flat["files"] if f["name"].startswith(k["prefix"]) and f["name"].endswith(".svg"))
    step = max(1, len(names) // max(1, limit))
    pick = names[::step][:limit]
    progress(f"{k['name']} {ver}: downloading {len(pick)} of {len(names)} icons")

    def one(n: str) -> tuple[str, str]:
        return n.rsplit("/", 1)[-1], _http(f"https://cdn.jsdelivr.net/npm/{k['package']}@{ver}{n}")
    with ThreadPoolExecutor(12) as ex:
        files = dict(ex.map(one, pick))
    try:
        lic = _http(k["license_url"])
    except Exception:  # noqa: BLE001
        lic = ""
    return install(key, k["name"], k["license"], k["home"], files, lic, ver, "filled" if "filled" in key else "stroke")


def collections() -> list[dict]:
    out = []
    for f in sorted(root().glob("*/collection.json")) if root().exists() else []:
        out.append(json.loads(f.read_text()))
    return out


def load(key: str) -> tuple[dict, dict[str, str]]:
    d = root() / key
    if not (d / "collection.json").exists():
        raise ValueError(f"no icon set '{key}' installed. Run: moneyhub assets fetch {key}" if key in KNOWN else f"no icon set '{key}' installed (see: moneyhub assets list)")
    meta = json.loads((d / "collection.json").read_text())
    check_license(meta["license"])
    icons = {p.stem: p.read_text(encoding="utf-8") for p in sorted((d / "icons").glob("*.svg"))}
    meta["license_text"] = (d / "LICENSE.txt").read_text(encoding="utf-8") if (d / "LICENSE.txt").exists() else ""
    return meta, icons


def notice(meta: dict) -> str:
    """The text that goes into LICENSES.txt in a buyer's download."""
    return (f"Icon artwork in this download is from {meta['name']} ({meta['source']}), licensed under {meta['license']} "
            f"({ALLOWED.get(meta['license'], '')}). The original licence follows.\n\n{meta.get('license_text', '').strip()}\n")
