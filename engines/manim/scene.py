"""Manim Community scene for MoneyHub: reads a plan JSON (path in MONEYHUB_PLAN) and animates it.

Run through MoneyHub (`render.motion: [manim]`) or directly:
    MONEYHUB_PLAN=plan.json manim render -r 1000,1500 --fps 24 scene.py MoneyScene
"""
import json
import os
import textwrap
from contextlib import ExitStack

from manim import (DOWN, LEFT, RIGHT, UP, Circle, FadeIn, FadeOut, Group, ImageMobject, LaggedStart, ManimColor,
                   Rectangle, Scene, Text, VGroup, config, register_font)

PLAN = json.load(open(os.environ["MONEYHUB_PLAN"]))
W, H = PLAN["width"], PLAN["height"]
config.frame_height = 14.0
config.frame_width = 14.0 * W / H
FH = config.frame_height
S = min(W, H) / 1000          # design scale: sizes below are written for a 1000px-wide canvas
PAL = {k: ManimColor(v) for k, v in PLAN["palette"].items()}
HEAD, BODY, SCRIPT = PLAN["fonts"]["heading"], PLAN["fonts"]["body"], PLAN["fonts"]["script"]


def unit(px: float) -> float:
    """Design pixels -> Manim units."""
    return px * S * FH / H


def wrap(text: str, px: float, frac: float) -> str:
    chars = max(8, int(frac * W / (0.52 * px * S)))
    return "\n".join(textwrap.wrap(text, chars)) or text


class MoneyScene(Scene):
    def construct(self):
        with ExitStack() as stack:
            for f in PLAN["fontPaths"]:
                stack.enter_context(register_font(f))
            probe = Text("Hg", font=HEAD, font_size=100)
            self.K = probe.height / 100          # units of height per font-size point
            self._build()

    def fs(self, px: float) -> float:
        return unit(px) / self.K

    def _build(self):
        pages = [ImageMobject(p) for p in PLAN["pages"]]
        for i, s in enumerate(PLAN["scenes"]):
            kind, secs = s["kind"], float(s["seconds"])
            dark = kind == "cta"
            self.camera.background_color = PAL["accent"] if dark else PAL["soft"]
            ink = PAL["accentInk"] if dark else PAL["ink"]
            group = Group()
            if kind in ("title", "cta"):
                t = Text(wrap(s["text"], 96, 0.8), font=HEAD, weight="BOLD", color=ink, font_size=self.fs(96), line_spacing=0.9)
                t.move_to(UP * FH * 0.08)
                chip = Text("INSTANT DOWNLOAD", font=BODY, weight="BOLD", font_size=self.fs(30), color=PAL["accent"] if dark else PAL["accentInk"])
                pill = Rectangle(width=chip.width + unit(90), height=chip.height + unit(40), fill_opacity=1, stroke_width=0,
                                 fill_color=PAL["paper"] if dark else PAL["accent"]).round_corners(unit(37))
                pill.next_to(t, DOWN, buff=unit(70))
                chip.move_to(pill)
                self.play(FadeIn(t, shift=UP * unit(40)), run_time=0.7)
                self.play(FadeIn(pill), FadeIn(chip), run_time=0.5)
                self.wait(max(0.1, secs - 1.2))
                group.add(t, pill, chip)
            elif kind == "page" and pages:
                img = pages[i % len(pages)].copy()
                img.set_height(FH * 0.62)
                img.shift(UP * FH * 0.04)
                cap = Text(s["text"], font=SCRIPT, color=PAL["accent"], font_size=self.fs(74)).to_edge(DOWN, buff=FH * 0.1)
                self.play(FadeIn(img, shift=UP * unit(90)), run_time=0.6)
                self.play(FadeIn(cap), img.animate.scale(1.07), run_time=max(0.5, secs - 0.6))
                group.add(img, cap)
            else:
                head = Text(s["text"].upper(), font=BODY, weight="BOLD", color=PAL["accent"], font_size=self.fs(40)).to_edge(UP, buff=FH * 0.2).to_edge(LEFT, buff=unit(90))
                self.play(FadeIn(head), run_time=0.4)
                rows = VGroup()
                for b in s.get("bullets", [])[:4]:
                    dot = Circle(radius=unit(30), fill_opacity=1, stroke_width=0, color=PAL["accent"])
                    txt = Text(wrap(b, 56, 0.62), font=HEAD, weight="BOLD", color=PAL["ink"], font_size=self.fs(56))
                    txt.next_to(dot, RIGHT, buff=unit(34))
                    rows.add(VGroup(dot, txt))
                rows.arrange(DOWN, aligned_edge=LEFT, buff=unit(46)).next_to(head, DOWN, buff=unit(50)).align_to(head, LEFT)
                self.play(LaggedStart(*[FadeIn(r, shift=RIGHT * unit(40)) for r in rows], lag_ratio=0.5), run_time=max(1.0, secs - 0.6))
                self.wait(0.2)
                group.add(head, rows)
            self.play(FadeOut(group), run_time=0.25)
