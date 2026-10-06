# MoneyHub - notes for Claude Code (read this first)

Local creator tool: generates sellable digital products (planners, trackers, journals, worksheets, cards, wall art, ebooks), listing kits, Pinterest pins, launch videos. The owner uploads manually; there is no marketplace publishing by design.

## Run it (macOS M4 / Linux)
```
bash scripts/setup.sh && source .venv/bin/activate
moneyhub doctor            # fix whatever it reports first
pytest -q                  # ~3.5 min; expect 230ish passed, 1 skipped
moneyhub make "nurse" weekly_planner --llm builtin   # offline smoke test
moneyhub ui
```
`claude -p` is the default LLM; `--llm builtin` forces offline. Config: `moneyhub.yaml` (provider chains per task: content, listing, research, motion).

## Layout
- `src/moneyhub/products/` generators (+ `templates/*.j2`), `listing/` kit + marketplace guides, `render/` (WeasyPrint/Playwright PDF, Pillow graphics, motion engines), `brag/` launch videos, `qa.py`, `risk.py`, `growth.py`, `cli.py`, `web/`.
- `engines/` optional Remotion/Manim, `editor/penpot/`, `docs/` (research, licenses, brag.md, editing.md).

## Conventions
- Python 3.11+, Typer CLI, Pydantic models, pytest in `tests/`. Match surrounding style; keep comments sparse.
- New product type: subclass in `products/`, register in `registry`, add `_TYPE_WORDS` entry in `listing/kit.py` (a test enforces it), add tests.
- Generated output goes to `out/` (not committed). Never commit API keys.
- Marketplace rules matter: Etsy AI disclosure line in descriptions, no trademarked/brand terms (see `risk.py`), Pinterest text outside the bottom 20% safe zone, QA must pass before a product is "ready".
- No PRs or pushes unless the owner asks.

## Known gaps (not verified on a real Mac yet)
Etsy video/photo limits (could not reach etsy.com), Penpot SVG import, live AI-art providers, xlsx recalculation in Excel/Numbers, GoodNotes link behaviour, Kokoro voice install on Mac. Not built: marketplace API publishing, KDP export, HyperFrames engine, e-ink planner variants, Canva/Notion files, spell-check QA. If something breaks on the Mac, fix it and add a test.
