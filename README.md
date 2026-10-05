# MoneyHub

A local creator studio that generates **sellable digital products** - planners, habit and budget trackers, guided journals, worksheet packs, card decks - for **any niche**, together with everything you need to list them: marketplace images, SEO titles/tags/descriptions, Pinterest pins, per-marketplace upload guides, and automated quality checks. You review each product and upload it yourself (Etsy, Gumroad, Payhip, Ko-fi, Pinterest).

It is built for your own use: the quality of each product comes from a niche-aware design system + an LLM that writes niche-specific content, followed by a human review step.

## Quick start (macOS / Linux)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[anthropic,chromium,dev]"
# macOS: WeasyPrint needs Pango:  brew install pango

moneyhub types                       # product types, niches, which AI providers are ready
moneyhub make "beginner knitting" weekly_planner --weeks 52
moneyhub make adhd budget_tracker --llm builtin      # offline, no AI
moneyhub batch "nurse,teacher,wedding" --products weekly_planner,guided_journal
moneyhub ui                          # web UI at http://127.0.0.1:8765
```

Each run creates `out/products/<timestamp>-<niche>-<type>/`:

```
product/   the files you sell (PDFs, XLSX)
images/    etsy/ (6 listing photos), gumroad/, payhip/, kofi/, pinterest/ (6 pins 1000x1500)
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

Adding a product type = one module in `src/moneyhub/products/` with a content model, an offline builder, an LLM brief and a `build()`.

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
pytest          # ~50 s; covers content validity for every niche x product, LLM fallback, pipeline, UI, spreadsheets
```
