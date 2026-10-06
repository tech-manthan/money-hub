"""Design system: palettes, font pairings and layout variants, chosen from a seed so every product looks distinct."""
from __future__ import annotations

import random
from dataclasses import dataclass, field, asdict

from .paths import FONT_DIR


def _lum(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    rgb = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


@dataclass(frozen=True)
class Palette:
    key: str
    mood: tuple[str, ...]
    paper: str      # page background
    ink: str        # body text
    muted: str      # secondary text
    line: str       # hairlines / grid
    accent: str     # brand colour (header bands, buttons)
    accent_ink: str # text colour on accent
    soft: str       # tinted fill
    accent2: str    # secondary highlight

    def issues(self) -> list[str]:
        out = []
        if contrast(self.ink, self.paper) < 7:
            out.append("ink/paper < 7")
        if contrast(self.muted, self.paper) < 4.5:
            out.append("muted/paper < 4.5")
        if contrast(self.accent_ink, self.accent) < 4.5:
            out.append("accent_ink/accent < 4.5")
        if contrast(self.ink, self.soft) < 7:
            out.append("ink/soft < 7")
        return out


PALETTES: list[Palette] = [
    Palette("sage", ("calm", "earthy", "wellness"), "#FFFFFF", "#26332B", "#566259", "#D5DDD4", "#3F6B55", "#FFFFFF", "#E8F0EA", "#C58B4E"),
    Palette("terracotta", ("warm", "earthy", "cozy"), "#FFFFFF", "#33241D", "#6B574D", "#E6D8CE", "#A5502F", "#FFFFFF", "#F8EBE2", "#3F6B73"),
    Palette("ocean", ("calm", "clean", "professional"), "#FFFFFF", "#12263A", "#475C71", "#D3DEE8", "#1F5F8B", "#FFFFFF", "#E5EFF7", "#E08E45"),
    Palette("blush", ("soft", "feminine", "wedding"), "#FFFFFF", "#3A2530", "#6E5360", "#EFD9E0", "#A8456B", "#FFFFFF", "#FBEAF0", "#7E8F6A"),
    Palette("lavender", ("soft", "calm", "creative"), "#FFFFFF", "#2B2440", "#5F5878", "#DEDAF0", "#5B47A6", "#FFFFFF", "#EEEBFA", "#D18A5B"),
    Palette("charcoal", ("bold", "minimal", "professional"), "#FFFFFF", "#1C1C1E", "#55555A", "#DADADD", "#2F3A4A", "#FFFFFF", "#EEF0F3", "#C4572E"),
    Palette("forest", ("earthy", "calm", "outdoors"), "#FFFFFF", "#1F2D24", "#4F6056", "#D3DFD6", "#2D5A3F", "#FFFFFF", "#E6F0E9", "#B8822D"),
    Palette("sunset", ("bold", "warm", "energetic"), "#FFFFFF", "#341F1A", "#6B4B42", "#F2DDD4", "#B8442E", "#FFFFFF", "#FCEBE4", "#2E6F7E"),
    Palette("denim", ("clean", "professional", "bold"), "#FFFFFF", "#162033", "#4A5670", "#D5DAE6", "#2C4A8C", "#FFFFFF", "#E8ECF6", "#C9803B"),
    Palette("mocha", ("warm", "cozy", "minimal"), "#FFFFFF", "#2E241E", "#64544A", "#E4DAD1", "#6F4E37", "#FFFFFF", "#F4ECE4", "#4F7F78"),
    Palette("mint", ("fresh", "clean", "kids"), "#FFFFFF", "#17302C", "#476560", "#D2E6E1", "#1F7A6D", "#FFFFFF", "#E3F4F0", "#D4713E"),
    Palette("plum", ("rich", "bold", "creative"), "#FFFFFF", "#2D1B2E", "#634B66", "#E6D6E7", "#7A2E7A", "#FFFFFF", "#F4E8F4", "#C98B2E"),
]


@dataclass(frozen=True)
class FontPair:
    key: str
    heading: str
    body: str
    script: str
    heading_weights: tuple[int, ...]
    body_weights: tuple[int, ...]


FONT_PAIRS: list[FontPair] = [
    FontPair("editorial", "PlayfairDisplay", "DMSans", "Caveat", (400, 600, 700), (400, 500, 700)),
    FontPair("modern", "Fraunces", "Inter", "Caveat", (400, 600, 700), (400, 500, 600, 700)),
    FontPair("friendly", "Nunito", "Nunito", "Caveat", (600, 700, 800), (400, 600, 700)),
    FontPair("classic", "Lora", "Inter", "Caveat", (400, 600, 700), (400, 500, 600, 700)),
    FontPair("clean", "Poppins", "DMSans", "Caveat", (600, 700), (400, 500, 700)),
    FontPair("warm", "Fraunces", "DMSans", "Caveat", (400, 600, 700), (400, 500, 700)),
]

_POPPINS = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}


def font_file(family: str, weight: int) -> str:
    if family == "Poppins":
        return f"Poppins-{_POPPINS.get(weight, 'Regular')}.ttf"
    return f"{family}-{weight}.ttf"


def font_face_css(family: str, weights: tuple[int, ...]) -> str:
    out = []
    for w in weights:
        path = FONT_DIR / font_file(family, w)
        if path.exists():
            out.append(
                f"@font-face{{font-family:'{family}';font-weight:{w};src:url('{path.as_uri()}');}}"
            )
    return "\n".join(out)


@dataclass
class Style:
    palette: Palette
    fonts: FontPair
    header: str       # band | rule | box
    radius: int       # px for cards
    grid: str         # solid | dotted | dashed
    seed: int
    extra: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.palette.key}-{self.fonts.key}-{self.header}"

    def css_vars(self) -> str:
        p = self.palette
        return (
            f":root{{--paper:{p.paper};--ink:{p.ink};--muted:{p.muted};--line:{p.line};"
            f"--accent:{p.accent};--accent-ink:{p.accent_ink};--soft:{p.soft};--accent2:{p.accent2};"
            f"--radius:{self.radius}px;--gridstyle:{self.grid};"
            f"--font-h:'{self.fonts.heading}';--font-b:'{self.fonts.body}';--font-s:'{self.fonts.script}';}}"
        )

    def font_css(self) -> str:
        parts = [
            font_face_css(self.fonts.heading, self.fonts.heading_weights),
            font_face_css(self.fonts.body, self.fonts.body_weights),
            font_face_css(self.fonts.script, (400, 700)),
        ]
        return "\n".join(dict.fromkeys(parts))

    def describe(self) -> dict:
        return {"palette": self.palette.key, "fonts": self.fonts.key, "header": self.header,
                "radius": self.radius, "grid": self.grid, "seed": self.seed}


HEADERS = ["band", "rule", "box"]
RADII = [0, 6, 12, 18]
GRIDS = ["solid", "dotted", "dashed"]


def choose_style(seed: int | None = None, mood: str | None = None, palette: str | None = None,
                 fonts: str | None = None, header: str | None = None, radius: int | None = None,
                 grid: str | None = None) -> Style:
    """Random look from the seed; any of palette/fonts/header/radius/grid can be pinned."""
    seed = random.SystemRandom().randrange(1, 10**6) if seed is None else seed
    rng = random.Random(seed)
    pool = [p for p in PALETTES if mood and mood in p.mood] or PALETTES
    pal = next((p for p in PALETTES if p.key == palette), None) or rng.choice(pool)
    fp = next((f for f in FONT_PAIRS if f.key == fonts), None) or rng.choice(FONT_PAIRS)
    return Style(
        palette=pal, fonts=fp,
        header=_pick(rng, HEADERS, header),
        radius=_pick(rng, RADII, radius),
        grid=_pick(rng, GRIDS, grid),
        seed=seed,
    )


def _pick(rng: random.Random, choices: list, wanted):
    choice = rng.choice(choices)  # always draw, so pinning one knob does not reshuffle the others
    return wanted if wanted is not None else choice


def font_keys() -> list[str]:
    return [f.key for f in FONT_PAIRS]


def palette_keys() -> list[str]:
    return [p.key for p in PALETTES]


def style_from_dict(d: dict) -> Style:
    return Style(
        palette=next(p for p in PALETTES if p.key == d["palette"]),
        fonts=next(f for f in FONT_PAIRS if f.key == d["fonts"]),
        header=d["header"], radius=d["radius"], grid=d["grid"], seed=d.get("seed", 0),
    )
