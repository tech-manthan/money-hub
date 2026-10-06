"""Tone presets: how a brag feels (pacing, transitions, type, music)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tone:
    key: str
    feel: str
    scenes: tuple[int, int]          # min/max scene count
    transitions: tuple[str, ...]     # allowed transition kinds
    caps: bool                       # ALL CAPS headlines
    anim: str                        # headline entrance: rise | pop | slide | type | fade
    bpm: int
    mood: str                        # music mood key (see audio.py)
    hold: float                      # extra hold after text settles (seconds)
    brief: str                       # guidance for the planner


TONES: dict[str, Tone] = {t.key: t for t in (
    Tone("default", "Punchy, playful, clean", (4, 5), ("fade", "slide", "dip"), False, "rise", 112, "bright", 0.5,
         "Punchy, playful, clean. 4-5 scenes, soft transitions."),
    Tone("polished", "Serious, elegant, restrained", (3, 4), ("fade", "dip"), False, "fade", 84, "calm", 1.0,
         "Serious, elegant, restrained. 3-4 scenes with long holds and soft fades."),
    Tone("yc-parody", "Deadpan startup launch, played straight", (4, 5), ("cut",), False, "type", 120, "corporate", 0.4,
         "Deadpan startup launch video played completely straight, one claim per scene, hard cuts."),
    Tone("chaotic", "FAST, LOUD, ALL CAPS", (6, 8), ("flash", "zoom", "cut"), True, "pop", 140, "driving", 0.15,
         "FAST, LOUD, ALL CAPS. 6-8 scenes, some under 2 seconds, flash and zoom cuts."),
    Tone("deadpan", "Calm, dry, nothing is a joke", (3, 4), ("fade", "dip"), False, "fade", 70, "minimal", 1.2,
         "Calm and dry; nothing is a joke. 3-4 scenes with big empty space and slow fades."),
    Tone("cinematic", "Trailer-scale, epic claims", (4, 5), ("wipe", "dip", "zoom"), True, "rise", 90, "epic", 0.8,
         "Trailer-scale and epic with big type and dramatic wipes. Never fake claims; make the real thing feel huge."),
    Tone("app-store", "Clean feature cards", (4, 6), ("slide", "fade"), False, "slide", 108, "bright", 0.5,
         "Clean feature cards, smooth slides, 4-6 scenes."),
)}

_KEYWORDS = {
    "yc-parody": ("series a", "startup", "yc", "y combinator", "pitch", "disrupt", "vc"),
    "chaotic": ("chaos", "chaotic", "fast", "loud", "hype", "meme", "unhinged", "crazy"),
    "deadpan": ("deadpan", "dry", "calm", "understated", "quiet", "minimal"),
    "cinematic": ("cinematic", "epic", "trailer", "movie", "dramatic", "blockbuster"),
    "polished": ("polished", "elegant", "serious", "premium", "luxury", "refined"),
    "app-store": ("app store", "feature card", "apple"),
}


def resolve_tone(text: str | None) -> tuple[Tone, str]:
    """Preset name or free-form direction -> (nearest preset, extra direction passed to the planner)."""
    if not text:
        return TONES["default"], ""
    t = text.strip().lower()
    if t in TONES:
        return TONES[t], ""
    for key, words in _KEYWORDS.items():
        if any(w in t for w in words):
            return TONES[key], text.strip()
    return TONES["default"], text.strip()
