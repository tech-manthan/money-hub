"""Motion graphics: short MP4 pins / listing videos. An LLM (or the offline planner) writes a scene plan; a Pillow
frame renderer + ffmpeg turns it into video. Needs ffmpeg (system) or the optional `imageio-ffmpeg` package."""
from __future__ import annotations

import json
import logging
import math
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw
from pydantic import BaseModel, Field

from . import graphics as g

log = logging.getLogger("moneyhub.motion")
Kind = Literal["title", "page", "bullets", "cta"]


class Scene(BaseModel):
    kind: Kind
    text: str = Field(default="", description="Headline/caption for the scene, <= 9 words")
    bullets: list[str] = Field(default_factory=list, description="For 'bullets' scenes: 3-4 items, <= 6 words each")
    seconds: float = Field(default=2.0, ge=1.0, le=5.0)


class MotionPlan(BaseModel):
    scenes: list[Scene] = Field(min_length=3, max_length=7)


def builtin_plan(title: str, subtitle: str, features: list[str], headline: str) -> MotionPlan:
    short = [f.split(" - ")[0][:42] for f in features[:4]]
    return MotionPlan(scenes=[
        Scene(kind="title", text=headline or title, seconds=2.2),
        Scene(kind="page", text="See inside", seconds=2.0),
        Scene(kind="bullets", text="What you get", bullets=short, seconds=3.0),
        Scene(kind="page", text="Print it or use it on screen", seconds=1.8),
        Scene(kind="cta", text=title, seconds=2.2),
    ])


def fit_duration(plan: MotionPlan, max_total: float = 14.0) -> MotionPlan:
    """Scale scene lengths so the whole video is at most max_total seconds (Etsy clips listing videos at 15 s)."""
    total = sum(sc.seconds for sc in plan.scenes)
    if total <= max_total:
        return plan
    k = max_total / total
    return MotionPlan(scenes=[sc.model_copy(update={"seconds": max(1.0, round(sc.seconds * k, 2))}) for sc in plan.scenes])


def video_duration(path: Path) -> float | None:
    """Duration in seconds (parsed from ffmpeg's banner), or None."""
    import re

    exe = ffmpeg_exe()
    if not exe:
        return None
    r = subprocess.run([exe, "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else None


def llm_plan(router, title: str, subtitle: str, features: list[str], audience: str, providers=None) -> MotionPlan | None:
    prompt = (
        f"Plan a 10-second silent social video for a digital product.\nProduct: {title} ({subtitle})\nAudience: {audience}\n"
        "Features:\n- " + "\n- ".join(features) + "\n\nScenes available: title (hook headline), page (shows a product page with a short caption), "
        "bullets (3-4 short benefit lines), cta (closing card). Start with a title scene that hooks the audience's problem, "
        "end with a cta. Total 8-12 seconds. Be truthful; no income or guarantee claims."
    )
    return router.complete_json("motion", "You write concise scene plans for short product videos.", prompt, MotionPlan, providers=providers)


def ffmpeg_exe() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return None


def available() -> bool:
    """True when at least one motion engine can render."""
    return any(e.available() for e in ENGINES.values())


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


class _TextLayer:
    """Pre-rendered multi-line text that can fade/slide in."""

    def __init__(self, text, font, fill, max_w, anchor="c", gap=1.12):
        probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        lines = g.wrap(probe, text, font, max_w)
        lh = int(font.size * gap)
        self.img = Image.new("RGBA", (max_w, lh * len(lines) + 12), (0, 0, 0, 0))
        d = ImageDraw.Draw(self.img)
        for i, ln in enumerate(lines):
            w = d.textlength(ln, font=font)
            d.text(((max_w - w) / 2 if anchor == "c" else 0, i * lh), ln, font=font, fill=fill)
        self.alpha = self.img.split()[3]

    def paste(self, canvas: Image.Image, x: int, y: int, progress: float, slide: int = 40) -> None:
        p = _ease(progress)
        if p <= 0:
            return
        layer = self.img.copy()
        layer.putalpha(self.alpha.point(lambda v: int(v * p)))
        canvas.alpha_composite(layer, (x, int(y + (1 - p) * slide)))


class _Renderer:
    def __init__(self, plan: MotionPlan, pages: list[Image.Image], brush: g.Brush, size: tuple[int, int], title: str):
        self.plan, self.pages, self.brush, self.size, self.title = plan, pages, brush, size, title
        self.W, self.H = size
        self.u = min(self.W, self.H) / 1000  # unit scale so text sizes work for any aspect ratio
        self.portrait = self.H >= self.W
        self._prep: dict[int, dict] = {}

    def _bg(self, kind: str) -> Image.Image:
        b = self.brush
        if kind == "cta":
            img = Image.new("RGBA", self.size, b.accent + (255,))
            ImageDraw.Draw(img).ellipse((-self.W * 0.3, self.H * 0.6, self.W * 0.7, self.H * 1.3), fill=b.accent2 + (255,))
            return img
        return g._bg(self.size, b)

    def prepare(self, i: int, s: Scene) -> dict:
        b, u, W, H = self.brush, self.u, self.W, self.H
        pre: dict = {"bg": self._bg(s.kind)}
        ink = b.accent_ink if s.kind == "cta" else b.ink
        if s.kind in ("title", "cta"):
            size = int((96 if s.kind == "title" else 84) * u)
            pre["text"] = _TextLayer(s.text, b.heading(size), ink, int(W * 0.82))
            pre["chip"] = _TextLayer("INSTANT DOWNLOAD", b.body(int(30 * u)), b.accent_ink if s.kind == "title" else b.accent, int(W * 0.5))
        if s.kind == "page":
            pg = self.pages[i % len(self.pages)]
            h = int(H * (0.62 if self.portrait else 0.74))
            pre["page"] = g.fit_height(pg, h)
            pre["cap"] = _TextLayer(s.text, b.script(int(70 * u)), b.accent, int(W * 0.8))
        if s.kind == "bullets":
            pre["head"] = _TextLayer(s.text.upper(), b.body(int(40 * u)), b.accent, int(W * 0.8))
            pre["items"] = [_TextLayer(t, b.heading(int(56 * u)), b.ink, int(W * 0.7), anchor="l") for t in s.bullets[:4]]
        return pre

    def frame(self, i: int, s: Scene, t: float) -> Image.Image:
        pre = self._prep.setdefault(i, self.prepare(i, s))
        W, H, u, b = self.W, self.H, self.u, self.brush
        img = pre["bg"].copy()
        d = ImageDraw.Draw(img)
        if s.kind in ("title", "cta"):
            pre["text"].paste(img, int(W * 0.09), int(H * 0.30), t / 0.7)
            pw = pre["chip"].img.width
            if t > 0.6:
                p = _ease((t - 0.6) / 0.5)
                cw = int(520 * u)
                x, y = (W - cw) // 2, int(H * 0.30) + pre["text"].img.height + int(70 * u)
                col = b.accent if s.kind == "title" else b.bg
                d.rounded_rectangle((x, y, x + cw, y + int(74 * u * p)), int(37 * u), fill=col)
                if p > 0.8:
                    d.text((W // 2, y + int(37 * u)), "INSTANT DOWNLOAD", font=b.body(int(30 * u)),
                           fill=b.accent_ink if s.kind == "title" else b.accent, anchor="mm")
        elif s.kind == "page":
            zoom = 1.0 + 0.07 * (t / s.seconds)
            pg = pre["page"]
            w, h = int(pg.width * zoom), int(pg.height * zoom)
            z = pg.resize((w, h), Image.BILINEAR)
            slide = (1 - _ease(t / 0.6)) * H * 0.12
            g.paste_with_shadow(img, z, ((W - w) // 2, int(H * (0.08 if self.portrait else 0.1) + slide)), blur=int(26 * u), offset=(8, 16))
            pre["cap"].paste(img, int(W * 0.1), int(H * (0.78 if self.portrait else 0.86)), (t - 0.3) / 0.5, 24)
        else:  # bullets
            pre["head"].paste(img, int(W * 0.1), int(H * 0.2), t / 0.4)
            y = int(H * 0.3)
            for k, item in enumerate(pre["items"]):
                st = 0.4 + k * 0.45
                p = _ease((t - st) / 0.4)
                if p > 0:
                    r = int(30 * u * p)
                    cx, cy = int(W * 0.12), y + int(34 * u)
                    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=b.accent)
                    if p > 0.6:
                        d.line((cx - 12 * u, cy, cx - 3 * u, cy + 9 * u, cx + 13 * u, cy - 10 * u), fill=b.accent_ink, width=max(3, int(6 * u)))
                item.paste(img, int(W * 0.18), y, (t - st) / 0.4, 30)
                y += item.img.height + int(46 * u)
        return img


def _render_pillow(plan: MotionPlan, pages: list[Image.Image], brush: g.Brush, out: Path, size=(1000, 1500),
                   title: str = "", fps: int = 24) -> Path | None:
    exe = ffmpeg_exe()
    if not exe or not pages:
        log.warning("video skipped: ffmpeg not available")
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    r = _Renderer(plan, pages, brush, size, title)
    cmd = [exe, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}", "-r", str(fps),
           "-i", "-", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "veryfast", "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    fade = 0.25
    prev_last: Image.Image | None = None
    try:
        for i, s in enumerate(plan.scenes):
            n = int(s.seconds * fps)
            for f in range(n):
                t = f / fps
                img = r.frame(i, s, t)
                if i > 0 and t < fade and prev_last is not None:  # cross-fade from previous scene
                    img = Image.blend(prev_last, img, _ease(t / fade))
                proc.stdin.write(img.convert("RGB").tobytes())
            prev_last = r.frame(i, s, s.seconds)
        proc.stdin.close()
        err = proc.stderr.read().decode()
        if proc.wait() != 0:
            log.warning("ffmpeg failed: %s", err[-300:])
            return None
    except BrokenPipeError:
        log.warning("ffmpeg closed early: %s", proc.stderr.read().decode()[-300:])
        return None
    return out


# ----------------------------------------------------------------------------- engines
ENGINES_DIR = Path(__file__).resolve().parents[3] / "engines"


class MotionEngine:
    name = "base"
    note = ""

    def available(self) -> bool:
        raise NotImplementedError

    def render(self, plan, pages, brush, out, size, title, fps) -> Path | None:
        raise NotImplementedError


class PillowEngine(MotionEngine):
    name = "pillow"
    note = "built in (Pillow frames + ffmpeg)"

    def available(self) -> bool:
        return ffmpeg_exe() is not None

    def render(self, plan, pages, brush, out, size, title, fps):
        return _render_pillow(plan, pages, brush, out, size, title, fps)


def _engine_assets(plan: MotionPlan, pages, brush: g.Brush, size, title, fps, workdir: Path) -> dict:
    """Write page images + fonts to workdir and return the JSON props shared by the Remotion and Manim engines."""
    import shutil as sh

    from ..design import font_file
    from ..paths import FONT_DIR

    workdir.mkdir(parents=True, exist_ok=True)
    names = []
    for i, im in enumerate(pages[:6]):
        n = f"page-{i}.png"
        im.convert("RGB").save(workdir / n)
        names.append(n)
    st = brush.style
    f = st.fonts
    font_files, font_paths = [], []
    for family, weights in ((f.heading, f.heading_weights), (f.body, f.body_weights), (f.script, (400, 700))):
        for w in weights:
            fn = font_file(family, w)
            src = FONT_DIR / fn
            if src.exists() and not any(x["file"] == fn for x in font_files):
                sh.copy(src, workdir / fn)
                font_files.append({"family": family, "weight": w, "file": fn})
                font_paths.append(str(workdir / fn))
    p = st.palette
    return {
        "width": size[0], "height": size[1], "fps": fps, "title": title,
        "scenes": [s.model_dump() for s in plan.scenes], "pages": names,
        "palette": {"paper": p.paper, "ink": p.ink, "muted": p.muted, "line": p.line, "accent": p.accent,
                    "accentInk": p.accent_ink, "soft": p.soft, "accent2": p.accent2},
        "fonts": {"heading": f.heading, "body": f.body, "script": f.script},
        "fontFiles": font_files, "fontPaths": font_paths,
    }


class RemotionEngine(MotionEngine):
    """Remotion (React video). Free for individuals and companies of up to 3 people; larger for-profit companies need a
    Remotion company licence. Setup: `moneyhub engines install remotion` (needs Node 18+)."""
    name = "remotion"
    note = "React-based; needs Node + `moneyhub engines install remotion`; see Remotion licence terms"

    @property
    def project(self) -> Path:
        from ..config import get_config
        return Path(get_config().get("render.remotion_dir") or ENGINES_DIR / "remotion")

    def browser(self) -> str | None:
        """Explicit chrome-headless-shell path (config `render.remotion_browser` or MONEYHUB_REMOTION_BROWSER), else a
        Playwright-managed headless shell if present, else None so Remotion downloads its own on first render."""
        import glob
        import os

        from ..config import get_config
        explicit = os.environ.get("MONEYHUB_REMOTION_BROWSER") or get_config().get("render.remotion_browser")
        if explicit:
            return explicit
        found = sorted(glob.glob(os.path.join(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", ""), "chromium_headless_shell-*", "chrome-linux*", "headless_shell")))
        return found[-1] if found else None

    def available(self) -> bool:
        return bool(shutil.which("node")) and (self.project / "node_modules" / ".bin" / "remotion").exists()

    def render(self, plan, pages, brush, out, size, title, fps):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            work = Path(td) / "public"
            props = _engine_assets(plan, pages, brush, size, title, fps, work)
            pj = Path(td) / "props.json"
            pj.write_text(json.dumps(props))
            out.parent.mkdir(parents=True, exist_ok=True)
            cmd = [str(self.project / "node_modules" / ".bin" / "remotion"), "render", "src/index.ts", "MoneyVideo", str(out),
                   f"--props={pj}", f"--public-dir={work}", "--log=error", "--concurrency=2", "--codec=h264"]
            browser = self.browser()
            if browser:
                cmd.append(f"--browser-executable={browser}")
            r = subprocess.run(cmd, cwd=self.project, capture_output=True, text=True, timeout=900)
            if r.returncode != 0 or not out.exists():
                log.warning("remotion failed: %s", (r.stderr or r.stdout)[-400:])
                return None
        return out


class ManimEngine(MotionEngine):
    """Manim Community Edition (MIT). Install: `pip install manim` (needs Cairo/Pango; on macOS `brew install pango cairo`)."""
    name = "manim"
    note = "needs `pip install manim` (+ Cairo/Pango)"

    def command(self) -> str | None:
        import os

        from ..config import get_config
        return os.environ.get("MONEYHUB_MANIM_COMMAND") or get_config().get("render.manim_command") or shutil.which("manim")

    def available(self) -> bool:
        return self.command() is not None

    def render(self, plan, pages, brush, out, size, title, fps):
        import json
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            work = Path(td) / "assets"
            props = _engine_assets(plan, pages, brush, size, title, fps, work)
            props["pages"] = [str(work / n) for n in props["pages"]]
            pj = Path(td) / "plan.json"
            pj.write_text(json.dumps(props))
            media = Path(td) / "media"
            cmd = [self.command(), "render", "-qh", "--format", "mp4", "-r", f"{size[0]},{size[1]}", "--fps", str(fps),
                   "--media_dir", str(media), "-o", "moneyhub.mp4", "--disable_caching", str(ENGINES_DIR / "manim" / "scene.py"), "MoneyScene"]
            env = dict(os.environ, MONEYHUB_PLAN=str(pj))
            r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=1200)
            produced = sorted(media.rglob("moneyhub.mp4"))
            if r.returncode != 0 or not produced:
                log.warning("manim failed: %s", (r.stderr or r.stdout)[-400:])
                return None
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(produced[-1], out)
        return out


class HyperFramesEngine(MotionEngine):
    """HyperFrames (HeyGen, Apache-2.0): an HTML + GSAP composition rendered to MP4 by headless Chrome and ffmpeg.
    Setup: `moneyhub engines install hyperframes` (needs Node 22+). Anonymous telemetry is switched off for every render."""
    name = "hyperframes"
    note = "HTML/GSAP-based; needs Node 22+ and `moneyhub engines install hyperframes`"

    @property
    def project(self) -> Path:
        from ..config import get_config
        return Path(get_config().get("render.hyperframes_dir") or ENGINES_DIR / "hyperframes")

    def _node_ok(self) -> bool:
        node = shutil.which("node")
        if not node:
            return False
        try:
            major = int(subprocess.run([node, "-v"], capture_output=True, text=True, timeout=10).stdout.strip().lstrip("v").split(".")[0])
        except (ValueError, subprocess.SubprocessError):
            return False
        return major >= 22

    def available(self) -> bool:
        return self._node_ok() and (self.project / "node_modules" / ".bin" / "hyperframes").exists() \
            and (self.project / "node_modules" / "gsap" / "dist" / "gsap.min.js").exists()

    @staticmethod
    def composition(plan: MotionPlan, props: dict) -> str:
        """The index.html for a plan: one absolutely-positioned scene per plan scene, animated by a paused GSAP timeline."""
        import html as h
        import json

        W, H = props["width"], props["height"]
        p, f = props["palette"], props["fonts"]
        total = round(sum(sc.seconds for sc in plan.scenes), 2)
        faces = "\n".join(f"@font-face{{font-family:'{ff['family']}';font-weight:{ff['weight']};src:url('{ff['file']}')}}" for ff in props["fontFiles"])
        big, mid = round(W * 0.085), round(W * 0.045)
        pages, scenes, js, t = props["pages"], [], [], 0.0
        for i, sc in enumerate(plan.scenes):
            d = round(sc.seconds, 2)
            bg = {"title": p["accent"], "cta": p["accent"], "page": p["soft"], "bullets": p["paper"]}[sc.kind]
            fg = p["accentInk"] if sc.kind in ("title", "cta") else p["ink"]
            inner = ""
            if sc.kind in ("title", "cta"):
                inner = f"<div class='t' id='t{i}'>{h.escape(sc.text)}</div>" + ("<div class='chip' id='c%d'>Instant download</div>" % i if sc.kind == "cta" else "")
            elif sc.kind == "page":
                img = pages[i % len(pages)] if pages else ""
                inner = f"<img class='pg' id='p{i}' src='{img}'><div class='cap' id='t{i}'>{h.escape(sc.text)}</div>"
            else:
                inner = f"<div class='hd' id='t{i}'>{h.escape(sc.text)}</div><ul>" + "".join(
                    f"<li id='b{i}_{k}'>{h.escape(b)}</li>" for k, b in enumerate(sc.bullets)) + "</ul>"
            scenes.append(f"<section class='clip sc' id='s{i}' data-start='{t}' data-duration='{d}' data-track-index='{i}' style='background:{bg};color:{fg}'>{inner}</section>")
            js.append(f"tl.fromTo('#s{i}',{{opacity:0}},{{opacity:1,duration:.35}},{t});")
            if sc.kind in ("title", "cta"):
                js.append(f"tl.fromTo('#t{i}',{{y:60,opacity:0}},{{y:0,opacity:1,duration:.7,ease:'power3.out'}},{t + .1});")
                if sc.kind == "cta":
                    js.append(f"tl.fromTo('#c{i}',{{scale:.6,opacity:0}},{{scale:1,opacity:1,duration:.5,ease:'back.out(2)'}},{t + .6});")
            elif sc.kind == "page":
                js.append(f"tl.fromTo('#p{i}',{{y:120,rotation:-4,opacity:0}},{{y:0,rotation:2,opacity:1,duration:.8,ease:'power3.out'}},{t + .1});")
                js.append(f"tl.to('#p{i}',{{scale:1.06,duration:{max(d - 1, .5)},ease:'none'}},{t + .9});")
                js.append(f"tl.fromTo('#t{i}',{{opacity:0}},{{opacity:1,duration:.5}},{t + .5});")
            else:
                js.append(f"tl.fromTo('#t{i}',{{x:-60,opacity:0}},{{x:0,opacity:1,duration:.5,ease:'power2.out'}},{t + .1});")
                for k in range(len(sc.bullets)):
                    js.append(f"tl.fromTo('#b{i}_{k}',{{x:-40,opacity:0}},{{x:0,opacity:1,duration:.45,ease:'power2.out'}},{t + .5 + k * .35});")
            t = round(t + d, 2)
        return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width={W}, height={H}">
<script src="gsap.min.js"></script>
<style>{faces}
*{{margin:0;padding:0;box-sizing:border-box}}html,body{{width:{W}px;height:{H}px;overflow:hidden;background:{p['paper']}}}
#root{{position:relative;width:{W}px;height:{H}px;font-family:'{f['body']}',sans-serif}}
.sc{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:{round(H*.03)}px;padding:{round(W*.08)}px;text-align:center}}
.t{{font-family:'{f['heading']}',serif;font-weight:700;font-size:{big}px;line-height:1.1}}
.hd{{font-family:'{f['heading']}',serif;font-weight:700;font-size:{round(big*.8)}px}}
ul{{list-style:none;display:flex;flex-direction:column;gap:{round(H*.025)}px;font-size:{mid}px;font-weight:600}}
li::before{{content:"";display:inline-block;width:.55em;height:.55em;border-radius:50%;background:{p['accent2']};margin-right:.5em}}
.pg{{max-height:{round(H*.68)}px;max-width:{round(W*.72)}px;border:2px solid {p['line']};border-radius:10px;box-shadow:0 18px 50px rgba(0,0,0,.18);background:#fff}}
.cap{{font-family:'{f['script']}',cursive;font-size:{round(big*.7)}px;color:{p['accent']}}}
.chip{{background:{p['paper']};color:{p['accent']};border-radius:999px;padding:.35em 1.1em;font-weight:700;font-size:{mid}px}}
</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}">
{chr(10).join(scenes)}
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
window.__timelines["main"] = tl;
tl.seek(0);
</script></body></html>"""

    def render(self, plan, pages, brush, out, size, title, fps):
        import json
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            work = Path(td) / "proj"
            props = _engine_assets(plan, pages, brush, size, title, fps, work)
            shutil.copy(self.project / "node_modules" / "gsap" / "dist" / "gsap.min.js", work / "gsap.min.js")
            (work / "hyperframes.json").write_text(json.dumps({"paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}}))
            (work / "index.html").write_text(self.composition(plan, props), encoding="utf-8")
            out.parent.mkdir(parents=True, exist_ok=True)
            env = {**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1", "HYPERFRAMES_SKIP_SKILLS": "1"}
            cmd = [str(self.project / "node_modules" / ".bin" / "hyperframes"), "render", str(work), "-o", str(out), "-f", str(fps), "--quiet"]
            r = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=900, env=env)
            if r.returncode != 0 or not out.exists():
                log.warning("hyperframes failed: %s", (r.stderr or r.stdout)[-400:])
                return None
        return out


class FilmCraftEngine(MotionEngine):
    """Slideshow video assembled in the third-party filmcraft video editor: each scene is a still (its finished layout), placed on a
    timeline with cross-dissolves and exported as H.264. No per-scene animation (the Pillow engine animates text and zooms).
    Off unless the craft master switch and the filmcraft switch are on (Settings or `moneyhub tools --enable filmcraft`)."""
    name = "filmcraft"
    note = "stills + dissolves edited in the filmcraft tool; needs the craft switches and `scripts/install_craft_tools.sh`"
    TICKS = 254016000000   # filmcraft time units per second
    DISSOLVE_FRAMES = 6

    def available(self) -> bool:
        from .. import crafttools
        return crafttools.is_enabled("filmcraft") and crafttools.find_tool("filmcraft") is not None

    def render(self, plan, pages, brush, out, size, title, fps):
        import tempfile

        from .. import crafttools
        out.parent.mkdir(parents=True, exist_ok=True)
        w, h = size[0] // 2 * 2, size[1] // 2 * 2
        r = _Renderer(plan, pages, brush, (w, h), title)
        timeout = float(crafttools._cfg("timeout", 90)) * 4
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            stills = []
            for i, s in enumerate(plan.scenes):
                f = work / f"scene-{i + 1:02d}.png"
                r.frame(i, s, s.seconds if s.kind == "page" else max(s.seconds, 2.4)).convert("RGB").save(f)
                stills.append(f)
            lines = [{"id": "file.newProject", "params": {"name": "moneyhub"}},
                     {"id": "file.import", "params": {"paths": [str(f) for f in stills]}},
                     {"id": "file.newSequence", "params": {"name": "main", "width": w, "height": h, "fps": fps, "video": 1, "audio": 1}}]
            frame = 0
            plan_frames = []
            for s in plan.scenes:
                n = max(1, int(round(s.seconds * fps)))
                plan_frames.append((frame, n))
                frame += n
            for i, (start, n) in enumerate(plan_frames):
                lines.append({"id": "timeline.place", "params": {"item": i + 1, "track": "V1", "frame": start,
                                                                  "duration": n * self.TICKS // fps, "audio": False}})
            script = work / "build.jsonl"
            script.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
            proj = work / "p.fcproj"
            res = crafttools.run("filmcraft", ["--compact", "--save-as", str(proj), "run", str(script)], timeout)
            rows = [json.loads(x) for x in res.out.splitlines() if x.startswith("{")]
            if not res.ok or len(rows) != len(lines) or not all(x.get("ok") for x in rows):
                log.warning("filmcraft could not build the timeline: %s", (res.err or res.out)[-300:])
                return None
            items = rows[1]["result"].get("items", [])
            clips = [x["result"]["clips"][0] for x in rows[3:]]
            if items != list(range(1, len(stills) + 1)) or len(clips) != len(stills):   # the placements above assume ids 1..n in scene order
                log.warning("filmcraft imported %d of %d scenes", len(items), len(stills))
                return None
            # the imports come back in path order, which is scene order; dissolve into every scene after the first
            fades = [{"id": "sequence.applyVideoTransition", "params": {"clip": c, "effect": "cross_dissolve", "frames": self.DISSOLVE_FRAMES, "edge": "in"}}
                     for c in clips[1:]]
            script2 = work / "fades.jsonl"
            script2.write_text("\n".join(json.dumps(x) for x in fades) + "\n", encoding="utf-8")
            res = crafttools.run("filmcraft", ["--compact", "--project", str(proj), "--save", "run", str(script2)], timeout)
            if not res.ok:   # no dissolves is still a valid slideshow
                log.info("filmcraft dissolves skipped: %s", (res.err or res.out)[-200:])
            tmp = out.with_suffix(".filmcraft.mp4")
            res = crafttools.run("filmcraft", ["--compact", "--project", str(proj), "export", str(tmp), "--format", "h264", "--no-audio"], timeout)
            want = sum(n for _, n in plan_frames) / fps
            got = video_duration(tmp) if tmp.exists() else None
            if not res.ok or got is None or abs(got - want) > 0.5:
                tmp.unlink(missing_ok=True)
                log.warning("filmcraft export failed or has the wrong length (%s vs %.1fs): %s", got, want, (res.err or res.out)[-200:])
                return None
            tmp.replace(out)
        return out


ENGINES: dict[str, MotionEngine] = {e.name: e for e in (PillowEngine(), RemotionEngine(), ManimEngine(), HyperFramesEngine(), FilmCraftEngine())}


def engine_status() -> list[dict]:
    from ..config import get_config
    chain = get_config().get("render.motion") or ["pillow"]
    return [{"name": n, "available": e.available(), "enabled": n in chain, "note": e.note} for n, e in ENGINES.items()]


def render_video(plan: MotionPlan, pages: list[Image.Image], brush: g.Brush, out: Path, size=(1000, 1500),
                 title: str = "", fps: int = 24, engines: list[str] | None = None) -> Path | None:
    """Render with the first working engine of the chain (config `render.motion`, default [pillow])."""
    from ..config import get_config

    if not pages:
        return None
    for name in engines or get_config().get("render.motion") or ["pillow"]:
        e = ENGINES.get(name)
        if not e or not e.available():
            log.info("motion engine %s unavailable", name)
            continue
        try:
            res = e.render(plan, pages, brush, out, size, title, fps)
        except Exception as ex:  # noqa: BLE001 - fall through to the next engine
            log.warning("motion engine %s failed: %s", name, ex)
            continue
        if res:
            return res
    return None
