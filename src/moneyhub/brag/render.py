"""Frame renderer for /brag: every frame is a pure function of time. Pillow compositing + ffmpeg encode with the soundtrack."""
from __future__ import annotations

import math
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..render import graphics as g
from .plan import BragPlan, Scene
from .tones import Tone

FORMATS = {"landscape": (1920, 1080), "vertical": (1080, 1920), "square": (1080, 1080)}
TRANSITION_SECONDS = {"cut": 0.0, "fade": 0.35, "dip": 0.5, "slide": 0.45, "zoom": 0.42, "wipe": 0.5, "flash": 0.2}
ENTRANCE = 0.55           # seconds a headline takes to settle
READ_PER_WORD = 0.3       # seconds each word must stay readable once settled


def ease_out(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def ease_back(t: float) -> float:
    t = min(1.0, max(0.0, t))
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def words(s: str) -> int:
    return len(re.findall(r"\w+", s))


@dataclass
class Timing:
    start: float
    end: float
    td: float            # transition-in length
    settle: float        # time (absolute) when everything is on screen and readable


@dataclass
class Timeline:
    items: list[Timing]
    total: float


def min_seconds(sc: Scene, tone: Tone, voice_len: float = 0.0) -> float:
    n = words(sc.headline) + words(sc.subline)
    read = ENTRANCE + READ_PER_WORD * n + tone.hold
    if sc.visual == "checklist":      # bullets tick on one by one (0.5 s apart); the last one must stay readable
        last = 0.5 + 0.5 * (len(sc.bullets) - 1) + 0.4 + READ_PER_WORD * (words(sc.bullets[-1]) if sc.bullets else 0)
        read = max(read, last + tone.hold)
    if sc.visual == "stat":
        read = max(read, 2.2)
    return max(read + TRANSITION_SECONDS.get(sc.transition, 0.3) * 0.5, voice_len + 0.35, 1.2)


def build_timeline(plan: BragPlan, tone: Tone, bpm: int, target: float, voice_lens: list[float] | None = None) -> Timeline:
    """Scene lengths: honour reading time and voice, snap boundaries to half-beats, stay near the target length."""
    half = 60.0 / bpm / 2
    voice_lens = voice_lens or [0.0] * len(plan.scenes)
    mins = [min_seconds(s, tone, v) for s, v in zip(plan.scenes, voice_lens)]
    durs = [max(s.seconds, m) for s, m in zip(plan.scenes, mins)]
    items, t = [], 0.0
    for i, (sc, d, m) in enumerate(zip(plan.scenes, durs, mins)):
        end = round((t + d) / half) * half
        while end - t < m - 1e-6:
            end += half
        td = TRANSITION_SECONDS.get(sc.transition, 0.3) if i > 0 else 0.0
        settle = t + td + ENTRANCE + READ_PER_WORD * (words(sc.headline) + words(sc.subline))
        items.append(Timing(t, end, td, min(settle, end)))
        t = end
    return Timeline(items, t)


# ----------------------------------------------------------------------------- text layers
class TextLayer:
    def __init__(self, text: str, font: ImageFont.FreeTypeFont, fill, max_w: int, caps: bool = False, align: str = "center", gap: float = 1.12):
        if caps:
            text = text.upper()
        self.text = text
        probe = ImageDraw.Draw(Image.new("RGB", (4, 4)))
        self.lines = g.wrap(probe, text, font, max_w)
        lh = int(font.size * gap)
        w = max((int(probe.textlength(ln, font=font)) for ln in self.lines), default=10) + 8
        self.img = Image.new("RGBA", (w, lh * len(self.lines) + int(font.size * 0.3)), (0, 0, 0, 0))
        d = ImageDraw.Draw(self.img)
        for i, ln in enumerate(self.lines):
            lw = d.textlength(ln, font=font)
            x = (w - lw) / 2 if align == "center" else 0
            d.text((x, i * lh), ln, font=font, fill=fill)
        self.alpha = self.img.split()[3]
        self.size = self.img.size

    def with_alpha(self, a: float) -> Image.Image:
        if a >= 0.999:
            return self.img
        out = self.img.copy()
        out.putalpha(self.alpha.point(lambda v: int(v * max(0.0, a))))
        return out

    def scaled(self, k: float, a: float = 1.0) -> Image.Image:
        im = self.with_alpha(a)
        if abs(k - 1) < 0.01:
            return im
        return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.BILINEAR)

    def typed(self, n_chars: int, caret: bool) -> Image.Image:
        """Same layer showing only the first n characters (typewriter)."""
        out = self.img.copy()
        probe = ImageDraw.Draw(out)
        font_h = self.size[1] // max(1, len(self.lines))
        shown = 0
        mask = Image.new("L", out.size, 0)
        md = ImageDraw.Draw(mask)
        for i, ln in enumerate(self.lines):
            take = max(0, min(len(ln), n_chars - shown))
            if take:
                lw_full = probe.textlength(ln, font=ImageFont.load_default())
                frac = take / len(ln)
                md.rectangle((0, i * font_h, int(self.size[0] * (frac if take < len(ln) else 1.0) + 2), (i + 1) * font_h), fill=255)
            shown += len(ln) + 1
        out.putalpha(Image.composite(self.alpha, Image.new("L", out.size, 0), mask))
        return out


# ----------------------------------------------------------------------------- renderer
@dataclass
class Event:
    t: float
    kind: str


class BragRenderer:
    def __init__(self, plan: BragPlan, pages: list[Image.Image], brush: g.Brush, tone: Tone, size: tuple[int, int], timeline: Timeline,
                 wall: Image.Image | None = None, captions: list[str] | None = None):
        self.plan, self.pages, self.b, self.tone = plan, pages, brush, tone
        self.W, self.H = size
        self.u = min(self.W, self.H) / 1000
        self.portrait = self.H > self.W
        self.tl = timeline
        self.wall = wall
        self.captions = captions or [""] * len(plan.scenes)
        self.events: list[Event] = []
        self._text: dict = {}
        self._bg: dict = {}
        self._pageimg: dict = {}
        self._last: dict = {}
        self._build_events()

    # ---- helpers
    def fonts(self, kind: str, size: float) -> ImageFont.FreeTypeFont:
        s = int(size * self.u)
        return {"h": self.b.heading, "b": self.b.body, "s": self.b.script}[kind](s)

    def text(self, key, text, kind, size, fill, max_w_frac=0.82, caps=None, align="center") -> TextLayer:
        k = (key, text, kind, size, fill, max_w_frac, caps)
        if k not in self._text:
            self._text[k] = TextLayer(text, self.fonts(kind, size), fill, int(self.W * max_w_frac), self.tone.caps if caps is None else caps, align)
        return self._text[k]

    def bg(self, kind: str) -> Image.Image:
        if kind in self._bg:
            return self._bg[kind].copy()
        b, W, H = self.b, self.W, self.H
        if kind == "accent":
            im = Image.new("RGBA", (W, H), b.accent + (255,))
            ImageDraw.Draw(im).ellipse((-W * .25, H * .62, W * .72, H * 1.35), fill=b.accent2 + (255,))
        elif kind == "dark":
            im = Image.new("RGBA", (W, H), tuple(int(c * .55) for c in b.ink) + (255,))
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(glow).ellipse((W * .55, -H * .2, W * 1.2, H * .55), fill=b.accent + (90,))
            im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(int(120 * self.u))))
        elif kind == "paper":
            im = Image.new("RGBA", (W, H), b.bg + (255,))
            ImageDraw.Draw(im).ellipse((W * .62, -H * .25, W * 1.3, H * .5), fill=b.soft + (255,))
        else:
            im = g._bg((W, H), b)
        self._bg[kind] = im
        return im.copy()

    def style_for(self, i: int, sc: Scene) -> tuple[str, tuple, tuple]:
        """(background kind, text colour, accent colour for chips/ticks)."""
        b, t = self.b, self.tone.key
        last = i == len(self.plan.scenes) - 1
        if t == "cinematic":
            return "dark", b.bg, b.accent2
        if t == "chaotic":
            kind = ["accent", "dark", "soft", "accent"][i % 4]
        elif t == "yc-parody":
            kind = "dark" if last else "paper"
        elif t in ("polished", "deadpan"):
            kind = "soft" if last else "paper"
        else:
            kind = "accent" if last or sc.kind == "punchline" else "soft"
        if kind in ("accent",):
            return kind, b.accent_ink, b.bg
        if kind == "dark":
            return kind, b.bg, b.accent2
        return kind, b.ink, b.accent

    def page_layers(self, idx: int, height: int) -> tuple[Image.Image, int]:
        k = (idx, height)
        if k not in self._pageimg:
            pg = g.rounded_page(g.fit_height(self.pages[min(idx, len(self.pages) - 1)], height), int(14 * self.u), (225, 225, 225))
            pad = int(60 * self.u)
            sh = Image.new("RGBA", (pg.width + pad * 2, pg.height + pad * 2), (0, 0, 0, 0))
            a = pg.split()[3].point(lambda v: 90 if v > 10 else 0)
            sh.paste((0, 0, 0, 255), (pad, pad), a)
            sh = sh.filter(ImageFilter.GaussianBlur(int(24 * self.u)))
            sh.alpha_composite(pg, (pad, pad))
            self._pageimg[k] = (sh, pad)
        return self._pageimg[k]

    def put_page(self, canvas: Image.Image, idx: int, cx: float, cy: float, height: float, angle: float = 0, scale: float = 1.0, alpha: float = 1.0) -> None:
        layer, pad = self.page_layers(idx, int(height))
        if scale != 1.0:
            layer = layer.resize((int(layer.width * scale), int(layer.height * scale)), Image.BILINEAR)
        if angle:
            layer = layer.rotate(angle, expand=True, resample=Image.BILINEAR)
        if alpha < 1:
            layer = layer.copy()
            layer.putalpha(layer.split()[3].point(lambda v: int(v * alpha)))
        canvas.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))

    def paste_center(self, canvas, layer: Image.Image, cx, cy):
        canvas.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))

    def headline(self, canvas, i, sc: Scene, lt: float, cx, cy, fill, size=96, max_w=0.82, delay=0.0):
        t = self.tone.anim
        layer = self.text(("h", i), sc.headline, "h", size, fill, max_w)
        p = (lt - delay) / ENTRANCE
        if p <= 0 and t != "type":
            return cy + layer.size[1] / 2
        if t == "pop":
            k = 0.55 + 0.45 * ease_back(p)
            self.paste_center(canvas, layer.scaled(k, min(1, p * 3)), cx, cy)
        elif t == "slide":
            e = ease_out(p)
            self.paste_center(canvas, layer.with_alpha(e), cx - (1 - e) * 140 * self.u, cy)
        elif t == "fade":
            self.paste_center(canvas, layer.with_alpha(ease_out(p)), cx, cy)
        elif t == "type":
            n = int(max(0.0, lt - delay) * 26)
            caret = int(lt * 2) % 2 == 0
            self.paste_center(canvas, layer.typed(n, caret), cx, cy)
        else:  # rise
            e = ease_out(p)
            self.paste_center(canvas, layer.with_alpha(e), cx, cy + (1 - e) * 46 * self.u)
        return cy + layer.size[1] / 2

    def subline(self, canvas, i, sc: Scene, lt: float, cx, y, fill, delay=0.35, max_w=0.74):
        if not sc.subline:
            return y
        layer = self.text(("s", i), sc.subline, "b", 40, fill, max_w, caps=False)
        p = ease_out((lt - delay) / 0.5)
        self.paste_center(canvas, layer.with_alpha(p), cx, y + layer.size[1] / 2 + (1 - p) * 20 * self.u)
        return y + layer.size[1]

    # ---- scenes
    def render_scene(self, i: int, lt: float) -> Image.Image:
        sc = self.plan.scenes[i]
        kind, fg, acc = self.style_for(i, sc)
        W, H, u = self.W, self.H, self.u
        im = self.bg(kind)
        d = ImageDraw.Draw(im)
        safe_top, safe_bot = H * (0.12 if self.portrait else 0.08), H * (0.78 if self.portrait else 0.92)
        mid = (safe_top + safe_bot) / 2
        v = sc.visual
        dur = self.tl.items[i].end - self.tl.items[i].start
        if v in ("text", "typing") or (v in ("page", "pages", "mockup") and not self.pages):
            big = 120 if sc.kind == "hook" or self.tone.key == "chaotic" else 100
            y = self.headline(im, i, sc, lt, W / 2, mid - (30 * u if sc.subline else 0), fg, big)
            self.subline(im, i, sc, lt, W / 2, y + 14 * u, fg)
            if sc.kind in ("outro", "punchline"):
                self.chip(im, "INSTANT DOWNLOAD", W / 2, min(safe_bot, y + (120 if sc.subline else 60) * u), fg, acc, lt, 0.9)
        elif v in ("page", "pages"):
            self.page_scene(im, i, sc, lt, dur, fg, acc, mid, safe_top, safe_bot)
        elif v == "mockup" and self.wall is not None:
            z = 1.0 + 0.06 * (lt / max(dur, 1e-3))
            wall = self.wall.resize((int(W * z), int(H * z)), Image.BILINEAR)
            im.alpha_composite(wall.convert("RGBA"), (-(wall.width - W) // 2, -(wall.height - H) // 2))
            self.headline(im, i, sc, lt, W / 2, safe_bot - 40 * u, self.b.ink, 70, 0.7, delay=0.2)
        elif v == "stat":
            n = sc.stat_value
            k = ease_out(lt / min(1.6, dur * 0.6))
            val = int(round(n * k))
            layer = self.text(("n", i, val), str(val), "h", 330 if not self.portrait else 380, acc, 0.9, caps=False)
            self.paste_center(im, layer.img, W / 2, mid - 40 * u)
            lab = self.text(("l", i), sc.stat_label or sc.headline, "h", 70, fg, 0.8)
            self.paste_center(im, lab.with_alpha(ease_out((lt - 0.4) / 0.4)), W / 2, mid + 190 * u)
        elif v == "checklist":
            self.checklist(im, i, sc, lt, fg, acc, safe_top, safe_bot)
        return im

    def chip(self, canvas, label, cx, cy, fg, acc, lt, delay):
        p = ease_back((lt - delay) / 0.4)
        if p <= 0:
            return
        f = self.fonts("b", 34)
        probe = ImageDraw.Draw(Image.new("RGB", (4, 4)))
        w = int(probe.textlength(label, font=f)) + int(90 * self.u)
        h = int(78 * self.u)
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle((0, 0, w - 1, h - 1), h // 2, fill=self.b.bg + (255,) if fg == self.b.accent_ink else self.b.accent + (255,))
        d.text((w / 2, h / 2), label, font=f, fill=self.b.accent if fg == self.b.accent_ink else self.b.accent_ink, anchor="mm")
        if p != 1:
            layer = layer.resize((max(1, int(w * p)), max(1, int(h * p))), Image.BILINEAR)
        self.paste_center(canvas, layer, cx, cy)

    def page_scene(self, im, i, sc, lt, dur, fg, acc, mid, safe_top, safe_bot):
        W, H, u = self.W, self.H, self.u
        zoom = 1.0 + 0.07 * (lt / max(dur, 1e-3))
        if sc.visual == "pages" and len(self.pages) > 1:
            n = min(3, len(self.pages))
            ph = (safe_bot - safe_top) * (0.78 if self.portrait else 0.8)
            for k in range(n):
                p = ease_out((lt - 0.12 * k) / 0.6)
                off = (k - (n - 1) / 2) * (W * (0.3 if not self.portrait else 0.24))
                cx = W / 2 + off + (1 - p) * W * 0.25
                cy = mid + (abs(k - (n - 1) / 2)) * 26 * u
                self.put_page(im, (sc.page_index + k) % len(self.pages), cx, cy, ph * (0.92 if k != 1 else 1.0), angle=(k - (n - 1) / 2) * -4, scale=zoom, alpha=p)
            y = safe_bot - 6 * u
            self.headline(im, i, sc, lt, W / 2, y, fg, 64, 0.8, delay=0.3)
            return
        ph = (safe_bot - safe_top) * (0.74 if self.portrait else 0.84)
        slide = (1 - ease_out(lt / 0.7))
        if self.portrait or self.W <= self.H * 1.2:
            self.put_page(im, sc.page_index, W / 2, mid - 20 * u + slide * H * 0.1, ph * 0.78, angle=-3, scale=zoom, alpha=ease_out(lt / 0.4))
            y = self.headline(im, i, sc, lt, W / 2, safe_bot - (60 if sc.subline else 20) * u, fg, 74, 0.82, delay=0.35)
            self.subline(im, i, sc, lt, W / 2, y + 6 * u, fg, 0.7)
        else:
            self.put_page(im, sc.page_index, W * 0.73 + slide * W * 0.1, mid, ph, angle=3, scale=zoom, alpha=ease_out(lt / 0.4))
            lx = W * 0.27
            y = self.headline(im, i, sc, lt, lx, mid - 40 * u, fg, 92, 0.42, delay=0.2)
            self.subline(im, i, sc, lt, lx, y + 20 * u, fg, 0.6, max_w=0.40)

    def checklist(self, im, i, sc, lt, fg, acc, safe_top, safe_bot):
        W, H, u = self.W, self.H, self.u
        head = self.text(("c", i), sc.headline.upper(), "b", 44, acc, 0.8, caps=False)
        items = [self.text(("b", i, k), b, "h", 62, fg, 0.7, caps=False, align="left") for k, b in enumerate(sc.bullets[:4])]
        block = sum(lay.size[1] + 46 * u for lay in items)
        y = max(safe_top + 150 * u, (safe_top + safe_bot) / 2 - block / 2 + 30 * u)
        self.paste_center(im, head.with_alpha(ease_out(lt / 0.4)), W / 2, y - 70 * u)
        x0 = W * (0.14 if not self.portrait else 0.1)
        for k, b in enumerate(sc.bullets[:4]):
            st = 0.5 + 0.5 * k
            p = ease_out((lt - st) / 0.4)
            layer = self.text(("b", i, k), b, "h", 62, fg, 0.7, caps=False, align="left")
            r = int(34 * u * min(1, ease_back((lt - st) / 0.35)))
            cy = y + layer.size[1] / 2
            if r > 2:
                ImageDraw.Draw(im).ellipse((x0 - r, cy - r, x0 + r, cy + r), fill=acc + (255,))
                if p > 0.55:
                    ImageDraw.Draw(im).line((x0 - 14 * u, cy, x0 - 4 * u, cy + 10 * u, x0 + 15 * u, cy - 11 * u), fill=self.b.accent_ink if acc == self.b.accent else self.b.ink, width=max(3, int(7 * u)))
            if p > 0:
                im.alpha_composite(layer.with_alpha(p), (int(x0 + 60 * u + (1 - p) * 40 * u), int(y)))
            y += layer.size[1] + 46 * u

    # ---- transitions + frame
    def last_frame(self, i: int) -> Image.Image:
        if i not in self._last:
            dur = self.tl.items[i].end - self.tl.items[i].start
            self._last[i] = self.render_scene(i, dur)
        return self._last[i]

    def blend(self, prev: Image.Image, cur: Image.Image, kind: str, p: float) -> Image.Image:
        p = min(1.0, max(0.0, p))
        W, H = self.W, self.H
        if kind == "cut" or p >= 1:
            return cur
        if kind == "fade":
            return Image.blend(prev, cur, ease_out(p))
        if kind == "dip":
            base = Image.new("RGBA", (W, H), self.b.bg + (255,))
            return Image.blend(prev, base, p * 2) if p < .5 else Image.blend(base, cur, (p - .5) * 2)
        if kind == "flash":
            white = Image.new("RGBA", (W, H), (255, 255, 255, 255))
            return Image.blend(prev, white, p * 2) if p < .5 else Image.blend(white, cur, (p - .5) * 2)
        if kind == "slide":
            e = ease_out(p)
            out = prev.copy()
            out.alpha_composite(cur, (int((1 - e) * W), 0))
            return out
        if kind == "zoom":
            e = ease_out(p)
            z = 1 + 0.22 * e
            big = prev.resize((int(W * z), int(H * z)), Image.BILINEAR)
            big = big.crop(((big.width - W) // 2, (big.height - H) // 2, (big.width - W) // 2 + W, (big.height - H) // 2 + H))
            return Image.blend(big, cur, e)
        if kind == "wipe":
            e = ease_out(p)
            mask = Image.new("L", (W, H), 0)
            ImageDraw.Draw(mask).polygon([(0, 0), (int((e * 1.3) * W), 0), (int((e * 1.3 - 0.3) * W), H), (0, H)], fill=255)
            out = prev.copy()
            out.paste(cur, (0, 0), mask)
            return out
        return cur

    def scene_at(self, t: float) -> int:
        for i, it in enumerate(self.tl.items):
            if t < it.end:
                return i
        return len(self.tl.items) - 1

    def frame(self, t: float) -> Image.Image:
        i = self.scene_at(t)
        it = self.tl.items[i]
        lt = t - it.start
        cur = self.render_scene(i, lt)
        if i > 0 and lt < it.td:
            cur = self.blend(self.last_frame(i - 1), cur, self.plan.scenes[i].transition, lt / it.td)
        cap = self.captions[i]
        if cap and lt > 0.15:
            cur = self.with_caption(cur, cap)
        return cur

    def with_caption(self, im: Image.Image, text: str) -> Image.Image:
        im = im.copy()
        W, H, u = self.W, self.H, self.u
        layer = self.text(("cap", text), text, "b", 40, (255, 255, 255), 0.78, caps=False)
        pad = int(22 * u)
        box = Image.new("RGBA", (layer.size[0] + pad * 2, layer.size[1] + pad), (0, 0, 0, 150))
        mask = Image.new("L", box.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, box.size[0] - 1, box.size[1] - 1), int(18 * u), fill=255)
        box.putalpha(mask.point(lambda v: int(v * 150 / 255)))
        cy = H * (0.72 if self.portrait else 0.86)
        im.alpha_composite(box, (int(W / 2 - box.width / 2), int(cy - box.height / 2)))
        im.alpha_composite(layer.img, (int(W / 2 - layer.size[0] / 2), int(cy - layer.size[1] / 2 - pad * 0.1)))
        return im

    # ---- sound events
    def _build_events(self) -> None:
        ev = self.events
        for i, (sc, it) in enumerate(zip(self.plan.scenes, self.tl.items)):
            tr = sc.transition
            if i > 0:
                ev.append(Event(it.start, {"flash": "flash", "cut": "tick"}.get(tr, "whoosh")))
            if self.tone.anim == "pop":
                ev.append(Event(it.start + it.td + 0.05, "pop"))
            elif self.tone.anim == "type":
                for k in range(min(14, len(sc.headline) // 2)):
                    ev.append(Event(it.start + it.td + k * 0.08, "type"))
            if sc.kind == "reveal":
                ev.append(Event(it.start + it.td + 0.15, "chime"))
            if sc.visual == "checklist":
                for k in range(len(sc.bullets[:4])):
                    ev.append(Event(it.start + 0.5 + 0.5 * k + 0.12, "tick"))
            if sc.visual == "stat":
                for k in range(5):
                    ev.append(Event(it.start + 0.15 + k * 0.28, "tick"))
            if sc.visual == "pages":
                for k in range(3):
                    ev.append(Event(it.start + 0.12 * k + 0.1, "pop"))
            if sc.kind in ("outro", "punchline"):
                ev.append(Event(max(0.0, it.start - 1.1), "riser"))
                ev.append(Event(it.start + it.td, "impact"))
        ev.sort(key=lambda e: e.t)

    # ---- poster
    def poster_time(self) -> float:
        for sc, it in zip(self.plan.scenes, self.tl.items):
            if sc.kind == "reveal":
                return min(it.end - 0.05, max(it.settle, it.start + it.td + ENTRANCE + 0.5))
        it = self.tl.items[min(1, len(self.tl.items) - 1)]
        return min(it.end - 0.05, it.settle)


def srt(captions: list[str], tl: Timeline) -> str:
    def ts(t: float) -> str:
        h, rem = divmod(t, 3600)
        m, s = divmod(rem, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"
    out, n = [], 1
    for cap, it in zip(captions, tl.items):
        if cap:
            out.append(f"{n}\n{ts(it.start + 0.15)} --> {ts(it.end - 0.1)}\n{cap}\n")
            n += 1
    return "\n".join(out)


def encode(renderer: BragRenderer, out: Path, audio: Path | None, ffmpeg: str, fps: int = 30, poster: Image.Image | None = None,
           progress=None) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    W, H = renderer.W, renderer.H
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-"]
    if audio:
        cmd += ["-i", str(audio)]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-preset", "veryfast", "-movflags", "+faststart"]
    if audio:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd.append(str(out))
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    n = int(round(renderer.tl.total * fps))
    try:
        for f in range(n):
            if f == 0 and poster is not None:
                im = poster          # frame 0 IS the poster so every platform's thumbnail shows it (same length, audio stays in sync)
            else:
                im = renderer.frame(f / fps)
            proc.stdin.write(im.convert("RGB").tobytes())
            if progress and f % (fps * 2) == 0:
                progress(f"rendering {f / n:.0%}")
        proc.stdin.close()
        err = proc.stderr.read().decode()
        if proc.wait() != 0:
            raise RuntimeError(f"ffmpeg failed: {err[-400:]}")
    except BrokenPipeError as e:
        raise RuntimeError(f"ffmpeg closed early: {proc.stderr.read().decode()[-400:]}") from e
    return out
