"""HTML templating + shared print CSS."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..design import Style

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "products" / "templates"


@dataclass(frozen=True)
class PageSize:
    key: str
    label: str
    width_in: float
    height_in: float
    base_pt: float  # root font size, everything else is in em so layouts scale

    @property
    def css_size(self) -> str:
        return f"{self.width_in:.3f}in {self.height_in:.3f}in"

    @property
    def landscape(self) -> bool:
        return self.width_in > self.height_in

    @property
    def px(self) -> tuple[int, int]:
        return round(self.width_in * 150), round(self.height_in * 150)


PAGE_SIZES: dict[str, PageSize] = {
    "letter": PageSize("letter", "US Letter (8.5 x 11 in)", 8.5, 11.0, 10.0),
    "a4": PageSize("a4", "A4 (210 x 297 mm)", 8.268, 11.693, 10.0),
    "a5": PageSize("a5", "A5 (148 x 210 mm)", 5.827, 8.268, 7.4),
    "eink": PageSize("eink", "E-ink tablet (reMarkable / Kindle Scribe / Boox, 3:4)", 6.212, 8.283, 7.8),
    "tablet": PageSize("tablet", "Tablet / GoodNotes (landscape)", 11.25, 8.44, 10.0),
}

# KDP paperback trim sizes (inches). Interiors are built at exactly this size; base_pt scales the type with the page.
KDP_TRIMS: dict[str, tuple[float, float]] = {"5.5x8.5": (5.5, 8.5), "6x9": (6.0, 9.0), "7x10": (7.0, 10.0), "8x10": (8.0, 10.0), "8.5x11": (8.5, 11.0)}
for _k, (_w, _h) in KDP_TRIMS.items():
    PAGE_SIZES[f"kdp_{_k}"] = PageSize(f"kdp_{_k}", f"KDP paperback {_k} in", _w, _h, round(10.0 * _w / 8.5 + 0.6, 2))

BASE_CSS = """
@page { size: {{ page.css_size }}; margin: 0; }
* { box-sizing: border-box; }
html { font-size: {{ page.base_pt }}pt; }
body { margin: 0; color: var(--ink); background: var(--paper); font-family: var(--font-b), 'DejaVu Sans', sans-serif; line-height: 1.3; }
h1,h2,h3,.h { font-family: var(--font-h), 'DejaVu Serif', serif; margin: 0; color: var(--ink); line-height: 1.1; }
.page { width: {{ page.width_in }}in; height: {{ page.height_in }}in; position: relative; overflow: hidden;
        page-break-after: always; break-after: page; padding: {{ margin }}em; display: flex; flex-direction: column; }
.page:last-child { page-break-after: auto; break-after: auto; }
.script { font-family: var(--font-s), cursive; }
.label { font-size: .62em; letter-spacing: .14em; text-transform: uppercase; color: var(--accent); font-weight: 700; }
.muted { color: var(--muted); }
.small { font-size: .78em; }

/* page header */
.hdr { margin-bottom: 1em; display: flex; justify-content: space-between; align-items: flex-end; }
.hdr h2 { font-size: 1.9em; }
.hdr .sub { font-size: .8em; color: var(--muted); }
.hdr.band { background: var(--accent); margin: -{{ margin }}em -{{ margin }}em 1em; padding: {{ margin * 0.8 }}em {{ margin }}em .8em; align-items: center; }
.hdr.band h2, .hdr.band .sub { color: var(--accent-ink); }
.hdr.rule { border-bottom: 3px solid var(--accent); padding-bottom: .5em; }
.hdr.box { border: 2px solid var(--accent); border-radius: var(--radius); padding: .6em .9em; background: var(--soft); align-items: center; }

/* cards & lines */
.card { border: 1px solid var(--line); border-radius: var(--radius); padding: .55em .7em; background: var(--paper); display: flex; flex-direction: column; min-height: 0; }
.fill { display:flex; flex-direction:column; flex:1; min-height:0; }
.fill > .card { flex:1; }
.card.soft { background: var(--soft); border-color: var(--soft); }
.card .label { margin-bottom: .35em; }
.lines { flex: 1; min-height: 1.1em; }
.dots { flex: 1; background-image: radial-gradient(circle, var(--line) 0.7px, transparent 0.9px); background-size: 1.1em 1.1em; }
.check { display: inline-block; width: .85em; height: .85em; border: 1.2px solid var(--accent); border-radius: 50%; margin-right: .25em; vertical-align: -.1em; }
.sq { display: inline-block; width: .85em; height: .85em; border: 1.2px solid var(--accent); border-radius: 2px; vertical-align: -.1em; }
.footer { margin-top: auto; padding-top: .5em; font-size: .62em; color: var(--muted); display: flex; justify-content: space-between; align-items: center; letter-spacing: .04em; }
.nav a { color: var(--accent); text-decoration: none; font-weight: 700; margin-left: .8em; letter-spacing: .1em; text-transform: uppercase; }
"""


def make_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True, lstrip_blocks=True,
    )


_env = make_env()


def lines_css(style: Style, page: PageSize) -> str:
    """Ruled lines as one repeating SVG background (a single element is far faster to lay out than N divs)."""
    lh = 1.9 * page.base_pt * 96 / 72  # px
    dash = {"solid": "", "dotted": "stroke-dasharray='1.5 4' stroke-linecap='round'", "dashed": "stroke-dasharray='9 6'"}[style.grid]
    col = style.palette.line.replace("#", "%23")
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='200' height='{lh:.2f}' viewBox='0 0 200 {lh:.2f}' preserveAspectRatio='none'>"
           f"<line x1='0' y1='{lh - 0.8:.2f}' x2='200' y2='{lh - 0.8:.2f}' stroke='{col}' stroke-width='1.1' {dash}/></svg>")
    return (f".lines{{background-image:url(\"data:image/svg+xml;utf8,{svg}\");background-repeat:repeat-y;"
            f"background-size:100% {lh:.2f}px;background-position:0 100%;}}")


def base_css(style: Style, page: PageSize, margin: float = 3.4) -> str:
    css = _env.from_string(BASE_CSS).render(page=page, margin=margin)
    return "\n".join([style.font_css(), style.css_vars(), css, lines_css(style, page)])


def render_html(template: str, style: Style, page: PageSize, extra_css: str = "", margin: float = 3.4, **ctx) -> str:
    body = _env.get_template(template).render(page=page, style=style, **ctx)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{base_css(style, page, margin)}\n{extra_css}</style></head><body>{body}</body></html>"
    )
