# Visual editing with Penpot (or Open Design)

MoneyHub generates images automatically, but you can touch them up by hand. The export gives you **layered SVGs** (live text, separate image layers, named shapes) that open in Penpot, Inkscape, Figma or any browser.

## 1. Export
```bash
moneyhub edit export <product-id>      # or "Export editable files" on the product page in the UI
```
Creates `<product>/editable/` with
- `pins/pin-01..06.svg` (1000x1500 Pinterest pins)
- `listing/01-hero.svg` (2700x2025 Etsy hero image)
- `posters/design-NN.svg` (wall art posters, when the product is wall art)
- `fonts/` (the fonts used, SIL OFL - for editing only, never include them in what you sell)
- `BRIEF.md` (palette, fonts, copy, safe areas, file list)
- `edited/` (put your exports here)

## 2. Edit in Penpot (free, open source)
Option A, hosted: sign up at penpot.app. Option B, on your Mac with Docker:
```bash
bash editor/penpot/run.sh          # downloads Penpot's official compose file and starts it on http://localhost:9001
```
1. Create a project, then **drag the SVG files onto the canvas** (Penpot imports SVG as editable shapes; text stays text).
2. Install/upload the fonts from `editable/fonts/` (Penpot: team settings -> Fonts). If a font is missing Penpot substitutes one, so check the text.
3. Edit headlines, colours, positions. Keep important text out of the bottom third of pins.
4. Select each frame/board and **export PNG/JPG with the same file name as the SVG** (`pin-01.png`, `01-hero.jpg`) into `editable/edited/`. Sizes are adjusted automatically on import, but keep the same aspect ratio.

## 3. Import
```bash
moneyhub edit import <product-id>          # or upload the files on the product page
```
Matching images are replaced (originals saved in `images/_original/`) and `upload-package.zip` is rebuilt. File-name rules: `pin-01.png` -> Pinterest pin 1, `01-hero.jpg` (or any `NN-name` of an Etsy image), `gumroad-cover.png`, `gumroad-thumbnail.png`, `payhip-cover.png`, `kofi-square.png`.

## Using an AI design agent instead
- **Open Design** (Apache-2.0, local-first, works with Claude Code, Codex and other coding agents): install from https://github.com/nexu-io/open-design, point it at `editable/BRIEF.md` and the SVGs, and ask for variants (new headline treatments, a seasonal colourway). Export PNGs with the same names and run `moneyhub edit import`.
- **Claude Code + a Penpot MCP server:** community MCP servers let an agent read and change Penpot files and export frames (for example Penpot's own MCP server; see https://penpot.app/ai/mcp-server). Then you can say "make all six pins more playful" and review in Penpot. Treat third-party MCP servers like any other software: read what they do before connecting them to your files.

## Limits
- Posters export at a 4:5 ratio. For the other print ratios, re-export from the generator (the packs are made from the same designs) or resize in Penpot.
- Spreadsheet screenshots are not editable SVGs; replace them with real screenshots.
