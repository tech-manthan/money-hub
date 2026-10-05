# Research notes (Oct 2026)

Summary of the market and platform research behind MoneyHub. Prices/limits change, so re-check before relying on them.

## What sells
- Templates, planners and printables dominate Etsy/Gumroad digital products (70-90% margins). Trending niches: ADHD/neurodivergent planners, budget trackers, guided journals, wedding suites, affirmation/prompt cards, homeschool packs, kids printables.
- Generic AI output is saturated; specificity and lived expertise win (nurse, ADHD, specific hobbies). Validate demand with real listings before scaling.
- Spreadsheet products (budget/habit trackers) command higher prices than single printables; hyperlinked tablet planners ($10-$25) more than plain PDFs ($3-$10).

## Marketplace constraints that shaped the design
| Platform | Facts used |
|---|---|
| Etsy | Digital listings: up to 5 files, 20 MB each; up to 10 images (>= 2000 px shortest side; 4:3 recommended); 13 tags; AI-assisted designs must be disclosed in the listing description; selling AI prompts as the deliverable is prohibited. Fees: $0.20 listing + 6.5% transaction. |
| Gumroad | No product-creation API (creation is manual). Cover 1280x720, thumbnail 600x600 (cropped from centre). 10% fee (30% via Discover). |
| Payhip | Up to 9 images, min 1000 px wide, aspect ratio matters; free plan 5% fee. |
| Ko-fi | 0% platform fee on shop sales (processor fees apply). |
| Pinterest | Pins 1000x1500 (2:3), title <= 100, description <= 500. The API starts in trial mode and its guidelines expect a person to review each action, so MoneyHub prepares pins and you post them. |

## Tools chosen (all open source)
WeasyPrint (PDF), Playwright/Chromium (optional alternate PDF renderer), XlsxWriter + openpyxl (spreadsheets), Pillow (graphics), pypdfium2 (page previews), pypdf (QA), Jinja2, FastAPI, Typer, Pydantic. Fonts: Google Fonts under the SIL OFL (embedded, never redistributed as files). All artwork is generated procedurally, so there are no third-party image licences inside the products.

## LLM options
`claude -p` (Claude Code headless), Anthropic API, Gemini/Groq/OpenRouter free tiers, Ollama (local), plus an offline builtin library. Every task has its own ordered chain with automatic fallback (see `moneyhub.yaml`). Note: Anthropic has been scoping subscription usage to first-party Claude Code; use an API key if you ever wrap this in something you sell to others.

## Not yet built / ideas
- Real spreadsheet screenshots for mockups (needs Excel/LibreOffice rendering on your machine).
- Remotion/Manim motion graphics for video pins.
- Optional AI art provider (cloud image API) for wall-art products.
- Penpot/Open Design as a visual editing step.
