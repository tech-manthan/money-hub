"""Spelling QA for product content and listing text. Warns only: a flagged word may be a niche term, never a blocker."""
from __future__ import annotations

import json
import re

from .niches import NicheProfile
from .qa import Check

_WORD = re.compile(r"[A-Za-z][A-Za-z'’]*")
# Words that are normal here but missing from a general dictionary.
_EXTRA = {
    "cricut", "dxf", "eps", "scanncut", "glowforge", "colorists", "colorist", "mandala", "mandalas", "coloring", "svgs", "cutters", "welded", "weld",
    "scrapbookers", "scrapbooker", "scrapbooking", "scrapbook", "crafters", "crafter", "apps", "app", "seamless", "gingham", "harlequin", "jpgs", "pngs",
    "boho", "clipart", "cliparts", "colourway", "colourways", "procreate", "cricut", "photoshop", "illustrator", "inkscape", "affinity",
    "terrazzo", "vectors", "scalable", "transparency", "sublimation",
    "etsy", "gumroad", "payhip", "ko-fi", "kofi", "pinterest", "goodnotes", "notability", "remarkable", "boox", "kindle", "scribe",
    "pdf", "pdfs", "xlsx", "jpg", "jpeg", "png", "svg", "zip", "gsheet", "gsheets", "excel", "numbers", "canva", "notion", "kdp",
    "printable", "printables", "undated", "hyperlinked", "planner", "planners", "tracker", "trackers", "worksheet", "worksheets",
    "adhd", "srgb", "dpi", "ai", "ui", "diy", "wifi", "tiktok", "reels", "pins", "pin", "tabs", "mockup", "mockups", "checklist", "checklists",
    "decluttering", "meal", "preps", "meds", "ebook", "ebooks", "eink", "e-ink", "a4", "a5", "ios", "ipad", "ipads", "samsung",
    "moneyhub", "affirmations", "weekly", "monthly", "dotted", "habit", "habits", "lifestyle", "homeschool", "homeschooling",
    "wi", "fi", "etc", "vs", "okay", "ok", "gen", "z", "mom", "moms", "mum", "mums", "pre", "non", "re", "tabbed", "spreadsheet",
    "cardstock", "builtin", "printout", "printouts", "cutout", "cutouts", "downloadable", "tablet-friendly", "goodnotes", "samsung",
    "spreadsheets", "gsheet", "google", "sheets", "numbers", "onenote", "evernote", "todoist", "bujo", "journaling", "journal",
}


def _us_variants(w: str) -> list[str]:
    """British spellings are fine: map them to the American form the dictionary knows."""
    out = []
    for pat, rep in ((r"our(s|ed|ing|ful|ite)?$", r"or\1"), (r"is(e|es|ed|ing|ation|ations)$", r"iz\1"), (r"ys(e|es|ed|ing)$", r"yz\1"),
                     (r"ll(ed|ing|er|ers)$", r"l\1"), (r"ogue(s)?$", r"og\1"), (r"re(s)?$", r"er\1"), (r"ence$", "ense"), (r"ae", "e"), (r"oe", "e")):
        v = re.sub(pat, rep, w)
        if v != w:
            out.append(v)
    return out


def _checker():
    try:
        from spellchecker import SpellChecker
    except ImportError:
        return None
    return SpellChecker()


def _strings(obj) -> list[str]:
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        return [t for v in obj.values() for t in _strings(v)]
    if isinstance(obj, (list, tuple)):
        return [t for v in obj for t in _strings(v)]
    return []


def _niche_words(niche: NicheProfile | None, extra: str) -> set[str]:
    text = " ".join(_strings(niche.model_dump()) if niche else []) + " " + extra
    return {w.lower().strip("'’") for w in _WORD.findall(text)}


def misspellings(texts: list[str], niche: NicheProfile | None = None, allow: str = "") -> list[tuple[str, str]]:
    """(word, suggestion) for words not in the dictionary, the niche vocabulary or the allow-list. Empty if unavailable."""
    sc = _checker()
    if sc is None:
        return []
    known = _EXTRA | _niche_words(niche, allow)
    seen, out = set(), []
    for text in texts:
        text = re.sub(r"https?://\S+|\S+@\S+|[A-Za-z]*\d[\w-]*", " ", text)  # urls, emails, tokens with digits
        for raw in _WORD.findall(text):
            w = raw.lower().replace("’", "'")
            base = w[:-2] if w.endswith("'s") else w
            if base in seen or base in known or len(base) <= 2 or raw.isupper():
                continue
            seen.add(base)
            parts = [p for p in re.split(r"-", base) if p]
            if all(p in known or p in sc for p in parts) and parts:
                continue
            if any(v in sc for v in _us_variants(base)):
                continue
            if base in sc.unknown([base]) and base.rstrip("'") not in sc:
                out.append((raw, sc.correction(base) or ""))
    return out


def spelling_check(content_json: str, listing: dict, niche: NicheProfile | None = None) -> Check:
    if _checker() is None:
        return Check("Spelling", "warn", "spell-check not installed (pip install pyspellchecker)")
    texts = _strings(json.loads(content_json)) + _strings(listing)
    bad = misspellings(texts, niche)
    if not bad:
        return Check("Spelling", "pass", f"checked {len(texts)} text fields; no unknown words")
    shown = "; ".join(f"{w}" + (f" → {s}" if s and s.lower() != w.lower() else "") for w, s in bad[:10])
    more = f" (+{len(bad) - 10} more)" if len(bad) > 10 else ""
    return Check("Spelling", "warn", f"check these words: {shown}{more}")
