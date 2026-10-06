"""Motion graphics: short MP4 pins / listing videos. An LLM (or the offline planner) writes a scene plan; a Pillow
frame renderer + ffmpeg turns it into video. Needs ffmpeg (system) or the optional `imageio-ffmpeg` package."""
from __future__ import annotations

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


ENGINES: dict[str, MotionEngine] = {e.name: e for e in (PillowEngine(), RemotionEngine(), ManimEngine())}


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
