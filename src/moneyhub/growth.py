"""Small helpers around products: bundles, free samples, seasonal calendar, keyword ideas."""
from __future__ import annotations

import json
import re
import zipfile
from datetime import date
from pathlib import Path

from .config import get_config
from .store import Store

# Approximate public fee schedules; they change, so the numbers are labelled estimates in all output.
FEES = {
    "etsy": {"pct": 0.065 + 0.03, "fixed": 0.20 + 0.25, "note": "6.5% transaction + ~3% & $0.25 payment processing + $0.20 listing (estimate; check Etsy's fee page)"},
    "gumroad": {"pct": 0.10, "fixed": 0.50, "note": "10% + $0.50 flat fee (estimate; 30% via Discover; check Gumroad)"},
    "payhip": {"pct": 0.05, "fixed": 0.0, "note": "free plan ~5% + processor fees (estimate; check Payhip)"},
    "kofi": {"pct": 0.0, "fixed": 0.0, "note": "0% commission + processor fees (estimate; check Ko-fi)"},
}


def net_after_fees(price: float, marketplace: str) -> float:
    f = FEES[marketplace]
    return round(price * (1 - f["pct"]) - f["fixed"], 2)


def bundle_price(prices: list[float], discount: float = 0.30) -> float:
    """Sum of parts less a discount, ending in .99 or .00 when sensible, never below the priciest single item."""
    raw = max(sum(prices) * (1 - discount), max(prices) + 1.0)
    return float(int(raw)) + 0.99 if raw - int(raw) >= 0.5 else max(float(int(raw)) - 0.01, 0.99)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "bundle"


def _cover_page(folder: Path):
    """First page of a product's main PDF (its cover) as an image, or None."""
    from .render.raster import render_pages
    pdfs = sorted(f for f in (folder / "product").glob("*.pdf") if not f.name.startswith("00-"))
    if not pdfs:
        return None
    try:
        return render_pages(pdfs[0], [0], scale=1.1)[0]
    except Exception:   # a damaged or unusual PDF must not stop the bundle
        return None


def make_bundle(pids: list[int], name: str, discount: float = 0.30, store: Store | None = None, title: str | None = None,
                extra_tags: list[str] | None = None) -> Path:
    """One zip of several products plus a listing kit (title, tags, description, price with fees, AI line) and a collage cover image."""
    if len(pids) < 2:
        raise ValueError("a bundle needs at least two products")
    store = store or Store()
    rows = []
    for pid in pids:
        p = store.product(pid)
        if not p:
            raise ValueError(f"no product #{pid}")
        rows.append(p)
    out = Path(get_config().output_dir) / "bundles" / f"{date.today():%Y%m%d}-{_slug(name)}"
    n = 1
    while (out / "product").exists() and any((out / "product").iterdir()):
        n += 1   # a second bundle with the same name must not mix into the first
        out = Path(get_config().output_dir) / "bundles" / f"{date.today():%Y%m%d}-{_slug(name)}-{n}"
    (out / "product").mkdir(parents=True, exist_ok=True)
    zpath = out / "product" / f"{_slug(name)}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in rows:
            for f in sorted((Path(p["folder"]) / "product").glob("*")):
                if f.is_file():
                    z.write(f, f"{_slug(p['title'])[:30]}/{f.name}")
    prices = [float(p["price"] or 0) for p in rows]
    price = bundle_price([x or 5.0 for x in prices], discount)
    nets = "\n".join(f"- {m}: you keep about ${net_after_fees(price, m):.2f} - {FEES[m]['note']}" for m in FEES)
    tags, intros, disclosure = [], [], ""
    for p in rows:
        lst = Path(p["folder"]) / "listing" / "listing.json"
        if lst.exists():
            data = json.loads(lst.read_text())
            tags += data.get("copy_", {}).get("tags", [])
            intro = re.sub(r"^" + re.escape(p["title"]) + r"\s*[:.-]\s*", "", data.get("copy_", {}).get("intro", "").strip(), flags=re.I)
            intros.append(f"- {p['title']}: {intro}".rstrip(": "))
            disclosure = disclosure or data.get("ai_disclosure", "")
    tags = list(dict.fromkeys(t for t in [*(extra_tags or []), *tags] if len(t) <= 20))[:13]
    items = "\n".join(f"- {p['title']} (sold separately at ${float(p['price'] or 0):.2f})" for p in rows)
    title = (title or f"{name} - {len(rows)} Printable Digital Downloads - Instant Download")[:140]
    (out / "listing.md").write_text(
        f"# {name}\n\n**Suggested price:** ${price:.2f} (sum of parts ${sum(prices):.2f}, {int(discount * 100)}% bundle discount)\n\n"
        f"## Etsy title (140 characters max)\n{title}\n\n"
        f"## What you keep (estimates)\n{nets}\n\n## Tags (reused from the products, max 13)\n{', '.join(tags)}\n\n"
        f"## Description starter\nA bundle of {len(rows)} digital downloads, saving {int(discount * 100)}% against buying them one by one.\n\n"
        f"Included:\n{items}\n\nAbout each one:\n" + "\n".join(intros) + "\n\n"
        f"Instant digital download - no physical item will be shipped. Each folder in the zip keeps its own terms: copy the strictest licence wording "
        f"(for example from a clipart pack) into the listing.\n\n## AI disclosure line\n{disclosure or 'Add the AI disclosure line from the product listings.'}\n", encoding="utf-8")
    try:
        from PIL import Image  # noqa: F401
        from .design import choose_style
        from .render import graphics as g
        pages = [im for im in (_cover_page(Path(p["folder"])) for p in rows) if im is not None]
        if pages:
            brush = g.Brush(choose_style(seed=sum(pids)))
            g.hero(pages[:4], name, f"{len(rows)} products in one download", [f"Save {int(discount * 100)}%", "Instant download"], brush).convert("RGB").save(
                out / "bundle-cover.jpg", quality=90)
    except Exception as e:   # the cover is a bonus; the zip and listing are what matters
        (out / "bundle-cover-error.txt").write_text(str(e), encoding="utf-8")
    (out / "bundle.json").write_text(json.dumps({"name": name, "price": price, "discount": discount, "products": [
        {"id": p["id"], "title": p["title"], "type": p["product_type"], "price": p["price"]} for p in rows]}, indent=2), encoding="utf-8")
    return out


def make_sample(pid: int, pages: int = 2, store: Store | None = None) -> Path | None:
    """Free preview PDF (first pages of the main PDF) for lead magnets and Pinterest/email."""
    from pypdf import PdfReader, PdfWriter
    p = (store or Store()).product(pid)
    if not p:
        raise ValueError(f"no product #{pid}")
    folder = Path(p["folder"])
    pdfs = sorted(f for f in (folder / "product").glob("*.pdf") if not f.name.startswith("00-"))
    if not pdfs:
        return None
    reader = PdfReader(str(pdfs[0]))
    w = PdfWriter()
    for page in reader.pages[: max(1, pages)]:
        w.add_page(page)
    w.add_metadata({"/Title": f"{p['title']} - free sample"})
    out = folder / "sample"
    out.mkdir(exist_ok=True)
    dst = out / f"sample-{pdfs[0].stem}.pdf"
    with open(dst, "wb") as fh:
        w.write(fh)
    return dst


# month -> (occasion, what sells). General guidance: start 2-3 months ahead because listings need time to be indexed.
CALENDAR = {
    1: [("New year reset", "planners, goal setting, habit and budget trackers"), ("Tax season prep", "expense and receipt trackers")],
    2: [("Valentine's Day", "cards, couple journals, gift tags"), ("Wedding season planning", "wedding planners, checklists")],
    3: [("Spring cleaning", "cleaning schedules, decluttering checklists"), ("Easter", "kids activities, printable cards")],
    4: [("Mother's Day (May)", "gift cards, memory journals"), ("Graduation (May-June)", "cards, memory books, study planners")],
    5: [("Summer break", "kids routines, travel planners"), ("Father's Day (June)", "cards, journals")],
    6: [("Back to school (Jul-Sep)", "teacher planners, student planners, classroom printables")],
    7: [("Back to school", "student planners, lesson planners"), ("Fall planning", "undated planners, 12-month")],
    8: [("Halloween (Oct)", "party printables, kids activities"), ("Teacher gifts", "gift cards, appreciation notes")],
    9: [("Thanksgiving (Nov)", "meal planners, gratitude journals"), ("Q4 business planning", "business planners, content calendars")],
    10: [("Christmas / holidays", "advent calendars, gift trackers, holiday budgets, cards"), ("Black Friday", "bundles")],
    11: [("Next-year planners", "dated and undated planners, goal workbooks"), ("Christmas last minute", "instant-download gift cards")],
    12: [("New-year reset", "planners, habit trackers, budget trackers"), ("Tax prep", "receipt trackers")],
}


def calendar(today: date | None = None, months: int = 4) -> list[dict]:
    today = today or date.today()
    out = []
    for k in range(months):
        m = (today.month - 1 + k) % 12 + 1
        for occasion, ideas in CALENDAR[m]:
            out.append({"month": m, "in_months": k, "occasion": occasion, "ideas": ideas})
    return out


def keyword_ideas(seed: str, suggest: bool = False) -> list[str]:
    """Related search phrases. Offline: seed + common modifiers. Optional: Google autocomplete (public suggest endpoint)."""
    seed = seed.strip().lower()
    mods = ["printable", "digital download", "template", "pdf", "for women", "for men", "for kids", "for teachers", "for nurses",
            "for students", "goodnotes", "minimalist", "aesthetic", "undated", "2027", "instant download"]
    ideas = [f"{seed} {m}" for m in mods]
    if suggest:
        import httpx
        for q in (seed, f"{seed} printable", f"{seed} template"):
            try:
                r = httpx.get("https://suggestqueries.google.com/complete/search", params={"client": "firefox", "q": q}, timeout=8)
                ideas += [s for s in r.json()[1] if isinstance(s, str)]
            except Exception:  # noqa: BLE001
                break
    return list(dict.fromkeys(ideas))


# ------------------------------------------------------------------ what to make next, learned from your own results
def recommend(store: Store | None = None, limit: int = 5) -> dict:
    """Suggestions from the sales, views and favourites you have recorded. Small numbers are noise, so every reason says how much data
    it rests on. Returns {"basis": "sales"|"engagement"|"none", "make_next": [...], "good_looks": [...], "note": str}."""
    from .niches import LIBRARY
    from .products import all_product_types

    rows = (store or Store()).performance()
    types = list(all_product_types())
    made = {(r["niche_name"], r["product_type"]) for r in rows}
    sales = sum(r["units"] for r in rows)
    engagement = sum(r["views"] + r["favourites"] for r in rows)
    basis = "sales" if sales else "engagement" if engagement else "none"

    def score(r):  # revenue counts most; favourites show intent more than views
        return r["revenue"] * 10 + r["units"] * 3 + r["favourites"] * 1.5 + r["views"] * 0.05

    ranked = [r for r in sorted(rows, key=score, reverse=True) if score(r) > 0]
    out: list[dict] = []
    for r in ranked[:3]:   # more of what works: same audience, a different product
        for t in types:
            if (r["niche_name"], t) not in made and t != "wall_art":
                why = (f"{r['niche_name']} {r['product_type'].replace('_', ' ')} has {r['units']} sale(s) and {r['views']} views so far. "
                       "A matching product speaks to the same buyers.")
                out.append({"niche": r["niche_name"], "product_type": t, "reason": why, "kind": "same audience"})
                break
    best_type = ranked[0]["product_type"] if ranked else None
    if best_type:   # same product type for audiences you have not tried
        tried = {r["niche_name"] for r in rows}
        for nz in LIBRARY.values():
            if nz.name not in tried and len(out) < limit:
                out.append({"niche": nz.name, "product_type": best_type,
                            "reason": f"{best_type.replace('_', ' ')} is your best result so far. This audience is new to you.", "kind": "new audience"})
    if not out:   # nothing learned yet: untried built-in combinations
        for nz in LIBRARY.values():
            for t in ("weekly_planner", "habit_tracker", "checklist_pack"):
                if (nz.name, t) not in made and len(out) < limit:
                    out.append({"niche": nz.name, "product_type": t, "reason": "You have not tried this yet.", "kind": "untried"})
                    break
    looks: dict[str, float] = {}
    for r in ranked:
        pal = (r["style"] or "").split("-")[0]
        if pal:
            looks[pal] = looks.get(pal, 0) + score(r)
    note = {"sales": f"Based on {sales} recorded sale(s). Small numbers can mislead, so treat these as hints and keep testing.",
            "engagement": "No sales recorded yet. These lean on views and favourites, which are only a weak signal.",
            "none": "No results recorded yet. Record views and sales (Sales & learning) and these suggestions will learn from them."}[basis]
    return {"basis": basis, "make_next": out[:limit], "good_looks": [k for k, _ in sorted(looks.items(), key=lambda kv: -kv[1])[:3]], "note": note}
