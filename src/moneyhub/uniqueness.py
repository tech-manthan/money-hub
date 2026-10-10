"""Keep the catalogue distinct: fingerprint each product's text and warn when a new one is too similar to an old one."""
from __future__ import annotations

import hashlib
import json
import re


def _shingles(text: str, n: int = 3) -> set[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {" ".join(words[i : i + n]) for i in range(max(0, len(words) - n + 1))}


def fingerprint_text(content_json: str) -> str:
    sh = sorted(_shingles(content_json))
    return hashlib.sha1(" ".join(sh).encode()).hexdigest()[:12] + "|" + " ".join(sh[:400])


def design_fingerprint(key: str, palette: str, seed: int, sizes: list[str], options: dict) -> str:
    """For products whose text never changes (clipart, papers, cut files...): what makes one different is the design inputs, so two
    products match only when type, colours, seed, sizes and options are all the same."""
    raw = json.dumps([key, palette, seed, sorted(sizes), options], sort_keys=True, default=str)
    return "sig:" + hashlib.sha1(raw.encode()).hexdigest()[:16]


def similarity(a: str, b: str) -> float:
    if a.startswith("sig:") or b.startswith("sig:"):
        return 1.0 if a == b else 0.0
    sa = set(a.split("|", 1)[-1].split(" "))
    sb = set(b.split("|", 1)[-1].split(" "))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def most_similar(fp: str, others: list[tuple[int, str, str]]) -> tuple[float, int | None, str]:
    best = (0.0, None, "")
    for pid, title, ofp in others:
        s = similarity(fp, ofp) if ofp else 0.0
        if s > best[0]:
            best = (s, pid, title)
    return best


CROSS_TYPE_THRESHOLD = 0.6


def content_signature(palette: str, options: dict, meta: dict) -> list[str]:
    """What a niche-free pack is made of, as comparable tokens: its colours, its theme and the figures / patterns it drew."""
    toks = {f"palette:{palette}"}
    if options.get("theme"):
        toks.add(f"theme:{options['theme']}")
    toks |= {f"item:{x}" for x in meta.get("signature", [])}
    return sorted(toks)


def signature_similarity(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if sa and sb else 0.0


def cross_type_match(sig: list[str], ptype: str, others: list[tuple[int, str, str, list[str]]]) -> tuple[float, int | None, str, str]:
    """Closest pack of a DIFFERENT type: (similarity, id, title, type). others = (id, title, type, signature)."""
    best = (0.0, None, "", "")
    for pid, title, otype, osig in others:
        if otype == ptype or not osig:
            continue
        s = signature_similarity(sig, osig)
        if s > best[0]:
            best = (s, pid, title, otype)
    return best
