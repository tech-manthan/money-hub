"""Editable slide-deck templates (.pptx) built with the deckcraft tool.

`slide_commands` turns a palette and font pair into a list of deckcraft commands (12 widescreen slides, 960 x 540 pt). Every object is a
normal text box or shape, so the buyer can click, retype, recolour and move anything. `build_deck` runs the commands, writes the .pptx,
renders every slide to PNG and re-opens the file; a deck that does not pass those checks is deleted. Nothing here raises."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import crafttools as ct

W, H = 960, 540
M = 60          # side margin
Cmd = tuple[str, dict]


@dataclass(frozen=True)
class Look:
    paper: str
    ink: str
    muted: str
    accent: str
    accent_ink: str
    soft: str
    accent2: str
    line: str
    heading: str
    body: str


FAMILIES = {"PlayfairDisplay": "Playfair Display", "DMSans": "DM Sans"}


def family(key: str) -> str:
    """The font's real family name (what PowerPoint matches against installed fonts), from MoneyHub's file-style key."""
    return FAMILIES.get(key, key)


def _look(style) -> Look:
    p, f = style.palette, style.fonts
    return Look(p.paper, p.ink, p.muted, p.accent, p.accent_ink, p.soft, p.accent2, p.line, family(f.heading), family(f.body))


class _Slide:
    """Collects the commands for one slide."""

    def __init__(self, look: Look, bg: str):
        self.l = look
        self.cmds: list[Cmd] = [("slide.new", {"layout": "blank"}), ("design.background", {"color": bg})]

    def box(self, rect, fill, preset="roundRect", text="", color=None, size=18, bold=False, font=None, align="center", line=None, name=""):
        self.cmds.append(("shape.insert", {"preset": preset, "rect": list(rect), **({"text": text} if text else {})}))
        self.cmds.append(("shape.fill", {"color": fill} if fill else {"none": True}))
        self.cmds.append(("shape.line", {"color": line, "width": 1.5} if line else {"none": True}))
        if preset == "roundRect":
            self.cmds.append(("shape.adjust", {"index": 0, "value": 0.12}))
        if text:
            self.cmds += self._format(color or self.l.ink, size, bold, font or self.l.body, align)
        if name:
            self.cmds.append(("shape.rename", {"name": name}))
        return self

    def text(self, rect, text, size=18, color=None, bold=False, font=None, align="left", name=""):
        self.cmds.append(("insert.textBox", {"rect": list(rect), "text": text}))
        self.cmds += self._format(color or self.l.ink, size, bold, font or self.l.body, align)
        if name:
            self.cmds.append(("shape.rename", {"name": name}))
        return self

    def title(self, text, color=None, y=40):
        return self.text((M, y, W - 2 * M, 60), text, 34, color or self.l.ink, True, self.l.heading, name="Title")

    def _format(self, color, size, bold, font, align) -> list[Cmd]:
        return [("format.size", {"size": size}), ("format.bold", {"on": bold}), ("format.color", {"color": color}),
                ("format.font", {"family": font}), ("format.align", {"align": align})]


def slide_commands(style, names: dict | None = None) -> tuple[list[Cmd], int]:
    """The full command list for the deck and the number of slides. `names` can override sample wording (title, subtitle, items)."""
    l = _look(style)
    n = names or {}
    title = n.get("title", "Your Presentation Title")
    cmds: list[Cmd] = [("file.new", {"blank": True}), ("design.fonts", {"major": l.heading, "minor": l.body}),
                       ("design.colors", {"colors": {"dk1": l.ink, "lt1": l.paper, "dk2": l.muted, "lt2": l.soft, "accent1": l.accent, "accent2": l.accent2}}),
                       ("design.slideSize", {"w": W, "h": H})]
    slides: list[_Slide] = []

    # 1 title
    s = _Slide(l, l.accent)
    s.box((M, 200, 70, 8), l.accent2, "rect", name="Accent bar")
    s.text((M, 220, 760, 130), title, 54, l.accent_ink, True, l.heading, name="Title")
    s.text((M, 360, 700, 40), n.get("subtitle", "Subtitle or presenter name"), 22, l.accent_ink, False, l.body, name="Subtitle")
    s.text((M, 470, 500, 30), "Date  |  Company or event", 14, l.accent_ink, False, l.body, name="Footer")
    slides.append(s)

    # 2 agenda
    s = _Slide(l, l.paper).title("Agenda")
    for i, item in enumerate(["Introduction", "The problem", "Our approach", "Results", "Next steps"]):
        y = 130 + i * 70
        s.box((M, y, 48, 48), l.accent, "ellipse", str(i + 1), l.accent_ink, 20, True, l.heading, name=f"Number {i + 1}")
        s.text((M + 70, y + 6, 700, 40), item, 24, l.ink, False, l.body, name=f"Agenda item {i + 1}")
    slides.append(s)

    # 3 section header
    s = _Slide(l, l.soft)
    s.text((M, 150, 300, 140), "01", 110, l.accent, True, l.heading, name="Section number")
    s.text((M, 300, 800, 80), "Section title goes here", 40, l.ink, True, l.heading, name="Section title")
    s.text((M, 380, 700, 50), "One line that introduces what comes next.", 20, l.muted, False, l.body, name="Section note")
    slides.append(s)

    # 4 two columns
    s = _Slide(l, l.paper).title("Two columns")
    for i, head in enumerate(["First idea", "Second idea"]):
        x = M + i * 420
        s.box((x, 130, 400, 330), l.soft, "roundRect", name=f"Card {i + 1}")
        s.text((x + 24, 150, 340, 40), head, 24, l.accent, True, l.heading, name=f"Column {i + 1} heading")
        s.text((x + 24, 200, 350, 240), "Replace this text with your own points.\nKeep each point short.\nOne idea per line.", 22, l.ink, False, l.body, name=f"Column {i + 1} text")
    slides.append(s)

    # 5 quote
    s = _Slide(l, l.paper)
    s.box((M, 120, 10, 250), l.accent2, "rect", name="Quote bar")
    s.text((M + 40, 120, 800, 220), "“A short, memorable quote or key message goes here.”", 38, l.ink, True, l.heading, name="Quote")
    s.text((M + 40, 380, 600, 40), "Name, role", 18, l.muted, False, l.body, name="Attribution")
    slides.append(s)

    # 6 numbers
    s = _Slide(l, l.paper).title("Key numbers")
    for i, (big, label) in enumerate([("85%", "Describe this number"), ("3.2x", "Describe this number"), ("12k", "Describe this number")]):
        x = M + i * 290
        s.box((x, 150, 260, 260), l.soft if i != 1 else l.accent, "roundRect", name=f"Stat card {i + 1}")
        s.text((x + 10, 200, 240, 90), big, 56, l.accent if i != 1 else l.accent_ink, True, l.heading, "center", name=f"Stat {i + 1}")
        s.text((x + 20, 310, 220, 60), label, 18, l.ink if i != 1 else l.accent_ink, False, l.body, "center", name=f"Stat label {i + 1}")
    slides.append(s)

    # 7 process
    s = _Slide(l, l.paper).title("Our process")
    s.box((M + 40, 258, W - 2 * M - 80, 4), l.line, "rect", name="Process line")
    for i, step in enumerate(["Plan", "Design", "Build", "Launch"]):
        x = M + 30 + i * 215
        s.box((x, 225, 70, 70), l.accent if i % 2 == 0 else l.accent2, "ellipse", str(i + 1), l.accent_ink, 24, True, l.heading, name=f"Step {i + 1}")
        s.text((x - 30, 315, 130, 36), step, 22, l.ink, True, l.heading, "center", name=f"Step {i + 1} title")
        s.text((x - 40, 355, 150, 60), "Short description of this step", 14, l.muted, False, l.body, "center", name=f"Step {i + 1} text")
    slides.append(s)

    # 8 image grid
    s = _Slide(l, l.paper).title("Image gallery")
    for i in range(6):
        x, y = M + (i % 3) * 290, 125 + (i // 3) * 190
        s.box((x, y, 270, 170), l.soft, "roundRect", "Drop an image here", l.muted, 14, False, l.body, line=l.accent, name=f"Image {i + 1}")
    slides.append(s)

    # 9 comparison
    s = _Slide(l, l.paper).title("Before and after")
    for i, (head, fill, ink) in enumerate([("Before", l.soft, l.ink), ("After", l.accent, l.accent_ink)]):
        x = M + i * 420
        s.box((x, 130, 400, 330), fill, "roundRect", name=f"{head} card")
        s.text((x + 24, 150, 340, 40), head, 26, l.accent if i == 0 else l.accent_ink, True, l.heading, name=f"{head} heading")
        s.text((x + 24, 205, 350, 230), "Point one\nPoint two\nPoint three", 26, ink, False, l.body, name=f"{head} text")
    slides.append(s)

    # 10 team
    s = _Slide(l, l.paper).title("Meet the team")
    for i in range(3):
        x = M + i * 290
        s.box((x + 80, 140, 110, 110), l.soft, "ellipse", "Photo", l.muted, 14, False, l.body, line=l.accent, name=f"Photo {i + 1}")
        s.text((x, 270, 270, 36), "Name Surname", 22, l.ink, True, l.heading, "center", name=f"Name {i + 1}")
        s.text((x, 308, 270, 30), "Role", 16, l.accent, False, l.body, "center", name=f"Role {i + 1}")
        s.text((x + 15, 345, 240, 70), "One line about this person.", 14, l.muted, False, l.body, "center", name=f"Bio {i + 1}")
    slides.append(s)

    # 11 plans
    s = _Slide(l, l.paper).title("Plans and pricing")
    for i, (plan, price) in enumerate([("Basic", "$9"), ("Standard", "$29"), ("Premium", "$59")]):
        x = M + i * 290
        top = i == 1
        s.box((x, 130, 260, 330), l.accent if top else l.soft, "roundRect", name=f"{plan} card")
        s.text((x + 10, 150, 240, 34), plan, 22, l.accent_ink if top else l.accent, True, l.heading, "center", name=f"{plan} name")
        s.text((x + 10, 195, 240, 70), price, 48, l.accent_ink if top else l.ink, True, l.heading, "center", name=f"{plan} price")
        s.text((x + 30, 285, 200, 150), "Feature one\nFeature two\nFeature three", 20, l.accent_ink if top else l.ink, False, l.body, "center", name=f"{plan} features")
    slides.append(s)

    # 12 thank you
    s = _Slide(l, l.accent)
    s.text((M, 180, 840, 110), "Thank you", 66, l.accent_ink, True, l.heading, name="Title")
    s.box((M, 300, 70, 8), l.accent2, "rect", name="Accent bar")
    s.text((M, 330, 700, 90), "name@example.com\nwebsite.com  |  @handle", 22, l.accent_ink, False, l.body, name="Contact")
    slides.append(s)

    for s in slides:
        cmds += s.cmds
    return cmds, len(slides)


# ---------------------------------------------------------------------------------------------------------- running the tool
def _args(cmds: list[Cmd], out: Path) -> list[str]:
    a = ["run"]
    for cid, params in cmds:
        a += ["--cmd", f"{cid}={json.dumps(params, ensure_ascii=False)}"]
    return a + ["--save", str(out)]


def build_deck(style, out: Path, png_dir: Path, timeout: float = 180.0, names: dict | None = None) -> tuple[bool, int, str]:
    """Write the .pptx to `out` and a PNG of every slide to `png_dir`. Returns (ok, slide count, message). A deck that cannot be re-opened with
    the expected slide count, or that does not render every slide, is deleted. Never raises."""
    try:
        if ct.find_tool("deckcraft") is None:
            return False, 0, "deckcraft is not installed (scripts/install_craft_tools.sh)"
        cmds, n = slide_commands(style, names)
        out.parent.mkdir(parents=True, exist_ok=True)
        r = ct.run("deckcraft", _args(cmds, out), timeout)
        if not (r.ok and out.exists() and out.stat().st_size > 2000):
            out.unlink(missing_ok=True)
            return False, 0, ((r.err or r.out).strip() or "deckcraft wrote nothing")[:200]
        info = ct.run("deckcraft", ["info", str(out)], timeout)
        try:
            count = len(json.loads(info.out).get("slides") or [])
        except (ValueError, AttributeError, TypeError):
            count = 0
        if not info.ok or count != n:
            out.unlink(missing_ok=True)
            return False, 0, f"re-opened deck has {count} slides, expected {n}"
        png_dir.mkdir(parents=True, exist_ok=True)
        r = ct.run("deckcraft", ["render", str(out), "--all", str(png_dir)], timeout)
        pngs = sorted(png_dir.glob("slide-*.png"))
        if not r.ok or len(pngs) != n:
            out.unlink(missing_ok=True)
            return False, 0, f"rendered {len(pngs)} of {n} slides"
        return True, n, f"{n} slides"
    except Exception as e:   # noqa: BLE001 - optional tool: never break a product
        return False, 0, str(e)[:200]
