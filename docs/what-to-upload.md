# What to upload where

MoneyHub never publishes for you. For every product it prepares a **pack per platform**:

```
moneyhub export pack <id> etsy        # or gumroad, payhip, kofi
```

Each pack is one zip with three folders: `1-DOWNLOAD` (the files buyers receive), `2-LISTING-IMAGES` (photos in upload order) and `3-LISTING-TEXT` (step-by-step guide, title, description, tags, price). Upload them in that order. Files that do not fit a platform's limits are grouped into zips or flagged in the pack's README.

Limits MoneyHub checks (confirm them on the platform, they change): Etsy 5 files, 20 MB each, 100 MB in total; Gumroad 16 GB per file (free items 25 MB); Payhip 5 GB per file; Ko-fi about 1 GB per file.

## By platform

| Platform | Upload as the buyer's download | Listing photos | Text |
|---|---|---|---|
| **Etsy** | The `1-DOWNLOAD` files (max 5) | `images/etsy/` in numbered order (10 max) + the 1920 x 1080 listing video if you made it | Title, 13 tags and description from `guide-etsy.md`, including the AI disclosure line |
| **Gumroad** | The same files (no count limit) | `cover-1280x720.png` and `thumbnail-600x600.png` | `guide-gumroad.md` |
| **Payhip** | The same files | `cover-1600x1067.png` | `guide-payhip.md` |
| **Ko-fi** | The same files | `square-1000x1000.png` | `guide-kofi.md` |
| **Pinterest** | Nothing (it sends visitors to your listing) | The 1000 x 1500 pins in `images/pinterest/` and the pin video | `guide-pinterest.md` |
| **Amazon KDP** | Only for print-book types: `moneyhub export kdp <id>` | Cover made by the export | Follow the export's notes |
| **Canva / Notion** | Only if you sell a template link or import: `moneyhub export canva|notion <id>` | n/a | n/a |

Only the platform's own requirements matter: **no platform requires an editable format** (no PSD, no Word). Editable files are an optional extra that some buyers like.

## By product type: what the buyer should receive

| Product type | Download files | Optional extras (off by default, `moneyhub export craft <id>`) |
|---|---|---|
| Planners, journals, worksheets, checklists, cards, classroom, schedules, workbooks, activity books | PDF (Letter, A4, tablet or e-ink as chosen) + Start-Here | `docx` for guide, worksheet, checklist and journal text; PDF title/author |
| Budget and habit trackers | `.xlsx` + PDF print version + Start-Here | CSV/HTML copy of every sheet |
| Wall art | JPG zips in each print ratio + READ-ME | AI, EPS, PDF and layered PSD copies of the designs (rarely asked for) |
| Clipart, character clipart, icon packs, stickers | Transparent PNG and SVG zips + licence PDF (+ printable sheets) | none needed |
| Digital paper | JPG papers zip + licence PDF | none needed |
| Cut files | SVG, DXF, EPS and PNG zip + licence PDF | none needed |
| Coloring pages, kids coloring, oracle decks | PDF (+ KDP interior for coloring) | none needed |
| **Presentation templates** | **`.pptx` (12 slides) + PDF preview + Editing-Guide-and-License PDF** (3 files) | none needed |

## Presentation templates

`moneyhub make "x" presentation_template` (needs the `deckcraft` tool installed with `scripts/install_craft_tools.sh`; the craft on/off switches are not needed). The deck has 12 widescreen slides (title, agenda, section, two columns, quote, key numbers, process, image gallery, before and after, team, pricing, thank you), all plain text boxes and shapes in the product's palette and font pair. Fonts are free Google Fonts and are **not** included: the Editing guide names them.

Upload to Etsy, Gumroad, Payhip or Ko-fi the same three files from `1-DOWNLOAD`. Listing photos show the slides in overview sheets and in desk and tablet scenes. The Etsy guide asks you to copy the category of similar best-selling slide-deck listings, because MoneyHub cannot know Etsy's current category tree.

Not yet checked on real apps: opening the `.pptx` in PowerPoint, Keynote and Google Slides (fonts, spacing), and whether Google Slides keeps the shape text sizes.
