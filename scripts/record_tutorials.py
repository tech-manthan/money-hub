"""Record one narrated video tutorial per feature (shown on the /tutorials page).

Like record_tour.py it drives the real web app in headless Chromium against a throwaway, offline instance (built-in content, temp
output folder, nothing of yours is touched). It first makes a few real products with the command line, then records each tutorial in
its own browser session. Command-line tutorials replay the real output of real commands in a terminal window.

    python scripts/record_tutorials.py                      # every tutorial (about 30-40 minutes)
    python scripts/record_tutorials.py --only product-page,sell-on
    python scripts/record_tutorials.py --list

Writes src/moneyhub/web/static/media/tutorials/<key>.mp4, <key>.jpg and index.json.
Needs: the project venv, `playwright install chromium`, ffmpeg. The craft tools (deckcraft, gridcraft, wordcraft, pdfcraft) are
used for the last command-line tutorial when they are installed; that tutorial is skipped when they are not.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import record_tour as RT  # noqa: E402  (reuses the cursor overlay, narration timing, cutting and muxing)
from playwright.sync_api import Page, sync_playwright  # noqa: E402

OUT = RT.MEDIA / "tutorials"
BASE = RT.BASE
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
T = RT.Tour


# ------------------------------------------------------------------------------------------------ environment
class Env:
    """The throwaway MoneyHub instance: its own home, output folder and environment variables."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.vars = {**os.environ, "MONEYHUB_HOME": str(tmp), "MONEYHUB_OUT": str(tmp / "out"), "COLUMNS": "104", "NO_COLOR": "1", "TERM": "dumb"}

    def cli(self, args: list[str], timeout: int = 900) -> str:
        """Run `moneyhub <args>` in the throwaway instance and return its text output (colours removed)."""
        r = subprocess.run([sys.executable, "-c", "from moneyhub.cli import app; app()", *args], env=self.vars, capture_output=True, text=True, timeout=timeout)
        text = ANSI.sub("", (r.stdout + r.stderr)).strip()
        for raw in {str(self.tmp), str(self.tmp.resolve())}:     # never show the real temp folder in a video
            text = text.replace(raw, "~/moneyhub-demo")
        return text


def prebuild(env: Env) -> dict[str, int]:
    """Real products for the tutorials to show. Ids follow creation order in an empty catalogue."""
    plan = [("planner", ['make', 'nurse', 'weekly_planner', '--llm', 'builtin', '--sizes', 'letter', '--seed', '3']),
            ("budget", ['make', 'nurse', 'budget_tracker', '--llm', 'builtin', '--sizes', 'letter', '--no-video', '--seed', '4']),
            ("coloring", ['make', 'x', 'kids_coloring', '--llm', 'builtin', '--sizes', 'letter', '--no-video', '--pages', '12', '--seed', '5']),
            ("wallart", ['make', 'teacher', 'wall_art', '--llm', 'builtin', '--sizes', '4x5', '--no-video', '--seed', '6']),
            ("guide", ['make', 'nurse', 'ebook_guide', '--llm', 'builtin', '--sizes', 'letter', '--no-video', '--seed', '7'])]
    ids = {}
    for n, (key, args) in enumerate(plan, 1):
        print(f"  making {key} ...", flush=True)
        env.cli(args)
        ids[key] = n
    return ids


# ------------------------------------------------------------------------------------------------ the terminal window
TERM_HTML = """<!doctype html><meta charset=utf-8><title>Terminal</title>
<body style="margin:0;background:#0b0f17;font-family:system-ui,sans-serif">
<div style="margin:26px auto 0;width:1180px;height:580px;background:#11161f;border-radius:12px;box-shadow:0 18px 60px rgba(0,0,0,.55);overflow:hidden">
<div style="height:34px;background:#1b222e;display:flex;align-items:center;gap:8px;padding:0 14px;color:#8b95a7;font-size:14px">
<span style="width:12px;height:12px;border-radius:50%;background:#ff5f56"></span><span style="width:12px;height:12px;border-radius:50%;background:#ffbd2e"></span><span style="width:12px;height:12px;border-radius:50%;background:#27c93f"></span>
<span style="margin-left:12px">Terminal: moneyhub</span></div>
<pre id=t style="margin:0;padding:16px 22px;height:530px;overflow:hidden;color:#d6deeb;font:17px/1.42 ui-monospace,Menlo,Consolas,monospace;white-space:pre-wrap;word-break:break-word"></pre></div>
<script>window.__add = h => { const t = document.getElementById('t'); t.insertAdjacentHTML('beforeend', h); t.scrollTop = t.scrollHeight; };
window.__clear = () => { document.getElementById('t').innerHTML = ''; };</script>"""


def open_terminal(page: Page, tmp: Path):
    f = tmp / "terminal.html"
    f.write_text(TERM_HTML)
    page.goto(f.as_uri())
    page.wait_for_timeout(500)


def typed(t: T, cmd: str, output: str, head: int = 18, tail: int = 0, pause: float = 1.6, say: str = "", hold: float = 2.5):
    """Type a command, show its output, and speak `say` over it. Shows the first `head` lines (and last `tail`) of its real output."""
    p = t.page
    p.evaluate("window.__cap && window.__cap('')")      # no caption left over from the previous command
    p.evaluate("window.__clear()")
    p.evaluate("h => window.__add(h)", '<span style="color:#7ee787">$ </span>')
    for ch in cmd:
        p.evaluate("c => window.__add(c)", html.escape(ch))
        p.wait_for_timeout(28)
    p.wait_for_timeout(450)
    lines = output.splitlines()
    if len(lines) > head + tail:
        shown = lines[:head] + (["..."] + lines[-tail:] if tail else ["..."])
    else:
        shown = lines
    p.evaluate("h => window.__add(h)", "\n")
    for i in range(0, len(shown), 4):
        p.evaluate("h => window.__add(h)", html.escape("\n".join(shown[i:i + 4])) + "\n")
        p.wait_for_timeout(110)
    if say:
        t.cap(say, hold)        # spoken over the command and its output, which are on screen
    else:
        p.wait_for_timeout(int(pause * 1000))
    p.evaluate("window.__cap && window.__cap('')")


# ------------------------------------------------------------------------------------------------ tutorials
# Each tutorial is (key, title, one-line blurb, function). Captions are written as the narrator speaks: they are shown as subtitles
# and spoken aloud (record_tour.Tour.cap).
def next_step(t: T, n: int):
    t.click(f'.step.on [data-go="{n}"]', 0.7)


def go_make(t: T, audience: str, product: str | None = None):
    t.page.goto(BASE + "/make")
    t.page.wait_for_timeout(700)
    t.click(f'.idea:has-text("{audience}")', 0.5)
    if product:
        t.click(f'#types .type:has-text("{product}")', 0.5)


def tut_audience(t: T, ctx):
    p = t.page
    p.goto(BASE + "/make"); p.wait_for_timeout(800)
    t.cap("Every product starts with a group of people you want to help. These cards are ready-made audiences.", 3.2)
    t.hover('.idea:has-text("Teacher")', 0.5); t.hover('.idea:has-text("Wedding")', 0.5)
    t.click('.idea:has-text("Wedding")', 0.8)
    t.cap("Pick Wedding, and look at what happens to the products below.", 2.4)
    p.locator("#fit-note").scroll_into_view_if_needed(); p.wait_for_timeout(500)
    t.cap("Not every product suits every audience. A couple planning a wedding has no use for classroom charts, so we only show products that fit.", 4.6)
    t.hover("#types .type:has-text('Budget tracker')", 0.6)
    t.cap("Each card says in one sentence what you get.", 2.4)
    t.click("#show-all", 0.8)
    t.cap("If you really want something else, Show all brings every product back.", 3.0)
    t.hover("#types .tag.free", 1.0)
    t.cap("This label means the files are the same for every audience, like clipart or digital paper. The audience only nudges the colours.", 4.4)
    t.click("#show-all", 0.6)
    t.click("#surprise", 1.0)
    t.cap("Surprise me picks an audience and a product that go together.", 2.8)
    t.click("#custom-toggle", 0.6)
    p.keyboard.type("dog trainers", delay=80)
    t.cap("Or describe your own audience. We then show the products that are written for any audience.", 3.6)


def tut_options(t: T, ctx):
    p = t.page
    go_make(t, "Teacher", "Kids coloring book")
    t.cap("Some products have their own options. Pick a kids coloring book for the teacher audience, then press Next.", 3.6)
    next_step(t, 2)
    p.locator("#kids-opts").scroll_into_view_if_needed(); p.wait_for_timeout(500)
    t.cap("Here you choose a picture theme, the line thickness for the age, and how many pages.", 3.4)
    t.click("#theme", 0.4)
    p.select_option("#theme", index=2); t.cap("Animals, ocean, garden, vehicles, dinosaurs or treats.", 2.2)
    p.fill("#pages", "16"); t.cap("Sixteen pages.", 1.2)
    go_make(t, "Teacher", "Classroom printables")
    next_step(t, 2)
    p.locator("#class-opts").scroll_into_view_if_needed(); p.wait_for_timeout(400)
    t.click("#names", 0.4); p.keyboard.type("Ava, Ben, Chloe, Dev", delay=70)
    t.cap("Classroom printables can have your students' names printed on the name tags and desk plates. Leave it empty for blank lines to write in.", 4.8)
    go_make(t, "Mindfulness", "Oracle")
    next_step(t, 2)
    p.locator("#oracle-opts").scroll_into_view_if_needed(); p.wait_for_timeout(400)
    t.cap("An oracle deck lets you choose gentle message cards or a tarot-style deck, and the card size.", 3.6)
    go_make(t, "Teacher", "Learning workbook")
    next_step(t, 2)
    p.locator("#learn-opts").scroll_into_view_if_needed(); p.wait_for_timeout(400)
    t.cap("A learning workbook has a focus, such as colours, numbers, handwriting or sight words, and a language.", 3.6)
    t.cap("Only the options that belong to your product are shown. Everything here also works as a command.", 3.2)


def tut_look(t: T, ctx):
    p = t.page
    go_make(t, "Nurse", "Weekly planner")
    next_step(t, 2)
    t.cap("This is the look. Choose for me matches the colours and fonts to your audience.", 3.2)
    t.click('.opt:has-text("I\'ll pick")', 0.7)
    t.click('.sw:has-text("Ocean")', 0.8); t.click('.sw:has-text("Plum")', 0.8)
    t.cap("Or pick a colour set yourself, and watch the example page change.", 2.8)
    t.click("#use-brand", 0.6)
    p.evaluate("() => { const b = document.getElementById('brand'); b.value = '#c0392b'; b.dispatchEvent(new Event('input', {bubbles: true})); }")
    p.wait_for_timeout(900)
    t.cap("Or use your own brand colour. We build a matching palette that still passes the contrast check.", 3.6)
    t.click('#fonts .opt:has-text("Editorial")', 0.9)
    t.cap("Pick a font pair.", 1.6)
    t.click("details.help summary:has-text('More detail')", 0.8)
    t.cap("More detail changes the title style, corner radius, grid lines and the look number. The look number reproduces a design exactly.", 4.6)
    next_step(t, 3)
    t.cap("Planners also come in different page layouts. Each picture is a real page of your planner.", 3.4)
    p.wait_for_function("[...document.querySelectorAll('#layouts img')].every(i => i.complete && i.naturalWidth > 0)", timeout=90_000)
    t.click('#layouts .layopt:nth-child(2)', 0.7)
    t.click("#gen-layout", 0.5)
    p.wait_for_function("[...document.querySelectorAll('#layouts img')].every(i => i.complete && i.naturalWidth > 0)", timeout=90_000)
    t.cap("Generate another layout invents new ones.", 2.4)
    t.click("#layout-text", 0.5); p.keyboard.type("big priorities on the left and a habit row at the bottom", delay=45)
    t.cap("Or describe the layout you want in your own words.", 2.8)
    t.click("#opt-eink", 0.7)
    t.cap("For a reMarkable, Kindle Scribe or Boox tablet, tick the e-ink box. You get black and white pages with tap-to-jump links.", 4.2)


def tut_decoration(t: T, ctx):
    p = t.page
    go_make(t, "Nurse", "Weekly planner")
    next_step(t, 2)
    p.locator("#decor-opts").scroll_into_view_if_needed(); p.wait_for_timeout(600)
    t.cap("Planners are plain white pages by default, because plain pages print cleanly and save ink. Decoration is optional, and it stays off until you turn it on.", 5.4)

    def pick(sel, value, wait=1800):
        t.click(sel, 0.3)
        p.select_option(sel, value)
        p.wait_for_timeout(wait)
    pick("#decor_corner", "themed")
    t.cap("Corner art adds a faint line drawing in the corner of every page, like a watermark. Themed means pictures that suit your audience. For nurses, a stethoscope, a heart and a pulse line.", 6.4)
    pick("#decor_corner_at", "opposite")
    t.cap("Choose which corner it goes in, or use two opposite corners.", 3.0)
    pick("#decor_header", "themed")
    t.cap("Title-bar pictures put a small row of pictures in the title bar of every page.", 3.4)
    pick("#decor_background", "leaves")
    t.cap("A background adds a pale pattern behind the page. Your writing boxes stay white. It uses more ink, so your listing will say so.", 5.0)
    pick("#decor_strength", "medium")
    t.cap("Strength is light, medium or bold. We keep every strength faint enough to read the text easily.", 4.0)
    pick("#decor_theme", "garden")
    t.cap("Themed pictures follow your audience, but you can pick a different set. Here, a garden set.", 4.0)
    pick("#decor_theme", "")
    t.click("#decor-light", 1.6)
    t.cap("Light touch gives you a gentle corner and title bar in one click.", 3.4)
    t.click("#decor-full", 1.8)
    t.cap("Fully decorated turns on all three layers. No decoration switches everything off again.", 4.0)
    t.click("#decor-none", 1.4)
    t.click("#decor-light", 1.2)
    next_step(t, 3)
    t.cap("Your choices appear in the summary, and in the matching command, so you can repeat them from the terminal.", 4.2)
    p.locator("details.help summary:has-text('matching command')").click(); p.wait_for_timeout(900)
    t.cap("They can also be set as defaults in the settings file.", 3.0)


def tut_product_page(t: T, ctx):
    p = t.page
    pid = ctx["ids"]["planner"]
    p.goto(f"{BASE}/product/{pid}"); p.wait_for_load_state("networkidle")
    t.cap("This is a finished product. At the top you can approve it, reject it, or download the upload package.", 3.8)
    t.hover('button:has-text("Approve")', 0.5)
    p.locator("h2:has-text('Preview')").scroll_into_view_if_needed(); p.wait_for_timeout(700)
    t.cap("Preview shows every page. Click any page to open it large.", 2.8)
    t.scroll(520)
    t.cap("Quality checks run automatically. Green is good, yellow is advice, red means fix it before selling.", 3.8)
    t.hover(".qa li:nth-child(2)", 0.8)
    t.scroll(380)
    t.cap("Files you will sell lists exactly what the buyer receives, and nothing else.", 3.2)
    t.click('a[data-view="files"]', 1.2)
    t.cap("Click a file to look inside it, page by page, before anyone buys it.", 3.0)
    t.click("#v-close", 0.6)
    p.locator("h2:has-text('Listing copy')").scroll_into_view_if_needed(); p.wait_for_timeout(500)
    t.cap("Listing copy is written for you: the title, thirteen tags, the price and the description. The Copy buttons make pasting easy.", 4.2)
    t.click("#c-title + button", 0.6)
    p.locator("h2:has-text('Images by marketplace')").scroll_into_view_if_needed(); p.wait_for_timeout(500)
    t.cap("Photos are made for each marketplace. Etsy shows ten numbered photos in upload order.", 3.4)
    for tab in ("gumroad", "pinterest"):
        if p.locator(f'.tabs button[data-tab="img-{tab}"]').count():
            t.click(f'.tabs button[data-tab="img-{tab}"]', 0.9)
    t.cap("Gumroad gets a cover and thumbnail. Pinterest gets six pins that follow the safe-zone rule.", 3.4)
    p.locator("h2:has-text('Upload guides')").scroll_into_view_if_needed(); p.wait_for_timeout(500)
    t.cap("Each marketplace has a step-by-step upload guide with the exact title, tags and description to paste.", 3.8)
    t.click('.tabs button[data-tab="g-gumroad"]', 0.8)


def tut_sell_on(t: T, ctx):
    p = t.page
    pid = ctx["ids"]["planner"]
    p.goto(f"{BASE}/product/{pid}"); p.wait_for_load_state("networkidle")
    p.locator("#sell-panel").scroll_into_view_if_needed(); p.wait_for_timeout(600)
    t.cap("Sell it on. MoneyHub never uploads for you. It prepares one pack per marketplace, and you upload it yourself.", 4.0)
    t.hover("#sell-platform", 0.5)
    p.wait_for_function("document.querySelector('#sell-body').innerText.length > 20", timeout=30_000)
    t.cap("For Etsy it shows which files go there, and whether they fit Etsy's limits: five files, twenty megabytes each.", 4.0)
    for plat in ("gumroad", "payhip", "kofi"):
        p.select_option("#sell-platform", plat); p.wait_for_timeout(1200)
    t.cap("Gumroad, Payhip and Ko-fi have different limits, so the pack changes for each one.", 3.2)
    p.select_option("#sell-platform", "etsy"); p.wait_for_timeout(900)
    t.hover("#sell-zip", 0.8)
    t.cap("Download pack gives one zip with three folders: the download, the listing photos in order, and the listing text.", 4.2)
    t.cap("Upload the download folder as the buyer's files, then the photos in numbered order, then paste the text. That is all.", 4.0)
    if p.locator("#export-panel").count():
        p.locator("#export-panel").scroll_into_view_if_needed(); p.wait_for_timeout(500)
        t.cap("Some products can also go to Amazon KDP as a paperback, to Notion, or to Canva. Those options appear here.", 3.8)


def tut_exports(t: T, ctx):
    p = t.page
    pid = ctx["ids"]["planner"]
    p.goto(f"{BASE}/product/{pid}"); p.wait_for_load_state("networkidle")
    p.locator("#export-panel").scroll_into_view_if_needed(); p.wait_for_timeout(600)
    t.cap("Sell it somewhere else. This planner can become a Canva template pack, a Notion import, or a printed paperback on Amazon KDP.", 4.4)
    t.click('form.exp[data-kind="canva"] input[name="link"]', 0.4)
    p.keyboard.type("https://www.canva.com/design/your-template-link", delay=25)
    t.cap("For Canva, paste your template link, and the buyer gets a page that opens it.", 3.2)
    t.click('form.exp[data-kind="canva"] button', 0.8)
    p.wait_for_function("document.querySelector('#exp-status').innerText.startsWith('Done')", timeout=240_000)
    t.cap("Done. The files are listed, including one zip with everything.", 2.8)
    t.click('form.exp[data-kind="notion"] button', 0.6)
    p.wait_for_function("document.querySelector('#exp-status').innerText.startsWith('Done')", timeout=240_000)
    t.cap("Notion makes pages and databases that import straight in.", 2.8)
    t.hover('form.exp[data-kind="kdp"] select[name="trim"]', 0.5)
    t.cap("For a paperback on KDP, choose the book size and paper. You get a print-ready interior, a full-wrap cover and a guide.", 4.2)
    t.cap("Check the gutter, paper thickness and bleed numbers on KDP's own pages before you rely on them.", 3.6)
    t.click('form.exp[data-kind="kdp"] button', 0.6)
    t.mark("wait0")
    p.wait_for_function("document.querySelector('#exp-status').innerText.startsWith('Done')", timeout=420_000)
    t.mark("wait1")
    t.cap("Done. Everything is saved in the product folder.", 2.4)


def tut_track(t: T, ctx):
    p = t.page
    pid = ctx["ids"]["planner"]
    p.goto(f"{BASE}/product/{pid}"); p.wait_for_load_state("networkidle")
    p.locator("h2:has-text('Track it')").scroll_into_view_if_needed(); p.wait_for_timeout(500)
    t.cap("Track it is how MoneyHub learns what works for you. Everything stays on your computer.", 3.4)
    t.click('form[action$="/listing"] input[name="url"]', 0.4)
    p.keyboard.type("https://www.etsy.com/listing/123456789/nurse-weekly-planner", delay=22)
    t.cap("After you list it, save where you listed it, with the link and the price.", 3.2)
    t.click('form[action$="/listing"] button', 1.2)
    p.wait_for_load_state("networkidle")
    p.locator("h2:has-text('Track it')").scroll_into_view_if_needed()
    t.click('form[action$="/metric"] input[name="views"]', 0.3); p.fill('form[action$="/metric"] input[name="views"]', "240")
    t.cap("You can also record views, favourites and pin clicks, so you can see what gets attention.", 3.2)
    t.click('form[action$="/metric"] button', 1.2)
    p.wait_for_load_state("networkidle")
    t.cap("Saving takes you to Sales and learning. It shows which audience, product and look is working, based on your own numbers.", 4.2)
    p.goto(f"{BASE}/product/{pid}"); p.wait_for_load_state("networkidle")
    p.locator("h2:has-text('Track it')").scroll_into_view_if_needed(); p.wait_for_timeout(400)
    t.click('form[action$="/sale"] input[name="revenue"]', 0.4); p.keyboard.type("11.99", delay=60)
    t.cap("When something sells, add the sale with the revenue.", 2.8)
    t.click('form[action$="/sale"] button', 1.2)
    p.wait_for_load_state("networkidle")
    t.cap("Your report updates. It also feeds the make-next suggestions on the first page of the wizard.", 3.6)


def tut_ideas(t: T, ctx):
    p = t.page
    p.goto(BASE + "/ideas"); p.wait_for_load_state("networkidle")
    t.cap("Not sure what to make? The Ideas page brainstorms audiences and products for you.", 3.2)
    t.click("#focus", 0.4); p.keyboard.type("pets", delay=90)
    t.cap("Type a focus if you like, and how many ideas you want.", 2.6)
    t.click('#ideas-form button[type="submit"]', 0.6)
    t.mark("wait0")
    p.wait_for_function("document.querySelectorAll('.gen-idea').length > 0", timeout=240_000)
    t.mark("wait1")
    p.wait_for_load_state("networkidle")
    t.cap("Each idea shows the product, why it might work, and the phrases to check by hand.", 3.6)
    t.scroll(250)
    t.cap("These are guesses from general knowledge, not live search data. Type the phrases into Etsy and Pinterest search before you build.", 4.6)
    t.hover(".gen-idea button", 0.6)
    t.cap("Like one? Press Generate this, and it is queued in My products.", 3.0)


def tut_settings(t: T, ctx):
    p = t.page
    p.goto(BASE + "/settings"); p.wait_for_load_state("networkidle")
    t.cap("Settings connects the services MoneyHub can use. None are required: it works offline with the built-in writer.", 4.0)
    t.hover(".keyrow[data-env]", 0.8)
    t.cap("AI writing helpers write better text. Paste a key and press Save, then Test. Keys are stored on this computer only, never in the code.", 4.6)
    p.locator("#art-form").scroll_into_view_if_needed(); p.wait_for_timeout(500)
    t.cap("AI artwork is optional and only for wall art backgrounds. Check each service's terms before you sell what it makes.", 4.0)
    p.locator("#craft-form").scroll_into_view_if_needed(); p.wait_for_timeout(500)
    t.cap("Second-opinion tools open your finished files with other programs and flag anything unreadable. They are all off until you switch them on.", 4.4)
    t.hover('#craft-form label:has-text("Use them")', 0.5)
    t.cap("There are also extra files you can build: editable vector copies, spreadsheet copies, PDF titles and an editable Word copy of the text.", 4.6)
    t.cap("A tool that is missing or fails is skipped, so a product never breaks.", 3.0)


def tut_variations(t: T, ctx):
    p = t.page
    pid = ctx["ids"]["planner"]
    p.goto(f"{BASE}/product/{pid}"); p.wait_for_load_state("networkidle")
    t.cap("Want a different version? Make a new variation keeps the audience and product, and changes the look and the copy.", 4.0)
    t.hover('button:has-text("Make a new variation")', 0.8)
    p.goto(BASE + "/products"); p.wait_for_load_state("networkidle")
    t.cap("My products is your catalogue. Open any product to review it again.", 3.0)
    p.goto(f"{BASE}/product/{pid}"); p.wait_for_load_state("networkidle")
    p.locator('form[action$="/delete"] button').first.scroll_into_view_if_needed(); p.wait_for_timeout(500)
    t.cap("Delete removes a product and its files from this computer. It asks you to confirm first, because it cannot be undone.", 4.0)


def tut_editing(t: T, ctx):
    p = t.page
    pid = ctx["ids"]["wallart"]
    p.goto(f"{BASE}/product/{pid}"); p.wait_for_load_state("networkidle")
    p.locator("#editor").scroll_into_view_if_needed(); p.wait_for_timeout(500)
    t.cap("Want to adjust a pin or a poster by hand? Export editable files makes layered pictures you can open in Penpot or Inkscape.", 4.4)
    t.click('form[action$="/editable"] button', 1.0)
    p.wait_for_load_state("networkidle")
    p.locator("#editor").scroll_into_view_if_needed(); p.wait_for_timeout(700)
    t.cap("Every object is its own named layer, such as background, motif and quote. Edit, export with the same file names, and upload them back.", 4.8)
    t.cap("Fonts are never put in a download. The files tell your buyers which free fonts to install.", 3.4)


def tut_launch_video(t: T, ctx):
    p = t.page
    pid = ctx["ids"]["planner"]
    p.goto(f"{BASE}/product/{pid}#brag"); p.wait_for_load_state("networkidle")
    p.locator("#brag").scroll_into_view_if_needed(); p.wait_for_timeout(500)
    t.cap("The launch video, called brag, makes a short promo with music and motion, plus captions for Pinterest, Reels, TikTok and Shorts.", 4.6)
    t.click('form[action$="/brag"] input[name="tone"]', 0.4); p.keyboard.type("calm and cosy", delay=60)
    t.cap("Choose a tone, a format and a length. You can add a voice-over and burned-in captions.", 3.6)
    t.click('form[action$="/brag"] input[name="captions"]', 0.5)
    t.click('form[action$="/brag"] button', 0.8)
    t.cap("It is built only from this product's real facts. Rendering takes a minute or two.", 3.4)
    t.mark("wait0")
    p.wait_for_timeout(5000)
    p.reload(); p.wait_for_load_state("networkidle")
    for _ in range(40):
        if p.locator("#brag ~ .panel video").count():
            break
        p.wait_for_timeout(5000); p.reload(); p.wait_for_load_state("networkidle")
    t.mark("wait1")
    p.locator("#brag").scroll_into_view_if_needed(); p.wait_for_timeout(600)
    t.cap("Here is the video, with the share text ready to paste.", 3.0)


def tut_cli_basics(t: T, ctx):
    o = ctx["cli"]
    open_terminal(t.page, ctx["tmp"])
    t.cap("Everything in the app also works from the command line. First, see what you can make.", 3.4)
    typed(t, "moneyhub types", o["types"], head=14, say="There are twenty-five product types, and any text works as an audience.", hold=3.0)
    typed(t, "moneyhub styles", o["styles"], head=16, say="Styles lists every look option: palettes, fonts, headers, layouts and more.", hold=3.2)
    typed(t, 'moneyhub make "nurse" habit_tracker --llm builtin', o["make"], head=20, tail=4, say="Make builds the whole product: files, photos, listing text, guides and quality checks.", hold=3.6)
    typed(t, "moneyhub list", o["list"], head=12, say="List shows your catalogue. Use the product number with the other commands.", hold=3.2)
    typed(t, 'moneyhub make "nurse" weekly_planner --palette ocean --fonts clean --weeks 12', o["make_look"], head=16, tail=4, say="Every option you pick in the app is a flag here: palette, fonts, number of weeks and so on.", hold=3.6)


def tut_cli_selling(t: T, ctx):
    o = ctx["cli"]
    open_terminal(t.page, ctx["tmp"])
    t.cap("These commands help you list and learn. Start by checking the listing text for risky words.", 3.6)
    typed(t, "moneyhub risk 1", o["risk"], head=16, say="Risk looks for brand names, trademarks and risky claims, so you can fix them before a marketplace does.", hold=3.8)
    typed(t, "moneyhub export pack 1 etsy", o["pack"], head=14, say="Export pack builds the zip for one marketplace: the download, the photos and the text.", hold=3.4)
    typed(t, "moneyhub approve 1", o["approve"], head=6, say="Record that you approved it, listed it and sold it.", hold=2.8)
    typed(t, "moneyhub listed 1 etsy https://www.etsy.com/listing/123 --price 9.99", o["listed"], head=6)
    typed(t, "moneyhub sale 1 etsy 9.99", o["sale"], head=6)
    typed(t, "moneyhub report", o["report"], head=14)
    typed(t, "moneyhub next", o["next"], head=14, say="Report and next use your own numbers to suggest what to make next.", hold=3.2)
    typed(t, 'moneyhub keywords "planner"', o["keywords"], head=14)
    typed(t, "moneyhub calendar --months 3", o["calendar"], head=14, say="Keywords and calendar give search phrases and seasonal ideas to check by hand. They are guidance, not sales data.", hold=4.2)


def tut_cli_scale(t: T, ctx):
    o = ctx["cli"]
    open_terminal(t.page, ctx["tmp"])
    t.cap("To make many products at once, use make-many. It makes several distinct variations and prints a summary.", 4.0)
    typed(t, 'moneyhub make-many "x" digital_paper --count 3 --no-images', o["many"], head=16, say="A bundle combines products into one zip and one listing, with a fee-aware discounted price.", hold=3.8)
    typed(t, 'moneyhub bundle 1,2 --name "Nurse Starter Kit"', o["bundle"], head=16)
    typed(t, "moneyhub sample 1 --pages 2", o["sample"], head=8, say="Sample makes a free preview PDF for email sign-ups and Pinterest.", hold=3.0)
    typed(t, "moneyhub brag 1 --preview --no-llm", o["brag"], head=14, say="Brag makes the launch video from the command line, with the same tone, format and voice options.", hold=3.6)
    typed(t, "moneyhub edit export 3", o["edit"], head=10)
    typed(t, "moneyhub regenerate 1 --llm builtin", o["regen"], head=10, say="Edit export writes layered files for hand editing. Regenerate makes a fresh variation.", hold=3.4)


def tut_cli_tools(t: T, ctx):
    o = ctx["cli"]
    open_terminal(t.page, ctx["tmp"])
    t.cap("MoneyHub has some optional helper tools. Doctor checks your computer and says how to fix any gap.", 3.8)
    typed(t, "moneyhub doctor", o["doctor"], head=18)
    typed(t, "moneyhub tools", o["tools"], head=16, say="Tools lists the optional programs. Everything is off until you switch it on.", hold=3.2)
    if o.get("craft_sheets"):
        typed(t, "moneyhub export craft 2 --kinds sheets", o["craft_sheets"], head=12)
        t.cap("Export craft builds extra files. Here, CSV and web copies of every sheet of the budget spreadsheet.", 3.8)
    if o.get("craft_docx"):
        typed(t, "moneyhub export craft 5 --kinds docx", o["craft_docx"], head=8)
        t.cap("And an editable Word copy of the text of a guide.", 2.8)
    if o.get("deck"):
        typed(t, 'moneyhub make "x" presentation_template --llm builtin', o["deck"], head=14, tail=3)
        t.cap("Presentation template builds an editable slide deck with twelve slides, a preview and an editing guide.", 4.0)
    typed(t, "moneyhub assets list", o["assets"], head=10)
    typed(t, "moneyhub translations status", o["translations"], head=8, say="Assets manages open-source icon sets with their licences. Translations guards the Spanish, French and German word lists until a person approves them.", hold=5.0)
    typed(t, "moneyhub engines status", o["engines"], head=10, say="Engines lists the optional video engines. Finally, moneyhub ui opens the app.", hold=3.6)


TUTORIALS = [
    ("audience", "Pick an audience and a product", "Choose who to help, see only the products that fit them, Surprise me, and your own audience.", tut_audience),
    ("options", "Product options", "The options that belong to each product: themes, ages, names, decks and learning focus.", tut_options),
    ("decoration", "Page decoration", "Optional corner art, title-bar pictures and pale backgrounds for planners, with strength and themes.", tut_decoration),
    ("look", "Colours, fonts, layouts and e-ink", "Palettes, your brand colour, fonts, advanced look, page layouts, described layouts and e-ink.", tut_look),
    ("product-page", "The product page", "Preview, quality checks, files, listing copy, photos and upload guides.", tut_product_page),
    ("sell-on", "What to upload on each platform", "Platform packs for Etsy, Gumroad, Payhip and Ko-fi, and what goes where.", tut_sell_on),
    ("exports", "Canva, Notion and KDP", "Turn a product into a Canva pack, a Notion import or a KDP paperback.", tut_exports),
    ("track", "Track sales and learn", "Record listings, sales and views, and read the Sales and learning report.", tut_track),
    ("ideas", "The Ideas page", "Brainstorm audiences and products, and check them by hand.", tut_ideas),
    ("settings", "Settings, AI keys and tools", "Connect AI helpers, art providers and the optional second-opinion tools.", tut_settings),
    ("variations", "Variations and the catalogue", "New variations, My products and deleting.", tut_variations),
    ("editing", "Edit the art yourself", "Export layered editable files and upload your edits back.", tut_editing),
    ("launch-video", "The launch video", "Make a promo video with music, tone and captions.", tut_launch_video),
    ("cli-basics", "Command line: the basics", "types, styles, make, list and look flags.", tut_cli_basics),
    ("cli-selling", "Command line: listing and learning", "risk, export pack, approve, listed, sale, report, next, keywords, calendar.", tut_cli_selling),
    ("cli-scale", "Command line: many products", "make-many, bundle, sample, brag, edit export and regenerate.", tut_cli_scale),
    ("cli-tools", "Command line: tools and extras", "doctor, tools, extra files, slide templates, assets, translations and engines.", tut_cli_tools),
]
NEEDS_BROWSER_ONLY = {k for k, *_ in TUTORIALS if not k.startswith("cli-")}


def capture_cli(env: Env, ids: dict) -> dict:
    """Run the real commands the terminal tutorials show and keep their output."""
    print("capturing command output ...", flush=True)
    c = env.cli
    o: dict = {}
    o["types"] = c(["types"])
    o["styles"] = c(["styles"])
    o["make"] = c(["make", "nurse", "habit_tracker", "--llm", "builtin", "--no-video", "--seed", "8"])
    o["list"] = c(["list"])
    o["make_look"] = c(["make", "nurse", "weekly_planner", "--llm", "builtin", "--palette", "ocean", "--fonts", "clean", "--weeks", "12", "--no-video", "--no-images", "--seed", "9"])
    o["risk"] = c(["risk", "1"])
    o["pack"] = c(["export", "pack", "1", "etsy"])
    o["approve"] = c(["approve", "1"])
    o["listed"] = c(["listed", "1", "etsy", "https://www.etsy.com/listing/123", "--price", "9.99"])
    o["sale"] = c(["sale", "1", "etsy", "9.99"])
    o["report"] = c(["report"])
    o["next"] = c(["next"])
    o["keywords"] = c(["keywords", "planner"])
    o["calendar"] = c(["calendar", "--months", "3"])
    o["many"] = c(["make-many", "x", "digital_paper", "--count", "3", "--no-images", "--llm", "builtin"])
    o["bundle"] = c(["bundle", "1,2", "--name", "Nurse Starter Kit", "--llm", "builtin", "--no-images"])
    o["sample"] = c(["sample", "1", "--pages", "2"])
    o["brag"] = c(["brag", "1", "--preview", "--no-llm"])
    o["edit"] = c(["edit", "export", "3"])
    o["regen"] = c(["regenerate", "1", "--llm", "builtin"])
    o["doctor"] = c(["doctor"])
    o["tools"] = c(["tools"])
    o["craft_sheets"] = c(["export", "craft", str(ids["budget"]), "--kinds", "sheets"])
    o["craft_docx"] = c(["export", "craft", str(ids["guide"]), "--kinds", "docx"])
    o["deck"] = c(["make", "x", "presentation_template", "--llm", "builtin", "--no-video"])
    o["assets"] = c(["assets", "list"])
    o["translations"] = c(["translations", "status"])
    o["engines"] = c(["engines", "status"])
    if "not installed" in o["craft_sheets"] or "Nothing built" in o["craft_sheets"]:
        o["craft_sheets"] = o["craft_docx"] = ""
    if "Could not build" in o["deck"] or "Error" in o["deck"][:200]:
        o["deck"] = ""
    return o


# ------------------------------------------------------------------------------------------------ recording
def record(only: set[str] | None):
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required (brew install ffmpeg)")
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="moneyhub-tutorials-"))
    from moneyhub.brag.voice import SayVoice, pick
    voice = pick()
    if isinstance(voice, SayVoice):
        os.environ.setdefault("MONEYHUB_VOICE", "Samantha")
    print("narration:", voice.name if voice else "none (silent videos)")
    env = Env(tmp)
    shutil.copy(ROOT / "moneyhub.yaml", tmp / "moneyhub.yaml")
    import yaml
    (tmp / "moneyhub.local.yaml").write_text(yaml.safe_dump({"output_dir": str(tmp / "out"), "llm": {"tasks": {t: ["builtin"] for t in ("content", "listing", "research", "motion")}}}))
    wanted = [x for x in TUTORIALS if not only or x[0] in only]
    done: list[dict] = []
    server = None
    try:
        needs = {k for k, *_ in wanted} - {"audience", "options", "look", "ideas", "settings"}
        ids = {}
        if needs:
            print("making real products for the tutorials ...", flush=True)
            ids = prebuild(env)
        ctx = {"ids": ids, "tmp": tmp, "cli": capture_cli(env, ids) if any(k.startswith("cli-") for k, *_ in wanted) else {}}
        server = RT.start_server(tmp)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for key, title, blurb, fn in wanted:
                if key == "cli-tools" and not ctx["cli"].get("tools"):
                    continue
                print(f"recording {key} ...", flush=True)
                vctx = browser.new_context(viewport=RT.SIZE, record_video_dir=str(tmp / "video" / key), record_video_size=RT.SIZE)
                vctx.add_init_script(RT.OVERLAY)
                page = vctx.new_page()
                tour = T(page, voice, tmp)
                try:
                    fn(tour, ctx)
                    tour.cap("", 0.3)
                    ok = True
                except BaseException:   # noqa: BLE001 - one broken tutorial must not lose the others
                    traceback.print_exc()
                    page.screenshot(path=str(Path(tempfile.gettempdir()) / f"tutorial-{key}-failure.png"))
                    ok = False
                vctx.close()
                if not ok:
                    continue
                raw = Path(page.video.path())
                m = tour.marks
                fast = (m["wait0"], m["wait1"]) if "wait0" in m and "wait1" in m else None
                RT.encode(raw, OUT / f"{key}.mp4", start=0.4, fast=fast, factor=8, events=tour.events)
                dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(OUT / f"{key}.mp4")]))
                done.append({"key": key, "title": title, "blurb": blurb, "seconds": round(dur), "kind": "app" if key in NEEDS_BROWSER_ONLY else "terminal"})
                print(f"  {key}.mp4 {(OUT / f'{key}.mp4').stat().st_size / 1e6:.1f} MB, {dur:.0f}s", flush=True)
            browser.close()
    finally:
        if server:
            server.terminate()
        shutil.rmtree(tmp, ignore_errors=True)
    # keep entries of tutorials not re-recorded this time
    idx = OUT / "index.json"
    old = {e["key"]: e for e in json.loads(idx.read_text())} if idx.exists() else {}
    for e in done:
        old[e["key"]] = e
    order = [k for k, *_ in TUTORIALS]
    idx.write_text(json.dumps(sorted(old.values(), key=lambda e: order.index(e["key"]) if e["key"] in order else 99), indent=1))
    print(f"{len(done)} tutorial video(s) written to {OUT}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma list of tutorial keys")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        for k, title, blurb, _ in TUTORIALS:
            print(f"{k:<14} {title}: {blurb}")
        return
    record(set(a.only.split(",")) if a.only else None)


if __name__ == "__main__":
    main()
