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
- **WeasyPrint + CSS grid**: a `display:grid` page containing nested flex tables can intermittently take ~15 minutes to lay out (same input, random run). The budget pages use flex rows for that reason; prefer flex for anything that holds `.tbl` tables. After code changes, restart `moneyhub ui` (a running UI keeps old Python but reads new templates, which gives 500 errors).
- **Guided UI**: `/` landing, `/make` 3-step wizard (`web/templates/start.html`, `web/static/start.js`), `/docs` user guide, `/settings` keys. Everything in the UI is also a CLI flag; keep them in step (`moneyhub styles` lists the options).
- **Page layouts**: `layouts.py` holds layout specs (weekly, daily). Presets + `auto:N` generated + AI "described" layouts. To give another product type layouts: add a spec model/presets/random generator there, read `spec` in its template, set `layouts`, `auto_layout`, `layout_marker` on the class, and add a fit check like `weekly_planner.py`.
- **Keys**: `keystore.py` writes a git-ignored `.env` (0600); never put keys in yaml or code. Settings endpoints are local-only (Host/Origin checked).
- **Exports**: `exports/` has kdp, notion, canva (`moneyhub export ...`). KDP numbers (gutter, paper thickness, bleed) come from KDP's help pages; confirm them before relying on them.
- **Video engines** (`render/motion.py`): pillow (default), remotion, manim, hyperframes. HyperFrames telemetry is switched off in code.
- **Recording the tour**: `python scripts/record_tour.py` re-makes `web/static/media/*.mp4` from the real UI (offline, temp data, natural voice if installed). Re-run it when the wizard changes.
- Tests: ~290, about 4 minutes (`pytest -q`). CI is `.github/workflows/ci.yml` (not yet run on GitHub).

## Known gaps (not verified on a real Mac / device yet)
Penpot SVG import, live image-AI providers (Hugging Face, Together, OpenAI; `claude_svg` works), how exports behave inside Canva/Notion/KDP's previewer, GoodNotes link behaviour, e-ink tablets, xlsx recalculation in Excel/Numbers. Not built: marketplace API publishing (by design), KDP export for non-planner products, layouts for product types other than weekly/daily planner, Penpot/Canva native template files.

- **New since the pending list**: `clipart_pack` (transparent PNG + SVG + licence PDF) and `digital_paper` (seamless 12 x 12 in JPG papers from `patterns.py`), `coloring_pages` (`coloring.py` line art; KDP-ready), `cut_files` (`cutfiles.py` geometry, SVG/DXF/EPS/PNG) products, room mockups for wall-art listings (`render/mockups.py`), listed without the niche word (`niche_in_copy = False`, `_generic_copy` in `listing/kit.py`), wall-art formats `1x1`/`phone`/`frame_tv`, product-page file viewer and Sell-on platform packs (`listing/platforms.py`, `moneyhub export pack <id> etsy`), research in `docs/art-formats.md`. Product types can set `license_terms`/`license_faq`/`how_steps` to change the listing's licence wording.

- **Niche-free listings**: `ProductType.niche_in_copy = False` (+ `copy_audience`, `title_suffix`) makes `listing/kit.py` use `_generic_copy` and leave the niche out of the title, tags and LLM prompt. Used by clipart, digital paper, coloring pages, cut files, kids coloring, sticker sheets and oracle decks. Every such type needs a `_TYPE_WORDS` entry (a test enforces it).

- **Added Oct 2026**: `kids_coloring` (`kidsart.py`), `sticker_sheets` (`stickers.py`), `oracle_deck` (`oracle_art.py`; tarot-style or oracle); in-use mockups for every product family (`render/mockups.py`: `product_scene`, `scenes_for`; products put single designs in `meta["mockup_tiles"]`); niche-free products use design fingerprints and "Vol. N" titles (`ProductType.unique_title`/`fingerprint`); cut files have a round-trip check (`cutfiles.validate_exports`, QA "Opens in cutting software") and the DXF declares inches. Options added to the CLI and UI: `--pages`, `--theme`, `--age`, `--stickers`, `--deck`, `--card-size`, `--cards`. Inkscape (brew cask) is installed on the dev Mac; one test renders a cut SVG with it and skips if it is missing.

## Newer products and tooling (24 product types)
- Added since the first list: `activity_book` (`activities.py`: mazes with answers, dot-to-dot, tracing, odd-one-out), `learning_workbook` (`learning.py`: 10 worksheet types, 6 focuses, bilingual), `character_clipart`, `icon_pack`, `montessori_cards` (three-part cards), `classroom_pack` (name tags, desk plates, charts, calendar; `--names`), `visual_schedule` (`schedules.py` pictograms + feelings faces; boards and cards with hook-and-loop dot guides; never write the trademark "Velcro" in listing text). Kids art lives in `kidsart.py` + `kidsart_extra.py` (80 figures, 26 themes).
- **Translations** (`translations.py`): es/fr/de word lists are guarded. QA fails until `moneyhub translations check` (AI proofread) and a human `moneyhub translations approve`. New translated words go in `translations.py` only.
- **SVG assets** (`svgassets.py`, `moneyhub assets ...`): licence-checked Tabler/Lucide fetcher plus your own folder. Accepts MIT/ISC/Apache/CC0/PD/CC-BY 4.0; refuses CC-BY-SA, NC, GPL. Wall art can use `icon:<set>` motifs; `docs/licenses.md` has the detail.
- **Mockups** (`render/mockups.py`): in-use scenes for every family (`FAMILIES`); products put single designs in `meta["mockup_tiles"]` via `mockups.save_tiles`.
- **Platform packs** (`listing/platforms.py`): Etsy/Gumroad/Payhip/Ko-fi zips via `moneyhub export pack <id> <platform>`.
- **Craft tool switches**: `craft:` in `moneyhub.yaml` (master `enabled`, `verify_after_make`, per-tool `tools:`; ALL off by default). Change them in Settings (`/settings`), with `moneyhub tools --master --enable pdfcraft,gridcraft --verify-after-make`, or in `moneyhub.local.yaml`. When off, no tool is ever started and generation is unchanged; when on, `crafttools.second_opinion` adds one warn-only QA line and swallows every error. A tool that is switched off is never executed.
- **Craft tools** (`crafttools.py`, `scripts/install_craft_tools.sh`, installed into git-ignored `tools/craft/`): third-party storytold CLIs (vectorcraft, pdfcraft, gridcraft, photocraft, wordcraft, deckcraft, soundcraft, cadcraft, plus lightcraft/designcraft/effectcraft/filmcraft). `moneyhub tools` lists them, `moneyhub verify <id>` opens a product's PDFs, xlsx, editable SVGs, listing images and DXFs with the matching tool and writes `craft-verify.json` (advisory, never part of the QA gate), `moneyhub craft <tool> ...` runs any of them. Verified on real products: pdfcraft, gridcraft, photocraft, cadcraft and vectorcraft open our files. gridcraft opening an xlsx is not proof that Excel or Numbers recalculate it, and these are unaudited programs: Claude Code's permission check blocks running them, so the owner runs them with `!`.
- **PDFium is not thread-safe**: `render/pdfium_safe.py` (installed from `moneyhub/__init__.py`) puts one lock around every pypdfium2 call. Without it the UI crashed (trace trap / bus error) when a product page loaded many previews at once. Keep PDF rendering going through pypdfium2 so the lock applies.
- A failed generation now removes its folder (`pipeline.generate`), so no empty folders appear in `out/products`.
- Tests: ~565, about 8 minutes. Use `pytest -q --basetemp=<scratch dir>` and delete it afterwards; the data volume runs near full. The HyperFrames render test skips below 1 GB free disk.

## New product type checklist
1. `products/<key>.py` subclass, `@register`, import in `products/registry.py` `_load_all`; templates in `products/templates/` (reuse `coloring.html.j2` or `oracle.html.j2`/`montessori.html.j2`).
2. Niche-free products: `niche_in_copy = False`, `copy_audience`, `title_suffix`, `how_steps`, `self.unique_title(ctx, name)`.
3. `listing/kit.py` `_TYPE_WORDS`, `web/guide.py` entry, `exports/kdp.py` SUPPORTED / `web/app.py` `pdf_types` for print books, `render/mockups.py` FAMILIES.
4. CLI option in `cli.py make()`, web field in `web/app.py create_job` + `start.html` + `start.js` (+ classic `index.html`/`app.js`); validate in both CLI and web.
5. Tests in `tests/test_art_formats.py`, docs in `docs/art-formats.md`, re-run `scripts/record_tour.py` if the wizard changed.

## Pending work (start here in a new session)
Commit each with tests; no pushes unless the owner asks (~40 commits are local).
1. ~~Classroom printables~~ done. 2. ~~Visual schedules~~ done. 3. ~~More learning niches~~ done as `learning_workbook` focuses (`handwriting`, `cursive`, `sightwords --grade`, `stem`; English only; `handwriting.py`). 4. ~~Seasonal bundles~~ and 5. ~~starter kit + `make-many`~~ done in `bundles.py` (`moneyhub bundle <theme|niche|ids>`, `moneyhub make-many`; CLI only, no UI form). 6. ~~Print-then-cut~~ done (`--print-then-cut`, `stickers.cut_paths`; needs a real-machine check). 7. ~~Cross-type uniqueness warning~~ done (`uniqueness.content_signature`; only stickers and Montessori record figures). 8. ~~Cut files from kids figures~~ done (`cut_files --figures`, raster silhouette in `cutfiles.figure_silhouette`, no shapely).
Owner-side checks (needs the owner, see `docs/owner-verification.md`): Notion/Canva/KDP imports, e-ink devices, GoodNotes links, xlsx in Excel/Numbers, test cuts, paper printing, a native speaker approving translations, image-AI provider keys, Penpot import, pushing the branch so CI runs.
