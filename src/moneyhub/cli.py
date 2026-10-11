"""moneyhub command line."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import typer

from .config import get_config
from .design import GRIDS, HEADERS, PALETTES, RADII, FONT_PAIRS, font_keys, palette_keys
from .niches import library_keys, resolve_niche
from .pipeline import Request, generate, make_package
from .products import all_product_types
from .store import Store

app = typer.Typer(help="MoneyHub - generate sellable digital products and listing kits.", no_args_is_help=True)


def _check(value, allowed: list, flag: str):
    if value is not None and value not in allowed:
        raise typer.BadParameter(f"{value!r} is not valid; choose one of: {', '.join(map(str, allowed))}", param_hint=flag)
    return value


def _csv(v: str | None) -> list[str] | None:
    return [x.strip() for x in v.split(",") if x.strip()] if v else None


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", "-v")):
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    for noisy in ("fontTools", "weasyprint", "httpx"):  # noqa
        logging.getLogger(noisy).setLevel(logging.ERROR)


@app.command()
def make(
    niche: str = typer.Argument(..., help="Any niche, e.g. 'ADHD', 'nurse', 'dog training'"),
    product: str = typer.Argument("weekly_planner", help="run `moneyhub types` for the list"),
    sizes: str = typer.Option(None, help="Comma list: letter,a4,a5,tablet,eink"),
    seed: int = typer.Option(None, help="Reuse a seed to reproduce a look"),
    palette: str = typer.Option(None, help=f"One of: {', '.join(palette_keys())}"),
    fonts: str = typer.Option(None, help=f"Font pair, one of: {', '.join(font_keys())}"),
    page_layout: str = typer.Option(None, "--page-layout", help="Page layout for products that have several (see `moneyhub styles`), e.g. grid, focus, minimal"),
    layout_prompt: str = typer.Option(None, "--layout-prompt", help="Describe the page layout you want in words, e.g. 'big priorities on the left, habit row at the bottom'"),
    brand: str = typer.Option(None, help="Your own brand colour as hex, e.g. '#2F6B57'; builds a matching palette"),
    eink: bool = typer.Option(False, help="E-ink tablet version (reMarkable / Kindle Scribe / Boox): black and white, hyperlinked"),
    header: str = typer.Option(None, help=f"Page header style: {', '.join(HEADERS)}"),
    radius: int = typer.Option(None, help=f"Card corner radius in px: {', '.join(map(str, RADII))}"),
    grid: str = typer.Option(None, help=f"Grid line style: {', '.join(GRIDS)}"),
    motif: str = typer.Option(None, help="Wall art: background motif (see `moneyhub styles`), or icon:<set> / icon:<set>/<name> for a big open-source icon; default varies per poster"),
    layout: int = typer.Option(None, hidden=True, help="Old wall-art layout number 0-4; use --page-layout instead"),
    art_provider: str = typer.Option(None, help="AI art provider chain, e.g. 'claude_svg' (Claude draws vector art) or 'huggingface,together' (implies --ai-art)"),
    marketplaces: str = typer.Option(None, help="Guides to write: etsy,gumroad,payhip,kofi,pinterest (default all)"),
    llm: str = typer.Option(None, help="Provider chain override, e.g. 'claude_cli,builtin' or 'builtin'"),
    weeks: int = typer.Option(None, help="Weekly planner: number of weeks (4-60)"),
    no_images: bool = typer.Option(False, help="Skip listing images/pins"),
    no_video: bool = typer.Option(False, help="Skip the MP4 pin / listing video"),
    motion: str = typer.Option(None, help="Video engine chain, e.g. 'remotion,pillow' (engines: pillow, remotion, manim, hyperframes)"),
    ai_art: bool = typer.Option(False, help="Wall art: use the AI image providers configured in render.art for backgrounds"),
    days: int = typer.Option(None, help="Daily planner: number of pages (7-120)"),
    pages: int = typer.Option(None, help="Coloring books: number of pages (10-40)"),
    language: str = typer.Option(None, help="Learning workbook and Montessori cards: en (default), es, fr or de (names in that language, English instructions)"),
    level: str = typer.Option(None, help="Kids activity book: toddler, kids or big (maze size, dots, line thickness)"),
    focus: str = typer.Option(None, help="Kids learning workbook: mixed, colours, words, numbers, time, feelings, handwriting, cursive, sightwords or stem"),
    grade: str = typer.Option(None, help="Learning workbook, sightwords focus: prek, k (default), 1, 2 or 3 (Dolch list)"),
    deck: str = typer.Option(None, help="Oracle deck: 'oracle' (gentle message cards, default) or 'tarot' (22 archetype cards)"),
    card_size: str = typer.Option(None, help="Oracle deck: 'tall' (2.5 x 4.5 in, default) or 'poker' (2.5 x 3.5 in)"),
    cards: int = typer.Option(None, help="Oracle deck: number of oracle cards (12-36)"),
    count: int = typer.Option(None, help="Character clipart: number of characters (12-60); icon stickers: number of icons (12-120)"),
    collection: str = typer.Option(None, help="Icon stickers: installed icon set (see `moneyhub assets list`)"),
    query: str = typer.Option(None, help="Icon stickers: only icons whose name contains one of these comma-separated words"),
    shape: str = typer.Option(None, help="Icon stickers: badge shape circle, rounded or none"),
    stickers: int = typer.Option(None, help="Sticker sheets: number of stickers (12-48)"),
    theme: str = typer.Option(None, help="Kids coloring book and sticker sheets: picture theme (mixed, animals, ocean, garden, vehicles, dinosaurs, treats)"),
    age: str = typer.Option(None, help="Kids coloring book: 'kids' (ages 4-8) or 'toddler' (thicker, simpler lines)"),
    figures: bool = typer.Option(False, "--figures", help="Cut files: make the designs from the kids figures (one closed outline each; use --theme to choose them)"),
    print_then_cut: bool = typer.Option(False, "--print-then-cut", help="Sticker sheets: also write print-then-cut PNG sheets and cut-line SVGs (Cricut, Silhouette, Brother)"),
    names: str = typer.Option(None, help="Classroom printables: student names to print on tags and desk plates, comma separated (up to 30); blank lines to write in when omitted"),
    no_research: bool = typer.Option(False, help="Do not use an LLM to research unknown niches"),
    gsheet_link: str = typer.Option(None, help="Spreadsheet products: your Google Sheets link (its /edit ending becomes /copy on the Start Here page)"),
):
    """Generate one product with its images, listing copy and upload guides."""
    from .art import WALL_MOTIFS as MOTIFS
    from .design import is_hex_colour
    if brand and not is_hex_colour(brand):
        raise typer.BadParameter("use a hex colour like '#2F6B57'", param_hint="--brand")
    if palette and is_hex_colour(palette):
        brand, palette = brand or palette, None
    _check(palette, palette_keys(), "--palette"), _check(fonts, font_keys(), "--fonts"), _check(header, HEADERS, "--header")
    from . import kidsart
    _check(language, ["en", "es", "fr", "de"], "--language"), _check(level, ["toddler", "kids", "big"], "--level"), _check(focus, ["mixed", "colours", "words", "numbers", "time", "feelings", "handwriting", "cursive", "sightwords", "stem"], "--focus"), _check(grade, ["prek", "k", "1", "2", "3"], "--grade")
    if language and language != "en" and focus in ("handwriting", "cursive", "sightwords", "stem"):
        raise typer.BadParameter(f"the {focus} focus is English only", param_hint="--language")
    _check(deck, ["oracle", "tarot"], "--deck"), _check(card_size, ["tall", "poker"], "--card-size")
    _check(theme, list(kidsart.THEMES), "--theme"), _check(age, list(kidsart.AGES), "--age")
    if names:
        from .products.classroom_pack import parse_names
        try:
            names = ", ".join(parse_names(names))
        except ValueError as e:
            raise typer.BadParameter(str(e), param_hint="--names")
    _check(radius, RADII, "--radius"), _check(grid, GRIDS, "--grid"), _check(motif if not (motif or "").startswith("icon:") else None, MOTIFS, "--motif"), _check(layout, list(range(5)), "--layout")
    if layout is not None and not page_layout:   # the old numbered wall-art layouts are now the first five presets
        from .layouts import ART_PRESETS
        page_layout = list(ART_PRESETS)[layout]
    if page_layout:
        from .products import get_product_type
        try:
            have = get_product_type(product).layouts
        except KeyError as e:
            raise typer.BadParameter(str(e), param_hint="product")
        if not get_product_type(product).has_layout(page_layout):
            raise typer.BadParameter(f"{product} " + (f"has these layouts: {', '.join(have)}" + (", auto, auto:<number>" if get_product_type(product).auto_layout else "") if have else "has only one layout"), param_hint="--page-layout")
    layout_spec = None
    if layout_prompt:
        from . import layouts as _lay
        from .llm import get_router
        if product not in _lay.SPEC_MODELS:
            raise typer.BadParameter(f"{product} has no generated layouts (try weekly_planner, daily_planner or wall_art)", param_hint="--layout-prompt")
        spec_obj, how = _lay.spec_from_text(product, layout_prompt, get_router(), _csv(llm))
        layout_spec = spec_obj.model_dump()
        typer.echo(f"Layout '{spec_obj.name}' ({'designed by your AI helper' if how == 'ai' else 'generated; no AI helper was available'}): {spec_obj.model_dump_json()}")
    if motif and motif.startswith("icon:"):
        from .art import check_icon_motif
        try:
            check_icon_motif(motif)
        except ValueError as e:
            raise typer.BadParameter(str(e), param_hint="--motif")
    art_chain = _csv(art_provider)
    for a in art_chain or []:
        _check(a, __import__("moneyhub.art", fromlist=["ALL_ART_PROVIDERS"]).ALL_ART_PROVIDERS, "--art-provider")
    if (ai_art or art_chain) and product != "wall_art":
        typer.echo("note: AI art backgrounds only apply to wall_art; ignoring for this product.", err=True)
    if (ai_art or art_chain) and product == "wall_art":
        from .art import PROVIDERS, SVG_PROVIDERS
        every = {**PROVIDERS, **SVG_PROVIDERS}
        usable = [n for n in (art_chain or get_config().get("render.art") or ["claude_svg"]) if n in every and every[n].available()]
        if not usable:
            typer.echo("note: no AI art provider is usable. Use --art-provider claude_svg (needs Claude Code or another writing helper), or add a key "
                       "in Settings (Hugging Face / Together / OpenAI). Falling back to built-in motifs.", err=True)
    opts = {k: v for k, v in {"weeks": weeks, "days": days, "pages": pages, "stickers": stickers, "count": count, "collection": collection, "query": query, "shape": shape, "deck": deck, "card_size": card_size, "level": level, "focus": focus, "grade": grade, "language": language, "names": names, "print_then_cut": print_then_cut or None, "figures": figures or None, "cards": cards, "theme": theme, "age": age, "ai_art": (ai_art or bool(art_chain)) or None, "no_research": no_research or None,
                              "gsheet_url": gsheet_link, "page_layout": page_layout, "layout_spec": layout_spec, "brand": brand, "eink": eink or None, "header": header, "radius": radius, "grid": grid, "motif": motif,
                              "art_providers": art_chain}.items() if v is not None and v != "" and v is not False}
    req = Request(niche=niche, product_type=product, sizes=_csv(sizes), seed=seed, palette=palette, fonts=fonts,
                  providers=_csv(llm), options=opts, with_images=not no_images, with_video=not no_video, motion=_csv(motion))
    if marketplaces:
        req.marketplaces = _csv(marketplaces)
    res = generate(req, progress=lambda m: typer.echo(f"  - {m}"))
    typer.echo(f"\n{res.title}  [{res.qa_status.upper()}]")
    typer.echo(f"Folder: {res.folder}")
    typer.echo(f"Upload package: {res.folder / 'upload-package.zip'}")
    for c in res.checks:
        if c.status != "pass":
            typer.echo(f"  {c.status.upper()}: {c.name} - {c.detail}")


@app.command()
def styles():
    """List every look option `make` accepts: palettes, fonts, headers, radii, grids, motifs, layouts, AI art providers."""
    from .art import WALL_MOTIFS as MOTIFS, art_status
    typer.echo("Palettes (--palette):")
    for p in PALETTES:
        typer.echo(f"  {p.key:<11} accent {p.accent}  accent2 {p.accent2}  soft {p.soft}  mood: {', '.join(p.mood)}")
    typer.echo("\nFont pairs (--fonts):")
    for f in FONT_PAIRS:
        typer.echo(f"  {f.key:<10} headings {f.heading}, body {f.body}, script {f.script}")
    typer.echo(f"\nHeader styles (--header): {', '.join(HEADERS)}")
    typer.echo(f"Corner radius px (--radius): {', '.join(map(str, RADII))}")
    typer.echo(f"Grid lines (--grid): {', '.join(GRIDS)}")
    typer.echo(f"Wall art motifs (--motif): {', '.join(MOTIFS)}")
    typer.echo("\nPage layouts (--page-layout), by product:")
    from .products import all_product_types as _all
    for key, t in _all().items():
        if t.layouts:
            typer.echo(f"  {key}:")
            for name, desc in t.layouts.items():
                typer.echo(f"    {name:<11} {desc}")
    typer.echo("\nAI art providers (--art-provider; need a key/URL, see doctor):")
    for a in art_status():
        typer.echo(f"  {'ok ' if a['available'] else '-- '} {a['name']}")


export_app = typer.Typer(help="Export a finished product for another platform: kdp (Amazon paperback), notion, canva.", no_args_is_help=True)
app.add_typer(export_app, name="export")


@export_app.command("craft")
def export_craft(product_id: int, kinds: str = typer.Option("vectors,sheets,pdfs,docx", help="vectors (AI/EPS/PDF/PSD copies of poster designs), "
                                                                                  "sheets (CSV/HTML copies of spreadsheets), pdfs (title/author metadata), docx (editable Word copy of guide/worksheet/checklist/journal text)")):
    """Build extra editable files for a product with the craft tools. Needs the tools installed; ignores the on/off switches because you asked."""
    from . import craftbuild
    from .store import Store
    p = Store().product(product_id)
    if not p:
        raise typer.BadParameter(f"no product #{product_id}", param_hint="product_id")
    want = [k.strip() for k in kinds.split(",") if k.strip()]
    bad = [k for k in want if k not in craftbuild.KINDS]
    if bad:
        raise typer.BadParameter(f"unknown kind(s): {', '.join(bad)}. Choose from: {', '.join(craftbuild.KINDS)}", param_hint="--kinds")
    rows = craftbuild.build(Path(p["folder"]), product_id, want, force=True)
    if not rows:
        typer.echo("Nothing built: the tool is not installed, or the product has nothing of that kind (poster designs, xlsx files).")
        return
    for r in rows:
        typer.echo(f"{'ok  ' if r['ok'] else 'SKIP'} {r['kind']:<8} {r['file']:<44} {r['detail']}" + (f"   [{r['warn']}]" if r['warn'] else ""))
    typer.echo(f"Report: {Path(p['folder']) / 'craft-build.json'}\nFiles: {Path(p['folder']) / 'product' / craftbuild.FOLDER}")
    if any(not r["ok"] for r in rows):
        raise typer.Exit(1)


@export_app.command("kdp")
def export_kdp_cmd(product_id: int, trim: str = typer.Option("6x9", help="5.5x8.5, 6x9, 7x10, 8x10 or 8.5x11 (inches)"),
                   paper: str = typer.Option("white", help="white, cream or color"),
                   cover_image: Path = typer.Option(None, exists=True, dir_okay=False, help="Your own front-cover artwork (JPG/PNG, ideally 300 dpi at the front size); the title is drawn over it"),
                   cover_text: bool = typer.Option(True, "--cover-text/--no-cover-text", help="Draw the title over a cover image (turn off if your art already has the title)")):
    """Print-ready interior, a finished full-wrap cover (plus a guide-line template), and a KDP guide."""
    from .exports import kdp, load
    spec = kdp.export_kdp(load(product_id), trim, paper, progress=lambda m: typer.echo(f"  - {m}"), cover_image=cover_image, cover_text=cover_text)
    typer.echo(f"\nKDP pack: {spec['pages']} pages, spine {spec['spine_in']} in, cover {spec['full_cover_in'][0]} x {spec['full_cover_in'][1]} in")
    for c in spec["checks"]:
        typer.echo(f"  {'ok ' if c['ok'] else 'FAIL'} {c['name']}: {c['detail']}")
    typer.echo(f"Folder: {load(product_id).folder / 'exports' / 'kdp'}")


@export_app.command("pack")
def export_pack_cmd(product_id: int, platform: str = typer.Argument(..., help="etsy, gumroad, payhip or kofi")):
    """One zip for a marketplace: the buyer download (split to fit its limits), listing images, copy and guide."""
    from .exports import load
    from .listing import platforms
    if platform not in platforms.PLATFORMS:
        raise typer.BadParameter(f"choose one of: {', '.join(platforms.PLATFORMS)}", param_hint="platform")
    folder = load(product_id).folder
    p = platforms.plan(folder, platform)
    z = platforms.build_pack(folder, platform)
    typer.echo(f"{p['label']} pack: {z}")
    for d in p["downloads"]:
        typer.echo(f"  {'ok ' if d['ok'] else 'BIG'} {d['name']} ({d['size'] / 1e6:.1f} MB)")
    for w in p["warnings"]:
        typer.echo(f"  ! {w}")


@export_app.command("notion")
def export_notion_cmd(product_id: int):
    """Zip of Markdown pages and CSV databases to import into Notion."""
    from .exports import load, notion
    z = notion.export_notion(load(product_id))
    typer.echo(f"Notion pack: {z}")


@export_app.command("canva")
def export_canva_cmd(product_id: int, link: str = typer.Option(None, help="Your Canva template link, to put on the buyer's page")):
    """PDF and page images for Canva, a brand kit, a buyer 'template link' page and a how-to."""
    from .exports import canva, load
    typer.echo(f"Canva pack: {canva.export_canva(load(product_id), link)}")


@app.command(name="next")
def next_cmd(limit: int = typer.Option(5, help="How many suggestions")):
    """What to make next, learned from the sales and views you have recorded."""
    from .growth import recommend
    r = recommend(limit=limit)
    typer.echo(r["note"] + "\n")
    for i, x in enumerate(r["make_next"], 1):
        typer.echo(f"{i}. {x['niche']} / {x['product_type']}  [{x['kind']}]\n   {x['reason']}\n   moneyhub make \"{x['niche']}\" {x['product_type']}")
    if r["good_looks"]:
        typer.echo("\nColours that did well: " + ", ".join(r["good_looks"]))


@app.command()
def layouts(product: str = typer.Argument("weekly_planner"), count: int = typer.Option(8, help="How many generated layouts to show"),
            first: int = typer.Option(1, help="First layout number"), out: Path = typer.Option(Path("layouts.png"), help="Contact sheet image to write")):
    """See generated page layouts for a product as one picture. Use the number with `--page-layout auto:NUMBER`."""
    import io

    from PIL import Image

    from .products import get_product_type
    from .render.preview import layout_preview_png
    pt = get_product_type(product)
    if not pt.auto_layout:
        raise typer.BadParameter(f"{product} has no generated layouts")
    keys = [*pt.layouts, *[f"auto:{n}" for n in range(first, first + count)]]
    ims = []
    for k in keys:
        typer.echo(f"  rendering {k}")
        ims.append(Image.open(io.BytesIO(layout_preview_png(product, k))))
    cols = 4
    w, h = max(i.width for i in ims), max(i.height for i in ims)
    sheet = Image.new("RGB", (cols * w, -(-len(ims) // cols) * h), "white")
    for n, im in enumerate(ims):
        sheet.paste(im, ((n % cols) * w, (n // cols) * h))
    sheet.save(out)
    typer.echo(f"Wrote {out}: presets {', '.join(pt.layouts)}, then auto:{first} to auto:{first + count - 1}")


@app.command()
def batch(
    niches: str = typer.Argument(..., help="Comma list of niches"),
    products: str = typer.Option("weekly_planner,habit_tracker,guided_journal", help="Comma list of product types"),
    llm: str = typer.Option(None),
):
    """Make every product type for every niche (e.g. the first 5-10 products to test demand)."""
    for n in _csv(niches) or []:
        for p in _csv(products) or []:
            typer.echo(f"\n=== {n} / {p}")
            res = generate(Request(niche=n, product_type=p, providers=_csv(llm)), progress=lambda m: typer.echo(f"  - {m}"))
            typer.echo(f"  -> {res.title} [{res.qa_status}] {res.folder}")


tr_app = typer.Typer(help="Proofreading guardrail for the Spanish / French / German word lists: AI check, human sign-off, status.", no_args_is_help=True)
app.add_typer(tr_app, name="translations")


@tr_app.command("status")
def tr_status():
    """Review status of each language (what the QA check will say)."""
    from .translations import LANGS, review_status
    for lang in ("es", "fr", "de"):
        st, msg = review_status(lang)
        typer.echo(f"  {st.upper():<5} {LANGS[lang]}: {msg}")


@tr_app.command("check")
def tr_check(lang: str = typer.Option("all", help="es, fr, de or all"), llm: str = typer.Option(None, help="Provider chain override, e.g. claude_cli")):
    """Ask the AI helper to proofread the word list. Reports problems and records the result; it never edits the words."""
    from .translations import LANGS, ai_check, record_ai
    langs = ["es", "fr", "de"] if lang == "all" else [lang]
    for lg in langs:
        if lg not in ("es", "fr", "de"):
            raise typer.BadParameter("choose es, fr, de or all", param_hint="--lang")
        typer.echo(f"Checking {LANGS[lg]}...")
        res = ai_check(lg, _csv(llm))
        if not res["checked"]:
            typer.echo(f"  not checked: {res['reason']}")
            continue
        record_ai(lg, res)
        typer.echo(f"  {res['words']} words checked with {res['source']}: {len(res['issues'])} flagged")
        for i in res["issues"]:
            typer.echo(f"    {i['english']}: '{i['given']}' -> '{i.get('suggestion') or '?'}'  {i.get('note', '')}")
    typer.echo("An AI check is a safety net, not a native speaker. Have a person review, then: moneyhub translations approve --lang es --by 'Name'")


@tr_app.command("approve")
def tr_approve(lang: str = typer.Option(..., help="es, fr or de"), by: str = typer.Option(..., help="Who reviewed the list")):
    """Record that a person proofread the current word list (it stops counting if the words change)."""
    from .translations import approve
    try:
        approve(lang, by)
    except ValueError as e:
        raise typer.BadParameter(str(e))
    typer.echo(f"Signed off {lang} by {by}")


assets_app = typer.Typer(help="Open-source SVG icon sets used as raw material (licence-checked): list, fetch tabler/lucide, add your own folder.", no_args_is_help=True)
app.add_typer(assets_app, name="assets")


@assets_app.command("list")
def assets_list():
    """Installed icon sets, their licences and what can be fetched."""
    from . import svgassets
    have = svgassets.collections()
    for c in have:
        typer.echo(f"  {c['key']:<14} {c['icons']:>5} icons  {c['license']:<8} {c['name']}  (fetched {c['fetched']})")
    if not have:
        typer.echo("  none installed yet")
    typer.echo("\nCan fetch: " + ", ".join(f"{k} ({v['license']})" for k, v in svgassets.KNOWN.items()) + "\nUse: moneyhub assets fetch tabler")


@assets_app.command("fetch")
def assets_fetch(key: str = typer.Argument(..., help="tabler, tabler-filled or lucide"), limit: int = typer.Option(600, help="How many icons to download (evenly spaced)")):
    """Download an open-source icon set (MIT / ISC) and install it with its licence."""
    from . import svgassets
    try:
        d = svgassets.fetch(key, limit, progress=typer.echo)
    except Exception as e:  # noqa: BLE001
        raise typer.BadParameter(str(e), param_hint="key")
    typer.echo(f"Installed to {d}")


@assets_app.command("add")
def assets_add(folder: Path = typer.Argument(..., exists=True, file_okay=False), name: str = typer.Option(..., help="A short key, e.g. my-icons"),
               license: str = typer.Option(..., help="SPDX id: CC0-1.0, MIT, ISC, Apache-2.0, PD or CC-BY-4.0"), source: str = typer.Option(..., help="Where the files came from (URL)")):
    """Add your own folder of SVG icons. Refuses licences that would not allow reselling products made from them."""
    from . import svgassets
    try:
        d = svgassets.install(name, name, license, source, {p.name: p.read_text(encoding="utf-8", errors="ignore") for p in folder.glob("*.svg")})
    except ValueError as e:
        raise typer.BadParameter(str(e))
    typer.echo(f"Installed to {d}")


@app.command(name="delete")
def delete_cmd(product_id: int, yes: bool = typer.Option(False, "--yes", "-y", help="Do not ask first")):
    """Delete a product from the catalogue and remove its files."""
    from .pipeline import delete_product
    p = Store().product(product_id)
    if not p:
        raise typer.BadParameter(f"no product #{product_id}", param_hint="product_id")
    if not yes and not typer.confirm(f"Delete #{product_id} '{p['title']}' and its files?"):
        raise typer.Abort()
    delete_product(product_id)
    typer.echo(f"Deleted #{product_id}")


@app.command(name="list")
def list_products():
    """Show the catalogue."""
    for p in Store().products():
        typer.echo(f"#{p['id']:<4} {p['status']:<9} {p['product_type']:<15} {p['title']}  ({p['niche_name']}, ${p['price']:.2f})")


@app.command()
def types():
    """List product types, niches, sizes and LLM providers."""
    typer.echo("Product types:")
    for k, t in all_product_types().items():
        typer.echo(f"  {k:<16} {t.description}")
    typer.echo("\nBuilt-in niche profiles (any other text also works): " + ", ".join(library_keys()))
    typer.echo("\nLLM providers:")
    from .llm import get_router
    for row in get_router().status():
        typer.echo(f"  {'ok ' if row['available'] else '-- '} {row['name']:<11} {row['model']}")


@app.command()
def niche(text: str, research: bool = typer.Option(False, help="Use an LLM to research it (cached) if it is not built in")):
    """Show the profile the system will use for a niche."""
    if research:
        from .niches import smart_resolve
        profile, source = smart_resolve(text)
        typer.echo(f"# source: {source}")
        typer.echo(profile.model_dump_json(indent=2))
    else:
        typer.echo(resolve_niche(text).model_dump_json(indent=2))


@app.command()
def ideas(n: int = typer.Option(15, help="How many ideas"), focus: str = typer.Option(None, help="e.g. 'pets', 'students', 'health professionals'"),
          llm: str = typer.Option(None)):
    """Brainstorm niche + product ideas (LLM hypotheses - validate with Etsy/Pinterest searches before building)."""
    from .ideas import suggest_ideas
    data = suggest_ideas(n, focus, _csv(llm))
    typer.echo(f"(from {data['source']}; hypotheses, not live search data)\n")
    for i, d in enumerate(data["ideas"], 1):
        typer.echo(f"{i:>2}. [{d['product_type']}] {d['niche']}  - {d['angle']}")
        typer.echo(f"      why: {d['why']}\n      validate: {', '.join(d['keywords'])}  (competition: {d['competition']})")


@app.command()
def regenerate(product_id: int, llm: str = typer.Option(None)):
    """Make a fresh variation (new seed/look/copy) of an existing product's niche and type."""
    st = Store()
    p = st.product(product_id)
    if not p:
        raise typer.BadParameter("no such product")
    spec = json.loads((Path(p["folder"]) / "spec.json").read_text())
    r = spec["request"]
    res = generate(Request(niche=r["niche"], product_type=r["product_type"], sizes=r.get("sizes"), providers=_csv(llm),
                           options=r.get("options") or {}), progress=lambda m: typer.echo(f"  - {m}"))
    typer.echo(f"{res.title} [{res.qa_status}] {res.folder}")


@app.command()
def risk(product_id: int = typer.Argument(None), text: str = typer.Option(None, help="Check any text instead of a product")):
    """Scan a product's listing text (or any --text) for brand/trademark terms, risky claims and rights language."""
    from . import risk as riskmod
    if text:
        findings = riskmod.scan_text(text, "text")
    else:
        p = Store().product(product_id) if product_id else None
        if not p:
            raise typer.BadParameter("give a product id or --text")
        folder = Path(p["folder"])
        listing = json.loads((folder / "listing" / "listing.json").read_text())
        spec = json.loads((folder / "spec.json").read_text())
        findings = riskmod.scan_listing(listing, json.dumps(spec["content"]), spec["request"]["niche"])
    if not findings:
        typer.echo("Nothing on the watch list. (This is a safety net, not legal advice.)")
    for f in findings:
        typer.echo(f"[{f.severity.upper():6}] {f.where:<11} '{f.term}'  ({f.group}) - {f.advice}")
    raise typer.Exit(1 if riskmod.status(findings) == "fail" else 0)


@app.command()
def approve(product_id: int):
    Store().set_status(product_id, "approved")
    typer.echo("approved")


@app.command()
def listed(product_id: int, marketplace: str, url: str, price: float = typer.Option(0.0)):
    """Record that you listed a product on a marketplace."""
    p = Store().product(product_id)
    Store().add_listing(product_id, marketplace, url, price or (p or {}).get("price", 0))
    typer.echo("recorded")


@app.command()
def sale(product_id: int, marketplace: str, revenue: float, units: int = 1, day: str = typer.Option("")):
    """Record a sale to learn which products earn."""
    import datetime as dt
    Store().add_sale(product_id, marketplace, day or dt.date.today().isoformat(), units, revenue)
    typer.echo("recorded")


@app.command()
def report():
    """Which niche/product/style is working?"""
    rows = Store().performance()
    for r in rows:
        typer.echo(f"#{r['id']:<4} ${r['revenue']:<8.2f} {r['units']:>3} sold {r['views']:>6} views {r['favourites']:>4} favs  {r['title']} [{r['style']}]")


edit_app = typer.Typer(help="Visual editing step: export layered SVGs for Penpot/Inkscape/Open Design and import your edits.", no_args_is_help=True)
app.add_typer(edit_app, name="edit")


@edit_app.command("export")
def edit_export(product_id: int):
    """Write layered, editable SVGs (pins, hero, posters) + fonts + a design brief into <product>/editable/."""
    from .editable import export_editable
    p = Store().product(product_id)
    if not p:
        raise typer.BadParameter("no such product")
    out = export_editable(Path(p["folder"]), product_id)
    typer.echo(f"Editable files: {out}\nImport the SVGs into Penpot (see docs/editing.md), export PNG/JPG with the same names into {out / 'edited'}, then:\n  moneyhub edit import {product_id}")


@edit_app.command("import")
def edit_import(product_id: int, folder: Path = typer.Argument(None, help="Folder with edited exports (default: <product>/editable/edited)")):
    """Replace listing images with your edited exports (matched by file name) and rebuild the upload package."""
    from .editable import import_edits
    p = Store().product(product_id)
    if not p:
        raise typer.BadParameter("no such product")
    src = folder or Path(p["folder"]) / "editable" / "edited"
    done = import_edits(Path(p["folder"]), src)
    for a, b in done:
        typer.echo(f"  {a}  ->  {b}")
    typer.echo(f"{len(done)} image(s) replaced; originals saved in images/_original/" if done else "No matching files found (name them like pin-01.png, 01-hero.jpg, gumroad-cover.png).")


@app.command()
def brag(
    product_id: int = typer.Argument(None, help="Product id to make a launch video for"),
    shop: str = typer.Option(None, "--shop", help="Comma-separated product ids for a shop/collection video"),
    url: str = typer.Option(None, "--url", help="Make a launch video from a website (needs Playwright + Chromium)"),
    tone: str = typer.Option(None, help="polished | playful | cinematic | chaotic | app-store | ... or free text like 'calm and cosy'"),
    fmt: str = typer.Option("vertical", "--format", help="vertical | landscape | square | all"),
    duration: float = typer.Option(20.0, help="Target seconds (12-30)"),
    voice: str = typer.Option("", help="Voice-over: 'auto' or an engine (kokoro | say | espeak). Empty = none"),
    music: str = typer.Option("generated", help="generated | none | file"),
    music_file: Path = typer.Option(None, help="Your own licensed track (with --music file)"),
    captions: bool = typer.Option(False, help="Burn captions into the video"),
    llm: bool = typer.Option(True, "--llm/--no-llm", help="Let an LLM write the story (falls back to the built-in writer)"),
    providers: str = typer.Option(None, help="Provider chain override, e.g. claude_cli,ollama"),
    preview: bool = typer.Option(False, help="Half-size, 15 fps draft"),
):
    """Launch video with music, motion and share copy (Pinterest/Reels/TikTok) for a product, collection or website."""
    from .brag.pipeline import make_brag
    from .brag.render import FORMATS
    from .brag import sources
    if fmt != "all" and fmt not in FORMATS:
        raise typer.BadParameter("format must be vertical, landscape, square or all")
    if url:
        mat = sources.from_url(url, FORMATS["vertical" if fmt == "all" else fmt])
    elif shop:
        mat = sources.from_shop([int(x) for x in shop.split(",") if x.strip()])
    elif product_id is not None:
        mat = sources.from_product(product_id)
    else:
        raise typer.BadParameter("give a product id, --shop ids, or --url")
    res = make_brag(mat, tone=tone, fmt=fmt, duration=duration, voice=(voice if voice not in ("", "auto") else bool(voice)),
                    music=music, music_file=music_file, captions=captions, providers=_csv(providers), use_llm=llm, preview=preview,
                    progress=lambda m: typer.echo(f"  {m}"))
    typer.echo(f"\nVideo:  {res.video}\nPoster: {res.poster}\nShare copy: {res.share}\nPlan: {res.plan_md}\n"
               f"{res.seconds:.1f}s, story by {res.plan_source}, music {res.music}, voice {res.voice_engine or 'none'}")
    for v in res.extra_videos:
        typer.echo(f"Also:   {v}")


@app.command()
def bundle(subject: str = typer.Argument(..., help="Product ids to combine ('3,4,5'), or a kids theme (halloween, christmas...) or niche to build a bundle from scratch"),
           name: str = typer.Option(None, help="Bundle name (required when combining ids)"),
           discount: float = typer.Option(0.30, help="Discount vs buying separately (0-0.6)"),
           types: str = typer.Option(None, help="Product types to make for a theme or niche, comma separated (default: coloring book, activity book, sticker sheets, "
                                                "character clipart for a theme; weekly planner, habit tracker, budget tracker, checklist pack for a niche)"),
           seed: int = typer.Option(None, help="Reuse a seed to reproduce the shared look"),
           palette: str = typer.Option(None, help=f"One palette for every product, one of: {', '.join(palette_keys())}"),
           fonts: str = typer.Option(None, help=f"One font pair for every product, one of: {', '.join(font_keys())}"),
           sizes: str = typer.Option(None, help="Comma list: letter,a4"),
           llm: str = typer.Option(None, help="Provider chain override, e.g. 'builtin'"),
           no_images: bool = typer.Option(False, help="Skip listing images/pins for the products"),
           video: bool = typer.Option(False, help="Also make the launch video for each product (slow)")):
    """Combine products into one zip + listing kit with fee-aware pricing. Give ids to combine existing products, or a theme / niche to make them."""
    from .growth import make_bundle
    discount = min(0.6, max(0.0, discount))
    parts = [x.strip() for x in subject.split(",") if x.strip()]
    if parts and all(x.isdigit() for x in parts):
        if not name:
            raise typer.BadParameter("give the bundle a name with --name", param_hint="--name")
        out = make_bundle([int(x) for x in parts], name, discount)
        typer.echo(f"Bundle written to {out}\nOpen listing.md for price, tags and description; upload product/*.zip.")
        return
    from .bundles import build_bundle
    _check(palette, palette_keys(), "--palette"), _check(fonts, font_keys(), "--fonts")
    try:
        res = build_bundle(subject, _csv(types), name, discount, seed, palette, fonts, _csv(llm), _csv(sizes), not no_images, video,
                           progress=lambda m: typer.echo(f"  - {m}"))
    except ValueError as e:
        raise typer.BadParameter(str(e))
    typer.echo(f"\n{res.name}")
    for r in res.products:
        typer.echo(f"  #{r.product_id:<4} {r.qa_status.upper():<5} {r.title}")
    typer.echo(f"Bundle written to {res.folder}\nOpen listing.md for price, tags and description; upload product/*.zip. Check the QA notes above first.")


@app.command("make-many")
def make_many_cmd(subject: str = typer.Argument(..., help="Niche or audience (niche-free products ignore it)"),
                  product: str = typer.Argument(..., help="Product type, see `moneyhub types`"),
                  count: int = typer.Option(10, help="How many variations (1-30)"),
                  vary: str = typer.Option("look", help="What changes between them: look, theme, seed (comma separated; layouts and art always change)"),
                  seed: int = typer.Option(None, help="Reuse a seed to reproduce the batch"),
                  sizes: str = typer.Option(None, help="Comma list: letter,a4"),
                  llm: str = typer.Option(None, help="Provider chain override, e.g. 'builtin'"),
                  no_images: bool = typer.Option(False, help="Skip listing images/pins"),
                  video: bool = typer.Option(False, help="Also make the launch video for each (slow)")):
    """Make several distinct variations of one product and print a summary table (id, title, QA, uniqueness)."""
    from .bundles import make_many
    try:
        rows = make_many(subject, product, count, _csv(vary), seed, _csv(llm), _csv(sizes), not no_images, video, progress=lambda m: typer.echo(f"  - {m}"))
    except ValueError as e:
        raise typer.BadParameter(str(e))
    typer.echo(f"\n{'ID':<6}{'QA':<7}{'Uniqueness':<16}Title")
    for r in rows:
        typer.echo(f"{r.product_id:<6}{r.qa.upper():<7}{r.uniqueness:<16}{r.title}")
    warn = [r for r in rows if r.qa != "pass"]
    typer.echo(f"\n{len(rows)} made, {len(warn)} with warnings or failures (open them in `moneyhub ui` or `moneyhub list`).")


@app.command()
def sample(product_id: int, pages: int = typer.Option(2, help="How many pages to include")):
    """Free preview PDF (first pages) for email/Pinterest lead magnets."""
    from .growth import make_sample
    dst = make_sample(product_id, pages)
    typer.echo(f"Sample: {dst}" if dst else "This product has no PDF to sample.")


@app.command()
def calendar(months: int = typer.Option(4, help="How many months ahead to show")):
    """Seasonal opportunities to prepare now (general guidance, not sales data)."""
    from .growth import calendar as cal
    import calendar as pycal
    for row in cal(months=months):
        when = "this month" if row["in_months"] == 0 else f"in {row['in_months']} month(s)"
        typer.echo(f"{pycal.month_name[row['month']]:<10} ({when:<13}) {row['occasion']}: {row['ideas'] if isinstance(row['ideas'], str) else '; '.join(row['ideas'])}")


@app.command()
def keywords(seed: str, suggest: bool = typer.Option(False, help="Also query Google autocomplete (sends the seed text to Google)")):
    """Search-phrase ideas to check by hand in Etsy/Pinterest search boxes. Does not scrape either site."""
    from .growth import keyword_ideas
    for k in keyword_ideas(seed, suggest):
        typer.echo(k)


voices_app = typer.Typer(help="Voice-over engines for 'moneyhub brag --voice'.", no_args_is_help=True)
app.add_typer(voices_app, name="voices")


@voices_app.command("status")
def voices_status():
    from .brag.voice import voice_status
    for v in voice_status():
        typer.echo(f"{'ok ' if v['available'] else '-- '}{v['name']:<8} {'ready' if v['available'] else 'not available'}")


@voices_app.command("install")
def voices_install():
    """Download the Kokoro voice model (~350 MB, Apache-2.0) into ~/.cache/moneyhub/kokoro."""
    from .brag.voice import install_kokoro
    typer.echo(f"Installed: {install_kokoro(progress=lambda m: typer.echo(f'  {m}'))}")


engines_app = typer.Typer(help="Optional video engines: remotion (React), manim (Python) and hyperframes (HTML).", no_args_is_help=True)
app.add_typer(engines_app, name="engines")


@engines_app.command("status")
def engines_status():
    """Which video engines are ready."""
    from .render.motion import engine_status
    for e in engine_status():
        typer.echo(f"{'ok ' if e['available'] else '-- '}{e['name']:<9} {'(in chain)' if e['enabled'] else '          '} {e['note']}")


@engines_app.command("install")
def engines_install(name: str = typer.Argument(..., help="remotion | manim | hyperframes")):
    """Install an optional engine (remotion/hyperframes: npm install in engines/<name>; manim: pip install manim)."""
    import shutil
    import subprocess
    import sys
    from .render.motion import ENGINES_DIR
    if name == "remotion":
        if not shutil.which("npm"):
            raise typer.BadParameter("Node.js/npm not found. Install Node 18+ (macOS: brew install node).")
        subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd=ENGINES_DIR / "remotion", check=True)
        typer.echo("Remotion installed. Add 'remotion' to render.motion in moneyhub.yaml, or use --motion remotion.\n"
                   "Remotion is free for individuals and companies of up to 3 people; see https://www.remotion.pro/license")
    elif name == "hyperframes":
        if not shutil.which("npm"):
            raise typer.BadParameter("Node.js/npm not found. HyperFrames needs Node 22+ (macOS: brew install node).")
        subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd=ENGINES_DIR / "hyperframes", check=True)
        typer.echo("HyperFrames installed (Apache-2.0). Use --motion hyperframes, or add 'hyperframes' to render.motion in moneyhub.yaml.\n"
                   "It needs Node 22+ and ffmpeg. MoneyHub switches HyperFrames' anonymous telemetry off for every render.")
    elif name == "manim":
        typer.echo("Manim needs Cairo/Pango first (macOS: brew install pango cairo pkgconf).")
        subprocess.run([sys.executable, "-m", "pip", "install", "manim"], check=True)
        typer.echo("Manim installed. Use --motion manim, or add 'manim' to render.motion.")
    else:
        raise typer.BadParameter("name must be 'remotion', 'manim' or 'hyperframes'")


@engines_app.command("test")
def engines_test(name: str = typer.Argument("pillow"), out: Path = typer.Option(Path("engine-test.mp4"))):
    """Render a small sample video with one engine to check it works."""
    from PIL import Image
    from .design import choose_style
    from .render import graphics as g
    from .render.motion import ENGINES, builtin_plan
    eng = ENGINES.get(name)
    if not eng or not eng.available():
        raise typer.BadParameter(f"engine '{name}' is not available (run: moneyhub engines status)")
    brush = g.Brush(choose_style(seed=3))
    pages = [Image.new("RGB", (800, 1000), "white")]
    plan = builtin_plan("Sample Planner", "Undated planner", ["52 weeks", "12 month views", "Goal pages", "Instant download"], "Plan the week you actually have")
    res = eng.render(plan, pages, brush, out, (1000, 1500), "Sample", 24)
    typer.echo(f"wrote {res}" if res else "render failed (re-run with -v)")
    raise typer.Exit(0 if res else 1)


@app.command()
def tools(enable: str = typer.Option(None, help="Switch these tools on for automatic checks (comma list, or 'all')"),
          disable: str = typer.Option(None, help="Switch these tools off (comma list, or 'all')"),
          master: bool = typer.Option(None, "--master/--no-master", help="Master switch for every automatic use of the craft tools"),
          verify_after_make: bool = typer.Option(None, "--verify-after-make/--no-verify-after-make",
                                                 help="Add a warn-only 'Second opinion' check to every new product"),
          outputs: str = typer.Option(None, help="Extra file kinds to build: vectors, sheets, pdfs, docx (comma list, 'all' or 'none')"),
          outputs_after_make: bool = typer.Option(None, "--outputs-after-make/--no-outputs-after-make",
                                                  help="Build the switched-on extra files automatically for every new product")):
    """Which storytold craft tools are installed, and which ones MoneyHub uses automatically (everything is off by default)."""
    from .crafttools import CHECKERS, save_settings, settings_view, status
    changes = {}
    for names, on in ((enable, True), (disable, False)):
        if names:
            for n in (CHECKERS if names.strip() == "all" else [x.strip() for x in names.split(",") if x.strip()]):
                changes[n] = on
    if changes or master is not None or verify_after_make is not None:
        try:
            save_settings(master, verify_after_make, changes)
        except ValueError as e:
            raise typer.BadParameter(str(e))
    if outputs is not None or outputs_after_make is not None:
        from . import craftbuild
        asked = [x.strip() for x in (outputs or "").split(",") if x.strip()]
        unknown = [x for x in asked if x not in (*craftbuild.KINDS, "all", "none")]
        if unknown:
            raise typer.BadParameter(f"unknown output(s): {', '.join(unknown)}. Choose from: {', '.join(craftbuild.KINDS)}, all, none", param_hint="--outputs")
        picked = {} if outputs is None else {k: ("all" in asked or k in asked) for k in craftbuild.KINDS}
        try:
            craftbuild.save_outputs(picked, outputs_after_make)
        except ValueError as e:
            raise typer.BadParameter(str(e))
    view = settings_view()
    on = {t["tool"]: t["enabled"] for t in view["tools"]}
    typer.echo(f"Craft tools: {'ON' if view['enabled'] else 'off'} (master)   verify after make: {'on' if view['verify_after_make'] else 'off'}\n")
    for t in status():
        flag = "auto " if on.get(t["tool"]) else "     "
        typer.echo(f"{'ok ' if t['path'] else '-- '}{flag}{t['tool']:<12} {t['version'] or '':<10} {t['path'] or 'not installed (scripts/install_craft_tools.sh)'}")
    if not view["enabled"]:
        typer.echo("\nOff means MoneyHub behaves exactly as before. Turn on: moneyhub tools --master --enable pdfcraft,gridcraft --verify-after-make")


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def craft(ctx: typer.Context, tool: str = typer.Argument(..., help="vectorcraft, pdfcraft, gridcraft, photocraft, wordcraft, ..."),
          timeout: float = typer.Option(300.0, help="Seconds before the tool is stopped")):
    """Run one of the craft tools with its own arguments, e.g. `moneyhub craft pdfcraft info file.pdf` (use -- before options)."""
    from .crafttools import passthrough
    r = passthrough(tool, list(ctx.args), timeout)
    if r.out:
        typer.echo(r.out, nl=not r.out.endswith("\n"))
    if r.err:
        typer.echo(r.err, err=True, nl=not r.err.endswith("\n"))
    raise typer.Exit(0 if r.ok else (r.code if r.code > 0 else 1))


@app.command()
def verify(product_id: int):
    """Second opinion: open a product's PDFs, spreadsheets and editable SVGs with the craft tools. Advisory only, never changes QA."""
    from .crafttools import verify_product, write_report
    from .store import Store
    p = Store().product(product_id)
    if not p:
        raise typer.BadParameter(f"no product #{product_id}", param_hint="product_id")
    findings = verify_product(Path(p["folder"]))
    if not findings:
        typer.echo("Nothing to check (no PDF, xlsx or editable SVG found).")
        return
    for f in findings:
        typer.echo(f"{'ok  ' if f['ok'] else 'FAIL'} {f['tool']:<11} {f['file']:<48} {f['check']}" + ("" if f["ok"] else f"  - {f['detail']}"))
    typer.echo(f"Report: {write_report(Path(p['folder']), findings)}")
    if any(not f["ok"] for f in findings):
        raise typer.Exit(1)


@app.command()
def doctor():
    """Check this machine (PDF engine, fonts, ffmpeg, AI providers, optional tools) and print how to fix gaps."""
    from . import doctor as d
    bad_required = 0
    for it in d.run():
        mark = "ok " if it.ok else ("!! " if it.required else "-- ")
        typer.echo(f"{mark}{it.name:<46} {it.detail}")
        if not it.ok and it.fix:
            typer.echo(f"      fix: {it.fix}")
        bad_required += (not it.ok and it.required)
    typer.echo("\nRequired tools OK." if not bad_required else f"\n{bad_required} required item(s) need attention.")
    raise typer.Exit(1 if bad_required else 0)


@app.command()
def ui(host: str = "127.0.0.1", port: int = 8765):
    """Open the local web UI."""
    import uvicorn
    from .web.app import app as web
    typer.echo(f"MoneyHub UI: http://{host}:{port}")
    uvicorn.run(web, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    app()
