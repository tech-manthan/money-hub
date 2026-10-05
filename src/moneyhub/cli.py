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
    for noisy in ("fontTools", "weasyprint", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


@app.command()
def make(
    niche: str = typer.Argument(..., help="Any niche, e.g. 'ADHD', 'nurse', 'dog training'"),
    product: str = typer.Argument("weekly_planner", help="weekly_planner | habit_tracker | budget_tracker | guided_journal | worksheet_pack | card_deck"),
    sizes: str = typer.Option(None, help="Comma list: letter,a4,a5,tablet"),
    seed: int = typer.Option(None, help="Reuse a seed to reproduce a look"),
    palette: str = typer.Option(None, help=f"One of: {', '.join(palette_keys())}"),
    llm: str = typer.Option(None, help="Provider chain override, e.g. 'claude_cli,builtin' or 'builtin'"),
    weeks: int = typer.Option(None, help="Weekly planner: number of weeks (4-60)"),
    no_images: bool = typer.Option(False, help="Skip listing images/pins"),
):
    """Generate one product with its images, listing copy and upload guides."""
    opts = {"weeks": weeks} if weeks else {}
    req = Request(niche=niche, product_type=product, sizes=_csv(sizes), seed=seed, palette=palette,
                  providers=_csv(llm), options=opts, with_images=not no_images)
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
def niche(text: str):
    """Show the profile the system will use for a niche."""
    typer.echo(resolve_niche(text).model_dump_json(indent=2))


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


@app.command()
def ui(host: str = "127.0.0.1", port: int = 8765):
    """Open the local web UI."""
    import uvicorn
    from .web.app import app as web
    typer.echo(f"MoneyHub UI: http://{host}:{port}")
    uvicorn.run(web, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    app()
