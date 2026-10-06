"""Where a brag gets its material: a catalogue product, several products (shop), or a live web page."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from ..config import get_config
from ..design import PALETTES, Style, choose_style, style_from_dict
from ..editable import _page_images
from ..niches import smart_resolve
from ..store import Store
from .plan import Facts


@dataclass
class Material:
    facts: Facts
    pages: list[Image.Image]
    style: Style
    slug: str
    out_dir: Path
    is_wall_art: bool = False
    art_pages: list[Image.Image] = field(default_factory=list)


def _features_from_description(desc: str) -> list[str]:
    m = re.search(r"WHAT'S INCLUDED\s*\n(.*?)\n\s*\n", desc, re.S)
    return [ln.lstrip("- ").strip() for ln in (m.group(1).splitlines() if m else []) if ln.strip()]


def _first_sentence(text: str, n: int = 120) -> str:
    s = re.split(r"(?<=[.!?])\s", text.strip())[0]
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def _shop() -> dict:
    cfg = get_config()
    return {k: (cfg.get(f"shop.{k}") or "") for k in ("name", "email", "url")}


def from_product(pid: int, store: Store | None = None) -> Material:
    store = store or Store()
    p = store.product(pid)
    if not p:
        raise ValueError(f"no product #{pid}")
    folder = Path(p["folder"])
    spec = json.loads((folder / "spec.json").read_text())
    listing = json.loads((folder / "listing" / "listing.json").read_text())
    copy = listing["copy_"]
    niche, _ = smart_resolve(spec["request"]["niche"])
    features = spec.get("features") or _features_from_description(listing.get("description", ""))
    features = [f for f in features if not f.lower().startswith(("made for", "designed for", "instant pdf download", "instant download"))] or features
    shop = _shop()
    url = shop["url"] or next((x["url"] for x in store.listings(pid) if x.get("url")), "")
    pages = _page_images(folder, n=4)
    style = style_from_dict(spec["style"])
    facts = Facts(
        name=p["title"], kind="product", one_liner=_first_sentence(copy.get("intro", "")) or f"Made for {niche.audience}.",
        audience=niche.audience, features=features[:6], pains=niche.pain_points[:3], price=f"${p['price']:.2f}" if p.get("price") else "",
        shop=shop["name"], url=url, n_pages=max(1, len(pages)))
    return Material(facts, pages, style, f"{p['id']:04d}-{re.sub(r'[^a-z0-9]+', '-', p['title'].lower()).strip('-')[:40]}",
                    folder / "brag", spec["request"]["product_type"] == "wall_art")


def from_shop(pids: list[int], store: Store | None = None) -> Material:
    store = store or Store()
    mats = [from_product(i, store) for i in pids]
    first = mats[0]
    shop = _shop()
    pages = [m.pages[0] for m in mats if m.pages]
    facts = Facts(
        name=shop["name"] or "New in the shop", kind="shop",
        one_liner=f"{len(mats)} new digital downloads: " + ", ".join(m.facts.name for m in mats[:3]) + ("…" if len(mats) > 3 else ""),
        audience=", ".join(dict.fromkeys(m.facts.audience.split(" who ")[0] for m in mats))[:120],
        features=[m.facts.name for m in mats[:5]], pains=[], shop=shop["name"], url=shop["url"], n_pages=max(1, len(pages)))
    out = Path(get_config().output_dir) / "brag" / f"shop-{'-'.join(str(i) for i in pids)}"
    return Material(facts, pages, first.style, f"shop-{'-'.join(str(i) for i in pids)}", out)


# ----------------------------------------------------------------------------- web page
def _hex_from_css(color: str) -> str | None:
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)", color or "")
    if not m or (m.group(4) is not None and float(m.group(4)) == 0):
        return None
    return "#%02x%02x%02x" % tuple(int(m.group(i)) for i in (1, 2, 3))


def closest_palette(hex_color: str | None) -> str:
    if not hex_color:
        return "sage"
    h = hex_color.lstrip("#")
    r, g_, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))

    def dist(p) -> float:
        a = p.accent.lstrip("#")
        return sum((int(a[i:i + 2], 16) - c) ** 2 for i, c in zip((0, 2, 4), (r, g_, b)))
    return min(PALETTES, key=dist).key


def inspect_url(url: str, size: tuple[int, int], shots: int = 4) -> dict:
    """Render the page in headless Chromium and collect copy, colours and section screenshots (needs Playwright)."""
    import io

    from playwright.sync_api import sync_playwright

    from ..render.pdf import chromium_executable

    if not re.match(r"https?://", url):
        url = "https://" + url
    W, H = size
    out: dict = {"url": url, "title": "", "description": "", "headings": [], "ctas": [], "accent": None, "shots": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chromium_executable())
        page = browser.new_page(viewport={"width": W // 2 if W > H else W // 2, "height": int((W // 2 if W > H else W // 2) * H / W)})
        page.goto(url, wait_until="networkidle", timeout=45000)
        for label in ("Accept all", "Accept", "I agree", "Agree", "Got it", "OK", "Allow all"):   # dismiss cookie banners
            try:
                page.get_by_role("button", name=label, exact=False).first.click(timeout=600)
                break
            except Exception:  # noqa: BLE001
                continue
        out["title"] = page.title()
        out["description"] = (page.locator('meta[name="description"]').first.get_attribute("content", timeout=500)
                              if page.locator('meta[name="description"]').count() else "") or ""
        out["site_name"] = (page.locator('meta[property="og:site_name"]').first.get_attribute("content", timeout=500)
                            if page.locator('meta[property="og:site_name"]').count() else "") or ""
        out["headings"] = [t.strip() for t in page.locator("h1, h2, h3").all_inner_texts()[:12] if t.strip()]
        out["ctas"] = [t.strip() for t in page.locator("a[class*=btn], a[class*=button], button").all_inner_texts()[:8] if 2 < len(t.strip()) < 30]
        bg = page.evaluate("() => { const b=document.querySelector('a[class*=btn], a[class*=button], button'); return b ? getComputedStyle(b).backgroundColor : '' }")
        out["accent"] = _hex_from_css(bg) or _hex_from_css(page.evaluate("() => getComputedStyle(document.querySelector('a')||document.body).color"))
        total = page.evaluate("() => document.documentElement.scrollHeight")
        vh = page.viewport_size["height"]
        for k in range(shots):
            y = int(k * max(1, (total - vh)) / max(1, shots - 1)) if total > vh else 0
            page.evaluate(f"window.scrollTo(0,{y})")
            page.wait_for_timeout(700)      # let scroll-triggered content animate in
            out["shots"].append(Image.open(io.BytesIO(page.screenshot())).convert("RGB"))
            if total <= vh:
                break
        browser.close()
    return out


def from_url(url: str, size: tuple[int, int]) -> Material:
    info = inspect_url(url, size)
    name = info["site_name"] or re.split(r"\s[-|–—:]\s", info["title"])[0] or url
    style = choose_style(seed=7, palette=closest_palette(info["accent"]))
    feats = [h for h in info["headings"][1:6] if 3 < len(h) < 60]
    facts = Facts(
        name=name[:60], kind="website", one_liner=_first_sentence(info["description"]) or (info["headings"][0] if info["headings"] else name),
        features=feats, cta=(info["ctas"][0] if info["ctas"] else "Check it out"), url=url, n_pages=max(1, len(info["shots"])))
    slug = re.sub(r"[^a-z0-9]+", "-", re.sub(r"^https?://", "", url.lower())).strip("-")[:40]
    out = Path(get_config().output_dir) / "brag" / slug
    return Material(facts, info["shots"], style, slug, out)
