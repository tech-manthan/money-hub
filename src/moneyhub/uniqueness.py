"""Keep the catalogue distinct: fingerprint each product's text and warn when a new one is too similar to an old one."""
from __future__ import annotations

import hashlib
import re


def _shingles(text: str, n: int = 3) -> set[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {" ".join(words[i : i + n]) for i in range(max(0, len(words) - n + 1))}


def fingerprint_text(content_json: str) -> str:
    sh = sorted(_shingles(content_json))
    return hashlib.sha1(" ".join(sh).encode()).hexdigest()[:12] + "|" + " ".join(sh[:400])


def similarity(a: str, b: str) -> float:
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
