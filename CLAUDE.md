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

## More things to know
- **Guided UI**: `/` landing, `/make` 3-step wizard (`web/templates/start.html`, `web/static/start.js`), `/docs` user guide, `/settings` keys. Everything in the UI is also a CLI flag; keep them in step (`moneyhub styles` lists the options).
- **Page layouts**: `layouts.py` holds layout specs (weekly, daily). Presets + `auto:N` generated + AI "described" layouts. To give another product type layouts: add a spec model/presets/random generator there, read `spec` in its template, set `layouts`, `auto_layout`, `layout_marker` on the class, and add a fit check like `weekly_planner.py`.
- **Keys**: `keystore.py` writes a git-ignored `.env` (0600); never put keys in yaml or code. Settings endpoints are local-only (Host/Origin checked).
- **Exports**: `exports/` has kdp, notion, canva (`moneyhub export ...`). KDP numbers (gutter, paper thickness, bleed) come from KDP's help pages; confirm them before relying on them.
- **Video engines** (`render/motion.py`): pillow (default), remotion, manim, hyperframes. HyperFrames telemetry is switched off in code.
- **Recording the tour**: `python scripts/record_tour.py` re-makes `web/static/media/*.mp4` from the real UI (offline, temp data, natural voice if installed). Re-run it when the wizard changes.
- Tests: ~290, about 4 minutes (`pytest -q`). CI is `.github/workflows/ci.yml` (not yet run on GitHub).

## Known gaps (not verified on a real Mac / device yet)
Penpot SVG import, live image-AI providers (Hugging Face, Together, OpenAI; `claude_svg` works), how exports behave inside Canva/Notion/KDP's previewer, GoodNotes link behaviour, e-ink tablets, xlsx recalculation in Excel/Numbers. Not built: marketplace API publishing (by design), KDP export for non-planner products, layouts for product types other than weekly/daily planner, Penpot/Canva native template files.

## Pending work (start here in a new session)
Do these in order; commit each with tests; no pushes unless the owner asks (3+ commits are local and unpushed at the time of writing).
1. ~~Wall-art motifs~~ done (scallop/topo/bouquet/retro redrawn; test covers every motif).
2. ~~Wall-art page layouts~~ done: `WallArtSpec` in `layouts.py` (presets stacked/headline/framed/poster/divided + `mixed`, `auto:N`, described); `art_boxes()` is the one geometry source for the page template and the editable SVG; `--layout 0-4` is a hidden alias for the first five presets. Default is now `stacked` (was mixed).
3. **Layouts for the other product types** (habit tracker print pages, journal, checklist pack, worksheet pack, card deck, ebook guide, budget print pages): spec model + presets + generator + fit check each, following `weekly_planner.py`.
4. **KDP export for more products** (checklists/worksheets already supported; add card deck as a printed deck is not a KDP product, so skip; consider journal/guide cover polish and a real cover image option).
5. **Verify on real platforms** (needs the owner): import the Notion zip into Notion, the Canva PDF into Canva, the KDP interior/cover in KDP's previewer, the e-ink PDFs on a device, GoodNotes links, xlsx in Excel/Numbers. Fix what breaks and add tests.
6. **CI**: push the branch (owner's call) and fix whatever the GitHub macOS/Linux matrix reports.
7. **Image-AI providers** (Hugging Face / Together / OpenAI) are untested: needs a key from the owner; test via Settings > Test, then a wall-art build with `--art-provider huggingface`.
8. **Penpot**: try importing an `editable/*.svg` into a real Penpot and fix import problems.
9. After UI changes, re-run `python scripts/record_tour.py` (about 6 minutes) and re-run the full test suite.
