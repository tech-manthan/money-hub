"""moneyhub command line."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import typer

from .config import get_config
from .design import palette_keys
from .niches import library_keys, resolve_niche
from .pipeline import Request, generate, make_package
from .products import all_product_types
from .store import Store

app = typer.Typer(help="MoneyHub - generate sellable digital products and listing kits.", no_args_is_help=True)


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
    sizes: str = typer.Option(None, help="Comma list: letter,a4,a5,tablet"),
    seed: int = typer.Option(None, help="Reuse a seed to reproduce a look"),
    palette: str = typer.Option(None, help=f"One of: {', '.join(palette_keys())}"),
    llm: str = typer.Option(None, help="Provider chain override, e.g. 'claude_cli,builtin' or 'builtin'"),
    weeks: int = typer.Option(None, help="Weekly planner: number of weeks (4-60)"),
    no_images: bool = typer.Option(False, help="Skip listing images/pins"),
    no_video: bool = typer.Option(False, help="Skip the MP4 pin / listing video"),
    motion: str = typer.Option(None, help="Video engine chain, e.g. 'remotion,pillow' (engines: pillow, remotion, manim)"),
    ai_art: bool = typer.Option(False, help="Wall art: use the AI image providers configured in render.art for backgrounds"),
    days: int = typer.Option(None, help="Daily planner: number of pages (7-120)"),
    no_research: bool = typer.Option(False, help="Do not use an LLM to research unknown niches"),
):
    """Generate one product with its images, listing copy and upload guides."""
    opts = {k: v for k, v in {"weeks": weeks, "days": days, "ai_art": ai_art or None, "no_research": no_research or None}.items() if v}
    req = Request(niche=niche, product_type=product, sizes=_csv(sizes), seed=seed, palette=palette,
                  providers=_csv(llm), options=opts, with_images=not no_images, with_video=not no_video, motion=_csv(motion))
    res = generate(req, progress=lambda m: typer.echo(f"  - {m}"))
    typer.echo(f"\n{res.title}  [{res.qa_status.upper()}]")
    typer.echo(f"Folder: {res.folder}")
    typer.echo(f"Upload package: {res.folder / 'upload-package.zip'}")
    for c in res.checks:
        if c.status != "pass":
            typer.echo(f"  {c.status.upper()}: {c.name} - {c.detail}")


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


engines_app = typer.Typer(help="Optional video engines: remotion (React) and manim (Python).", no_args_is_help=True)
app.add_typer(engines_app, name="engines")


@engines_app.command("status")
def engines_status():
    """Which video engines are ready."""
    from .render.motion import engine_status
    for e in engine_status():
        typer.echo(f"{'ok ' if e['available'] else '-- '}{e['name']:<9} {'(in chain)' if e['enabled'] else '          '} {e['note']}")


@engines_app.command("install")
def engines_install(name: str = typer.Argument(..., help="remotion | manim")):
    """Install an optional engine (remotion: npm install in engines/remotion; manim: pip install manim)."""
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
    elif name == "manim":
        typer.echo("Manim needs Cairo/Pango first (macOS: brew install pango cairo pkg-config).")
        subprocess.run([sys.executable, "-m", "pip", "install", "manim"], check=True)
        typer.echo("Manim installed. Use --motion manim, or add 'manim' to render.motion.")
    else:
        raise typer.BadParameter("name must be 'remotion' or 'manim'")


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
