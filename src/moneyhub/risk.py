"""Listing risk check: brand/trademark terms, 'inspired by' phrasing, risky claims and rights language.

The built-in watch list comes from marketplace guidance and seller-compliance write-ups (see docs/research/02 and 05). It is a
safety net, not legal advice: add your own terms in moneyhub.yaml under `risk.extra_terms`."""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict

from .config import get_config

# term -> (severity, group)
_WATCH: dict[str, tuple[str, str]] = {}


def _add(group: str, severity: str, *terms: str) -> None:
    for t in terms:
        _WATCH[t.lower()] = (severity, group)


_add("Entertainment / characters", "high",
     "disney", "mickey mouse", "minnie mouse", "marvel", "avengers", "spider-man", "spiderman", "star wars", "jedi", "mandalorian",
     "harry potter", "hogwarts", "pokemon", "pokémon", "pikachu", "hello kitty", "sesame street", "elmo", "peppa pig", "bluey",
     "paw patrol", "barbie", "taylor swift", "eras tour", "swiftie", "bts", "beyonce", "stranger things",
     "minecraft", "roblox", "fortnite", "zelda", "nintendo", "sanrio", "winnie the pooh", "snoopy", "peanuts", "squishmallow",
     "lego", "hot wheels", "cocomelon", "gabby's dollhouse", "ghibli", "totoro", "naruto", "pixar", "dc comics", "batman")
_add("Sports leagues / events", "high",
     "nfl", "nba", "mlb", "nhl", "fifa", "super bowl", "superbowl", "olympic", "olympics", "ufc", "wwe", "march madness", "premier league")
_add("Brands (often trademarked)", "high",
     "nike", "adidas", "lululemon", "starbucks", "coca-cola", "coca cola", "stanley cup", "gucci", "chanel", "louis vuitton", "tiffany",
     "disneyland", "ikea", "walmart", "amazon basics", "apple watch")
_add("Ambiguous words that are also trademarks", "medium",
     "elsa", "moana", "mario", "peanuts", "yeti", "tesla", "polaroid", "world cup", "frozen movie", "target store", "one piece anime")
_add("Generic words that are trademarks", "medium",
     "onesie", "velcro", "band-aid", "bandaid", "kleenex", "post-it", "sharpie", "ziploc", "jacuzzi", "crock-pot", "rollerblade", "q-tip",
     "tupperware", "jello", "popsicle", "frisbee", "xerox", "scotch tape", "bubble wrap", "chapstick", "ping pong", "plexiglas", "tylenol")
_add("Platform / tool names (fine to say 'for X' in the description, avoid in title and tags)", "low",
     "goodnotes", "notability", "ipad", "iphone", "excel", "google sheets", "canva", "notion", "samsung notes", "remarkable", "kindle scribe",
     "pinterest", "etsy", "amazon", "instagram", "tiktok")

_PHRASES = [  # (regex, severity, advice)
    (r"\b(inspired by|fan art|fanart|parody of|style of|in the style|not affiliated with|unofficial|tribute to|dupe)\b", "high",
     "Disclaimers like this do not protect you: marketplace scanners match the brand word anyway."),
    (r"\b(guarantee[sd]?|guaranteed results?|100% success|risk[- ]free)\b", "medium", "Avoid guarantees you cannot back."),
    (r"\b(cure[sd]?|treats? (?:your |the )?(?:adhd|anxiety|depression|insomnia|pain|condition|disease|disorder)|treatment for|heals?|diagnos\w+|clinically proven|doctor[- ]recommended|medical grade)\b", "medium",
     "Avoid health claims; say what the product helps you organise or track instead."),
    (r"\b(make|earn)\s+\$?\d[\d,]*\s*(/|per|a)?\s*(day|week|month|year)?\b|\bpassive income\b|\bget rich\b", "medium", "Avoid income claims."),
    (r"\b(resell|resale|master resell|mrr|plr|private label rights|commercial use allowed|rebrand)\b", "medium",
     "Rights language can trigger reviews; this product is sold for personal use."),
    (r"\b(free download|free printable)\b", "low", "'Free' in a paid listing can confuse buyers."),
    (r"\b(best seller|bestseller|#1|number one|top rated)\b", "low", "Unverifiable superlatives; remove unless you can prove them."),
]

SEVERITY_ORDER = {"high": 3, "medium": 2, "low": 1}


@dataclass
class Finding:
    where: str       # title | tags | description | pins | content | niche
    term: str
    severity: str
    group: str
    advice: str

    def to_dict(self):
        return asdict(self)


def _watch_terms() -> dict[str, tuple[str, str]]:
    terms = dict(_WATCH)
    for t in get_config().get("risk.extra_terms") or []:
        terms[str(t).lower()] = ("high", "Your own watch list")
    return terms


def scan_text(text: str, where: str) -> list[Finding]:
    out: list[Finding] = []
    low = text.lower()
    for term, (sev, group) in _watch_terms().items():
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", low):
            if group.startswith("Platform") and where in ("description", "content", "pins"):
                continue  # naming the app you are compatible with is normal in the description
            advice = ("Remove it from titles and tags; you may mention compatibility in the description."
                      if group.startswith("Platform") else "Rewrite without the brand/character name.")
            out.append(Finding(where, term, sev, group, advice))
    for rx, sev, adv in _PHRASES:
        if "resell" in rx and where not in ("title", "tags", "pins", "niche"):
            continue  # the description legitimately says "no resale"
        for m in re.finditer(rx, low):
            out.append(Finding(where, m.group(0).strip(), sev, "Risky phrasing", adv))
    return out


def scan_listing(listing: dict, content_text: str = "", niche: str = "") -> list[Finding]:
    c = listing.get("copy_", listing)
    out: list[Finding] = []
    if niche:
        out += scan_text(niche, "niche")
    out += scan_text(c.get("title"), "title")
    out += scan_text(c.get("short_title"), "title")
    out += scan_text(" ".join(c.get("tags", [])), "tags")
    out += scan_text(listing.get("description"), "description")
    out += scan_text(" ".join(c.get("pin_titles", []) + c.get("pin_headlines", []) + [c.get("pin_description")]), "pins")
    if content_text:
        out += scan_text(content_text, "content")
    # de-duplicate
    seen, uniq = set(), []
    for f in out:
        k = (f.where, f.term)
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    return sorted(uniq, key=lambda f: -SEVERITY_ORDER[f.severity])


def status(findings: list[Finding]) -> str:
    top = max((SEVERITY_ORDER[f.severity] for f in findings), default=0)
    return "fail" if top >= 3 else "warn" if top == 2 else "pass"
