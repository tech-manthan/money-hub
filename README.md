# MoneyHub

A local creator studio that generates **sellable digital products** - planners, habit and budget trackers, guided journals, worksheet packs, card decks - for **any niche**, together with everything you need to list them: marketplace images, SEO titles/tags/descriptions, Pinterest pins, per-marketplace upload guides, and automated quality checks. You review each product and upload it yourself (Etsy, Gumroad, Payhip, Ko-fi, Pinterest).

It is built for your own use: the quality of each product comes from a niche-aware design system + an LLM that writes niche-specific content, followed by a human review step.

## Quick start (macOS / Linux)

```bash
bash scripts/setup.sh                # installs Pango/ffmpeg via Homebrew (macOS), creates .venv, installs everything, runs `moneyhub doctor`
source .venv/bin/activate

moneyhub doctor                      # checks PDF engine, fonts, ffmpeg, AI providers; prints how to fix anything missing
moneyhub ideas --focus pets          # brainstorm niche + product ideas (hypotheses to validate)
moneyhub make "beginner knitting" weekly_planner --weeks 52
moneyhub make adhd budget_tracker --llm builtin      # offline, no AI
moneyhub make "new moms" wall_art                    # high-res print packs in 5 ratios
moneyhub batch "nurse,teacher,wedding" --products weekly_planner,guided_journal
moneyhub ui                          # web studio at http://127.0.0.1:8765
```

Manual install instead: `python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[anthropic,chromium,video,dev]"` (macOS also needs `brew install pango`).

Each run creates `out/products/<timestamp>-<niche>-<type>/`:

```
product/   the files you sell (PDFs, XLSX)
images/    etsy/ (6+ listing photos), gumroad/, payhip/, kofi/, pinterest/ (6 pins 1000x1500), video/ (MP4 pin + Etsy listing video)
listing/   listing.json, etsy title/tags/description, pins.json, guide-<marketplace>.md
spec.json  exactly what was generated (seed, style, content) - reproducible
upload-package.zip
```

## Product types
| Key | Output |
|---|---|
| `weekly_planner` | Undated planner: cover, goals, 12 month views, up to 60 weekly spreads, notes. Letter / A4 / A5 printable + hyperlinked landscape tablet version (GoodNotes, Notability) |
| `habit_tracker` | Excel/Sheets workbook (checkboxes, auto %, chart) + 12 printable months |
| `budget_tracker` | Excel/Sheets workbook (transactions, budget vs actual, savings, debt, dashboard charts) + printable budget pages |
| `guided_journal` | 30 daily prompt pages, gratitude/mood/step boxes, weekly check-ins |
| `worksheet_pack` | Worksheets with directions + answer key (math/language for teachers; reflective exercises otherwise) |
| `card_deck` | Affirmation/prompt/action cards, 9 per sheet with cut guides |
| `daily_planner` | Undated one-page-per-day planner: hourly schedule, top 3, to-do, niche boxes |
| `checklist_pack` | Bundle of niche-specific tick-box checklists |
| `ebook_guide` | Short printable guide: chapters, key points, action steps (best with an LLM; review facts before selling) |
| `wall_art` | Typographic posters with procedural artwork (optional AI backgrounds) as 300-DPI-class JPG packs in 5 ratios (2:3, 3:4, 4:5, 5:7, ISO A) plus a framed gallery-wall listing photo |

Adding a product type = one module in `src/moneyhub/products/` with a content model, an offline builder, an LLM brief and a `build()`.

## Research helpers
- `moneyhub ideas` / the **Ideas** page: LLM-brainstormed niche + product combos with the search phrases to validate on Etsy and Pinterest.
- Unknown niches are **researched by the LLM into a full profile** (cached in `out/niches/`), so "wheelchair users travel" gets real, specific content instead of a generic template. `moneyhub niche "<text>" --research` shows the profile.

## Motion, art and previews
- **Videos:** every product gets a 1000x1500 MP4 for Pinterest video pins and a 1920x1080 listing video. An LLM writes the scene plan (hook, page, benefits, call to action); a Pillow + ffmpeg renderer animates it. Needs ffmpeg (`brew install ffmpeg` or `pip install imageio-ffmpeg`). Skip with `--no-video`.
- **AI art (optional, off by default):** set a key (`HF_TOKEN`, `TOGETHER_API_KEY`, `OPENAI_API_KEY`) or `MONEYHUB_ART_URL` for a local server, list the provider under `render.art` in `moneyhub.yaml`, then use `--ai-art` for wall art backgrounds. Check each provider's terms before selling generated images. Default artwork is procedural SVG (no licence questions).
- **Spreadsheet previews:** habit and budget trackers get an illustrated spreadsheet-window listing photo with sample numbers. Replace it with real screenshots of your finished workbook when you can.

## AI providers (all optional)
Configured per task in `moneyhub.yaml`; each task tries providers in order and falls back automatically:

`claude_cli` (`claude -p`) → `anthropic` (API) → `gemini` / `groq` / `openrouter` (free tiers) → `ollama` (local) → `builtin` (offline library).

Set keys as environment variables (`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`). Copy `moneyhub.yaml` to `moneyhub.local.yaml` to override. PDF renderers are also pluggable (`weasyprint`, `chromium`).

## Quality & uniqueness
Every build runs automated checks: colour contrast, page counts, file sizes (Etsy 20 MB limit), fonts embedded, blank pages, internal links for the tablet planner, spreadsheet structure and (when LibreOffice is installed) formula recalculation. Each product is fingerprinted and compared with your catalogue so you are warned before making a near-duplicate. Seeds drive palette, font pairing, header style and cover layout, so the same niche + type looks different each time.

## Learn what sells
In the UI, record where you listed each product, views, favourites and sales (or `moneyhub listed|sale|report`). "Sales & learning" ranks products so you can make more of the niche/type/style that works.

## Rules to respect
- Etsy requires disclosing AI-assisted designs in the listing description; the generated description includes it.
- Fonts are Google Fonts (SIL OFL): embedded in PDFs, never included as files. Don't add third-party images/fonts to products without a commercial licence.
- Pinterest: review and post pins yourself; don't spam identical pins.

See `docs/research.md` for the research behind the design.

## Development
```bash
pytest          # ~3 min; content validity for every niche x product, LLM fallback and research, pipeline, wall-art packs, video, UI, spreadsheets
```
