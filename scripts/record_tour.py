"""Record the product tour videos shown on the landing and docs pages.

Drives the real web app (headless Chromium) through all four steps, with a visible cursor and captions, against a
throwaway offline instance (built-in content, temp output folder), so it never touches your real catalogue or AI accounts.

    python scripts/record_tour.py          # writes src/moneyhub/web/static/media/{tour,idea,look,make,publish}.mp4 + samples

Needs: the project venv, `playwright install chromium`, and ffmpeg.
"""
from __future__ import annotations

import os
import shutil
import wave
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import numpy as np
import yaml
from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
MEDIA = ROOT / "src" / "moneyhub" / "web" / "static" / "media"
PORT = 8799
BASE = f"http://127.0.0.1:{PORT}"
SIZE = {"width": 1280, "height": 720}

OVERLAY = """
(() => {
  const mk = () => {
    if (document.getElementById('__cap')) return;
    const c = document.createElement('div'); c.id = '__cap';
    c.style.cssText = 'position:fixed;left:50%;bottom:26px;transform:translateX(-50%);max-width:900px;padding:12px 22px;border-radius:12px;background:rgba(15,20,18,.86);color:#fff;font:600 22px/1.35 system-ui,sans-serif;text-align:center;z-index:99999;transition:opacity .25s;opacity:0;pointer-events:none';
    const d = document.createElement('div'); d.id = '__cur';
    d.style.cssText = 'position:fixed;left:-40px;top:-40px;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;background:rgba(255,200,40,.85);border:2px solid #fff;box-shadow:0 0 0 3px rgba(0,0,0,.25);z-index:100000;pointer-events:none;transition:transform .08s';
    document.documentElement.append(c, d);
    window.__cap = t => { c.textContent = t; c.style.opacity = t ? 1 : 0; };
    addEventListener('mousemove', e => { d.style.left = e.clientX + 'px'; d.style.top = e.clientY + 'px'; }, true);
    addEventListener('mousedown', () => d.style.transform = 'scale(.7)', true);
    addEventListener('mouseup', () => d.style.transform = '', true);
  };
  if (document.readyState === 'loading') addEventListener('DOMContentLoaded', mk); else mk();
})();
"""


def run(cmd: list[str], **kw):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)


def start_server(tmp: Path) -> subprocess.Popen:
    """Offline instance: built-in content only, output in a temp folder."""
    shutil.copy(ROOT / "moneyhub.yaml", tmp / "moneyhub.yaml")
    local = {"output_dir": str(tmp / "out"), "llm": {"tasks": {t: ["builtin"] for t in ("content", "listing", "research", "motion")}}}
    (tmp / "moneyhub.local.yaml").write_text(yaml.safe_dump(local))
    env = {**os.environ, "MONEYHUB_HOME": str(tmp), "MONEYHUB_OUT": str(tmp / "out")}
    proc = subprocess.Popen([sys.executable, "-c", "from moneyhub.cli import app; app()", "ui", "--port", str(PORT)],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    for _ in range(60):
        try:
            urllib.request.urlopen(BASE + "/", timeout=2)
            return proc
        except Exception:  # noqa: BLE001
            if proc.poll() is not None:
                raise SystemExit(f"server exited: {proc.stderr.read().decode()[-500:]}")
            time.sleep(0.5)
    proc.kill()
    raise SystemExit("server did not start")


SR = 44100

# What is said aloud. The on-screen captions stay short; the voice sounds like a person showing a friend.
SPOKEN = {
    "MoneyHub makes printable products you can sell.": "Hi! This is MoneyHub. It helps you make printable products you can sell, even if you have never done it before. Let me show you how it works.",
    "Press Start making.": "Let's begin. Just press Start making.",
    "Step 1: pick who you want to help.": "Step one. Think about who you would like to help. Every product starts with a group of people.",
    "Each card is a group of people. We suggest a product that suits them.": "Each card is a group of people with something in common, like nurses. Under each one, we have picked a product that suits them.",
    "You can change what to make. Planners and checklists are easy to start with.": "If you would like something different, you can change what we make for them. Planners and checklists are easy places to begin.",
    "Not sure? Surprise me picks for you.": "Not sure at all? That is fine. Press Surprise me, and we will pick something for you.",
    "Or describe any group of people yourself.": "Or, if you have your own idea, just type who it is for. Dog trainers, for example.",
    "We'll go with Nurse. Next, the look.": "I will stick with nurses. Now, on to the look.",
    "Step 2: how should it look?": "Step two. How should it look?",
    "\"Choose for me\" matches colours and fonts to your audience. It's the recommended choice.": "If design is not your thing, leave it on Choose for me. We match the colours and fonts to your audience, so you can hardly go wrong.",
    "Or pick yourself. Choose a colour set…": "Or pick it yourself. Start with a colour set.",
    "…and a font style.": "Then a font style. Watch the example page change as you choose.",
    "More detail lets you change titles, corners and lines. All optional.": "There is more detail if you want it, like the title style and the corners. But it is all optional.",
    "Step 3: check your choices.": "Step three. Here is a quick summary of what we are about to make.",
    "Pick how the pages are arranged. Each picture is a real page.": "Planners come in different layouts, because people like different things. Each picture here is a real page from your product.",
    "Not enough? Generate a new layout.": "And if none of these is quite right, press Generate another layout, and we will invent a new one for you. You can even describe the layout you want in words.",
    "Everything here also works in the terminal. This is the same request.": "And if you ever prefer a terminal, here is the very same request, written as a command.",
    "Press Make my product.": "Happy with it? Press Make my product.",
    "It's being made. This usually takes 20 seconds to 3 minutes.": "Now we wait a little. It usually takes a few minutes at most, and you can watch each step happen.",
    "Done! Your product is ready.": "And it is done! Your product is ready.",
    "What to do next is listed right here.": "Right here, it tells you exactly what to do next.",
    "Step 4: check it before you sell it.": "Last step. Before you sell anything, take a good look at it.",
    "Look through every preview page.": "Scroll through the preview pages, and make sure you like what you see.",
    "Quality checks show anything to fix. Green ticks are good.": "The quality checks flag anything that needs fixing. Green ticks mean you are good to go.",
    "Happy with it? Press Approve.": "If you are happy with it, press Approve.",
    "Download the upload package: your files, ready to upload.": "Then download the upload package. It has everything you need, ready to upload.",
    "Then follow the upload guide for your shop. It tells you what goes where.": "Finally, follow the guide for your shop. It tells you which file goes where, and gives you the title and description to copy. And that is it. You have just made a product.",
    "Optional: second-opinion tools.": "One optional extra. In Settings, there are second opinion tools.",
    "They open your finished files and tell you if anything cannot be read. All off until you switch them on.": "They open your finished files, and tell you if anything cannot be read. They are all off, until you switch them on.",
    "Switch them on, and choose which ones to use.": "Switch them on, then choose which ones you want to use. For example, one for PDFs, one for spreadsheets, and one to even out the sound.",
    "Save. A tool that is missing or fails is skipped, so a product never breaks.": "Press save. If a tool is missing, or fails, it is simply skipped, so your products never break.",
}



class Tour:
    def __init__(self, page: Page, voice=None, audio_dir: Path | None = None):
        self.page, self.t0, self.marks = page, time.time(), {}
        self.voice, self.audio_dir, self.events = voice, audio_dir, []   # events: (seconds into recording, wav path)

    def cap(self, text: str, hold: float = 2.0):
        """Show a caption and speak it; the caption stays up until the narration has finished."""
        spoken = 0.0
        if text and self.voice:
            wav = self.audio_dir / f"line-{len(self.events):03d}.wav"
            spoken = self.voice.synth(SPOKEN.get(text, text).replace("…", "."), wav, shutil.which("ffmpeg"))
            self.events.append((time.time() - self.t0, wav))
        self.page.evaluate("t => window.__cap && window.__cap(t)", text)
        self.page.wait_for_timeout(int(max(hold, spoken + 0.5) * 1000))

    def move(self, target, steps: int = 28):
        box, prev = target.bounding_box(), None
        for _ in range(40):  # wait out smooth scrolling so the cursor lands on the element
            if box == prev:
                break
            prev = box
            self.page.wait_for_timeout(120)
            box = target.bounding_box()
        self.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + min(box["height"] / 2, 40), steps=steps)
        self.page.wait_for_timeout(350)

    def click(self, selector: str, hold: float = 0.8):
        loc = self.page.locator(selector).first
        loc.evaluate("e => e.scrollIntoView({block: 'center', behavior: 'instant'})")   # centred, so the sticky header never covers it
        self.move(loc)
        self.page.mouse.down(); self.page.mouse.up()
        self.page.wait_for_timeout(int(hold * 1000))

    def hover(self, selector: str, hold: float = 0.6):
        loc = self.page.locator(selector).first
        loc.evaluate("e => e.scrollIntoView({block: 'center', behavior: 'instant'})")
        self.move(loc)
        self.page.wait_for_timeout(int(hold * 1000))

    def mark(self, name: str):
        self.marks[name] = time.time() - self.t0

    def scroll(self, dy: int, pause: float = 1.0):
        self.page.mouse.wheel(0, dy)
        self.page.wait_for_timeout(int(pause * 1000))


def tour(page: Page, voice=None, audio_dir: Path | None = None) -> Tour:
    t = Tour(page, voice, audio_dir)
    t.mark("idea0")
    # ---- landing + step 1
    page.goto(BASE + "/"); page.wait_for_timeout(800)
    t.cap("MoneyHub makes printable products you can sell.", 2.6)
    t.cap("Press Start making.", 1.0)
    t.click('a.btn.big:has-text("Start making")', 1.0)
    t.cap("Step 1: pick who you want to help.", 2.2)
    t.hover('.idea:has-text("Teacher")', 0.7); t.hover('.idea:has-text("Fitness")', 0.7)
    t.click('.idea:has-text("Nurse")', 0.6)
    t.cap("Each card is a group of people. We suggest a product that suits them.", 3.0)
    t.hover('#types .type:has-text("Habit tracker")', 0.4)
    t.cap("You can change what to make. Planners and checklists are easy to start with.", 3.0)
    t.click("#surprise", 1.2)
    t.cap("Not sure? Surprise me picks for you.", 2.4)
    t.click("#custom-toggle", 0.6)
    page.keyboard.type("dog trainers", delay=90)
    t.cap("Or describe any group of people yourself.", 2.4)
    page.fill("#custom-niche", "")
    t.click("#custom-toggle", 0.6)
    t.click('.idea:has-text("Nurse")', 0.6)
    t.cap("We'll go with Nurse. Next, the look.", 1.8)
    t.click('.step.on [data-go="2"]', 0.8)
    t.mark("idea1")

    # ---- step 2
    t.mark("look0")
    t.cap("Step 2: how should it look?", 2.0)
    t.click('.opt:has-text("Choose for me")', 0.5)
    t.cap("\"Choose for me\" matches colours and fonts to your audience. It's the recommended choice.", 3.2)
    t.click('.opt:has-text("I\'ll pick")', 0.8)
    t.cap("Or pick yourself. Choose a colour set…", 1.6)
    t.click('.sw:has-text("Plum")', 0.9)
    t.click('.sw:has-text("Ocean")', 0.7)
    t.click('.sw:has-text("Plum")', 0.8)
    t.cap("…and a font style.", 1.4)
    t.click('#fonts .opt:has-text("Classic")', 0.9)
    t.click("details.help summary:has-text('More detail')", 0.8)
    t.cap("More detail lets you change titles, corners and lines. All optional.", 3.0)
    t.click('.step.on [data-go="3"]', 0.8)
    t.mark("look1")

    # ---- step 3
    t.mark("make0")
    t.cap("Step 3: check your choices.", 2.0)
    t.hover("#summary", 1.0)
    page.evaluate("document.querySelectorAll('#layouts img').forEach(i => i.loading = 'eager')")
    page.wait_for_function("[...document.querySelectorAll('#layouts img')].every(i => i.complete && i.naturalWidth > 0)", timeout=90_000)
    t.hover('#layouts .layopt:nth-child(1)', 0.5)
    t.cap("Pick how the pages are arranged. Each picture is a real page.", 3.0)
    t.click('#layouts .layopt:nth-child(3)', 0.6)
    t.click('#gen-layout', 0.5)
    page.evaluate("document.querySelectorAll('#layouts img').forEach(i => i.loading = 'eager')")
    page.wait_for_function("[...document.querySelectorAll('#layouts img')].every(i => i.complete && i.naturalWidth > 0)", timeout=90_000)
    t.cap("Not enough? Generate a new layout.", 3.0)
    t.click("details.help summary:has-text('matching command')", 0.8)
    t.cap("Everything here also works in the terminal. This is the same request.", 3.0)
    t.click("details.help summary:has-text('matching command')", 0.4)
    t.cap("Press Make my product.", 1.2)
    t.click("#make", 0.8)
    t.cap("It's being made. This usually takes 20 seconds to 3 minutes.", 3.0)
    t.mark("wait0")
    page.wait_for_selector("#p-done:not([hidden]), #p-error:not([hidden])", timeout=420_000)
    if page.locator("#p-error:not([hidden])").count():
        raise SystemExit("build failed: " + page.inner_text("#p-errmsg"))
    t.mark("wait1")
    t.cap("Done! Your product is ready.", 2.6)
    t.cap("What to do next is listed right here.", 2.2)
    t.mark("make1")

    # ---- publish
    t.mark("publish0")
    t.click("#p-link", 1.2)
    page.wait_for_load_state("networkidle")
    t.cap("Step 4: check it before you sell it.", 2.2)
    t.scroll(380); t.cap("Look through every preview page.", 2.4)
    t.scroll(500); t.cap("Quality checks show anything to fix. Green ticks are good.", 3.0)
    t.scroll(-900, 0.8)
    t.cap("Happy with it? Press Approve.", 1.6)
    t.click('button:has-text("Approve")', 1.4)
    page.wait_for_load_state("networkidle")
    t.hover('a:has-text("Download upload package")', 0.6)
    t.cap("Download the upload package: your files, ready to upload.", 3.0)
    page.locator("text=Upload guides").first.scroll_into_view_if_needed()
    t.cap("Then follow the upload guide for your shop. It tells you what goes where.", 3.4)
    t.mark("publish1")

    # ---- optional second-opinion tools (Settings). Switched on and saved in the throwaway instance only.
    t.mark("tools0")
    page.goto(BASE + "/settings"); page.wait_for_load_state("networkidle")
    page.locator("#craft-form").scroll_into_view_if_needed()
    t.cap("Optional: second-opinion tools.", 2.6)
    t.hover('#craft-form label:has-text("Use them")', 0.5)
    t.cap("They open your finished files and tell you if anything cannot be read. All off until you switch them on.", 3.6)
    t.click('#craft-form label:has-text("Use them")', 0.6)
    t.click('#craft-form label:has-text("Check every new product")', 0.6)
    t.cap("Switch them on, and choose which ones to use.", 2.4)
    t.click('#craft-form label:has-text("pdfcraft")', 0.5)
    t.click('#craft-form label:has-text("gridcraft")', 0.5)
    t.click('#craft-form label:has-text("soundcraft")', 0.5)
    t.click('#craft-form button[type="submit"]', 1.0)
    t.cap("Save. A tool that is missing or fails is skipped, so a product never breaks.", 3.4)
    t.mark("tools1")
    t.cap("", 0.2)
    return t


def encode(src: Path, dst: Path, start: float = 0.0, end: float | None = None, fast: tuple[float, float] | None = None, factor: int = 6,
           events: list | None = None):
    """Cut [start, end] from the raw recording; the `fast` span (the build wait) is played `factor` times faster."""
    end = end or float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)]))
    cuts = [(start, end, 1)] if not fast else [(start, fast[0], 1), (fast[0], fast[1], factor), (fast[1], end, 1)]
    parts = [f"[0:v]trim=start={a:.2f}:end={b:.2f},setpts=(PTS-STARTPTS)/{f}[v{i}]" for i, (a, b, f) in enumerate(cuts) if b > a]
    chain = "".join(f"[v{i}]" for i in range(len(parts)))
    graph = ";".join(parts) + f";{chain}concat=n={len(parts)}:v=1:a=0,scale=1280:-2,fps=24[out]"
    run(["ffmpeg", "-y", "-i", str(src), "-filter_complex", graph, "-map", "[out]", "-c:v", "libx264", "-preset", "slow", "-crf", "30",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(dst)])
    run(["ffmpeg", "-y", "-ss", "1.5", "-i", str(dst), "-frames:v", "1", "-q:v", "4", str(dst.with_suffix(".jpg"))])
    if events:
        mux_audio(dst, events, cuts, start)


def _mapped(ts: float, cuts: list[tuple[float, float, float]]) -> float:
    """Recording time -> output time, given the (start, end, speed) segments that were kept."""
    acc = 0.0
    for a, b, f in cuts:
        if ts < a:
            return acc
        if ts < b:
            return acc + (ts - a) / f
        acc += (b - a) / f
    return acc


def mux_audio(video: Path, events: list, cuts: list, clip_start: float):
    """Lay the narration lines on a silent timeline matching the cut video, then add it as the audio track."""
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)]))
    mix = np.zeros(int((dur + 1) * SR), dtype=np.float32)
    base = _mapped(clip_start, cuts)
    for ts, wav in events:
        t = _mapped(ts, cuts) - base
        if t < -0.05 or t > dur:
            continue
        with wave.open(str(wav)) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
        i = max(int(t * SR), 0)
        mix[i:i + len(x)] += x[: len(mix) - i]
    peak = float(np.abs(mix).max())
    if peak > 0.85:
        mix *= 0.85 / peak  # leave headroom so overlapping lines never clip
    wav_out = video.with_suffix(".mix.wav")
    with wave.open(str(wav_out), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
    try:   # optional: level the narration with soundcraft when it is switched on in Settings (off by default, never fatal)
        from moneyhub.crafttools import polish_wav
        if polish_wav(wav_out, SR):
            print("  narration levelled with soundcraft")
    except ImportError:
        pass
    tmp = video.with_suffix(".av.mp4")
    run(["ffmpeg", "-y", "-i", str(video), "-i", str(wav_out), "-c:v", "copy", "-c:a", "aac", "-b:a", "96k", "-t", f"{dur:.2f}", "-movflags", "+faststart", str(tmp)])
    tmp.replace(video)
    wav_out.unlink()


def samples(tmp: Path):
    from PIL import Image
    out = MEDIA / "samples"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    imgs = sorted((tmp / "out" / "products").glob("*/images/etsy/*.jpg"))[:3]
    for i, f in enumerate(imgs, 1):
        im = Image.open(f).convert("RGB")
        im.thumbnail((900, 900))
        im.save(out / f"sample-{i}.jpg", quality=80, optimize=True)


def main():
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required (brew install ffmpeg)")
    MEDIA.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="moneyhub-tour-"))
    from moneyhub.brag.voice import SayVoice, pick
    voice = pick()
    if isinstance(voice, SayVoice):
        os.environ.setdefault("MONEYHUB_VOICE", "Samantha")  # the most natural built-in macOS voice; override with MONEYHUB_VOICE
    print("narration:", voice.name if voice else "none (no voice engine found; videos will be silent)")
    server = start_server(tmp)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport=SIZE, record_video_dir=str(tmp / "video"), record_video_size=SIZE)
            ctx.add_init_script(OVERLAY)
            page = ctx.new_page()
            try:
                t = tour(page, voice, tmp)
            except BaseException:
                page.screenshot(path=str(Path(tempfile.gettempdir()) / "tour-failure.png"))
                raise
            ctx.close()
            raw = Path(page.video.path())
            browser.close()
        m = t.marks
        wait = (m["wait0"], m["wait1"])
        encode(raw, MEDIA / "tour.mp4", fast=wait, events=t.events)
        for name in ("idea", "look", "make", "publish", "tools"):
            encode(raw, MEDIA / f"{name}.mp4", m[f"{name}0"], m[f"{name}1"] + 0.3, fast=wait if name == "make" else None, events=t.events)
        samples(tmp)
    finally:
        server.terminate()
        shutil.rmtree(tmp, ignore_errors=True)
    for f in sorted(MEDIA.glob("*.mp4")):
        print(f"{f.name:<14}{f.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
