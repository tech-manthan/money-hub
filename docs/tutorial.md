# MoneyHub: the complete tutorial

This is the long guide. It covers every page of the app, every product type and option, every command, the optional tools, the selling workflow and the things that still need a real device. Read it top to bottom once, then use the table of contents as a reference.

The short version lives in the app at `/docs`. This file goes deeper and is the one to keep open while you work.

**Contents**

1. [What MoneyHub is (and is not)](#1-what-moneyhub-is-and-is-not)
2. [Install and first run](#2-install-and-first-run)
3. [The ideas behind it: niche, product type, look](#3-the-ideas-behind-it)
4. [Your audience: does the niche apply to every product?](#4-your-audience-does-the-niche-apply-to-every-product)
5. [The web app, page by page](#5-the-web-app-page-by-page)
6. [Every product type](#6-every-product-type)
7. [Looks, layouts, e-ink and brand colour](#7-looks-layouts-e-ink-and-brand-colour)
8. [What is inside a finished product](#8-what-is-inside-a-finished-product)
9. [Quality checks (QA) explained](#9-quality-checks-qa-explained)
10. [The listing kit and marketplace rules](#10-the-listing-kit-and-marketplace-rules)
11. [What to upload on each platform](#11-what-to-upload-on-each-platform)
12. [Images, pins and videos](#12-images-pins-and-videos)
13. [Editing the art yourself](#13-editing-the-art-yourself)
14. [Exports: KDP, Notion, Canva, platform packs](#14-exports)
15. [Working at scale: variations, bundles, batches, samples](#15-working-at-scale)
16. [Learning what sells](#16-learning-what-sells)
17. [AI services and keys](#17-ai-services-and-keys)
18. [The optional craft tools](#18-the-optional-craft-tools)
19. [Video engines and voices](#19-video-engines-and-voices)
20. [Icons and licences (assets)](#20-icons-and-licences)
21. [Translations guardrail](#21-translations-guardrail)
22. [Configuration files and folders](#22-configuration-files-and-folders)
23. [Command reference](#23-command-reference)
24. [Step-by-step recipes](#24-step-by-step-recipes)
25. [Troubleshooting](#25-troubleshooting)
26. [What still needs a real device or app](#26-what-still-needs-a-real-device-or-app)
27. [Glossary](#27-glossary)
28. [The video tutorials](#28-the-video-tutorials)

---

## 1. What MoneyHub is (and is not)

MoneyHub is a **local tool that runs on your own computer**. You tell it who you want to help and what to make; it builds the finished digital product, the pictures for the listing, the listing text, the Pinterest pins, a short video and a ready-to-upload package.

It makes: printable planners, trackers, journals, worksheets, cards, wall art, e-books, clipart, digital paper, cut files, coloring books, stickers, oracle decks, kids learning material, classroom printables, visual schedules and editable slide templates.

It does **not**:

- publish to Etsy, Gumroad, Payhip, Ko-fi or Pinterest. You upload by hand, on purpose. This keeps your accounts safe and your decisions yours.
- promise sales. Nothing can. The research parts are hypotheses; you test them in the real search boxes.
- send your products anywhere. Everything is written to the `out/` folder on your machine. The only network calls are the AI services you switch on and the optional icon download.

Everything in the web app also exists as a command, and the other way round. Use whichever you like.

---

## 2. Install and first run

On a Mac (Apple silicon) or Linux:

```bash
cd ~/social-media/money-hub
bash scripts/setup.sh && source .venv/bin/activate
moneyhub doctor            # checks the machine and says how to fix gaps
```

`moneyhub doctor` reports on the PDF engine, fonts, ffmpeg (video), AI providers and the optional tools. **Fix whatever it reports first.** The common ones are missing fonts and no ffmpeg.

Make your first product with no AI and no internet, to prove everything works:

```bash
moneyhub make "nurse" weekly_planner --llm builtin
```

`--llm builtin` means "use only the offline writer". The result is real but plain. With an AI provider connected (section 17) the words are specific and much better. The default writer is `claude -p` (Claude Code headless), then the other providers in `moneyhub.yaml`, then the offline one as the last resort.

Open the app:

```bash
moneyhub ui                # http://127.0.0.1:8765
```

**Restart the app after any code update.** A UI left running from before an update keeps old Python but reads new templates, which shows "Internal Server Error". Press Ctrl+C and run `moneyhub ui` again.

Run the tests (about 8 to 12 minutes) only if you change the code:

```bash
pytest -q --basetemp=/some/scratch/dir      # delete the scratch dir afterwards
```

---

## 3. The ideas behind it

Four things decide what you get:

| Idea | What it is | Where you set it |
|---|---|---|
| **Niche (audience)** | The group of people you help: "nurse", "ADHD adults", "dog trainers". Anything typed works; 15 are built in. | Wizard step 1, or the first argument of `make` |
| **Product type** | What you make for them: weekly planner, clipart pack, presentation template... 25 types. | Wizard step 1 (lower half), or the second argument of `make` |
| **Look** | Colours (palette), fonts, header style, corner radius, grid lines, art motif, page layout. | Wizard step 2, or `--palette --fonts --header ...` |
| **Seed** | A number that makes a look reproducible. Same seed, same look. | `--seed` |

Built-in niche profiles: adhd, faith, fitness, gardening, home, meal_planning, mindfulness, new_mom, nurse, personal_finance, pet_owner, small_business, student, teacher, wedding. Any other text works; with an AI provider connected MoneyHub researches the unknown niche once and caches it (`moneyhub niche "dog trainers" --research`).

Every product goes through the same pipeline: research the niche, write the content, render the files, check for similar products, write the listing copy, make the images and pins, write the upload guides, run the quality checks, build the upload package. The wizard shows these steps while it works.

---

## 4. Your audience: does the niche apply to every product?

**No.** This is the most important thing to understand about the first wizard page.

MoneyHub has two kinds of product types.

**Audience-specific (10 types).** The content is written *for* the audience: the prompts, boxes, checklists, habits, budget categories and wall-art quotes come from the niche profile.

| Type | What the niche changes |
|---|---|
| weekly_planner, daily_planner | Sample goals, boxes and labels |
| habit_tracker | The habits listed |
| budget_tracker | Categories and goals |
| guided_journal | Prompts |
| checklist_pack | The checklists themselves |
| worksheet_pack | Exercises |
| card_deck | Affirmations, prompts or flashcards |
| ebook_guide | Chapters and advice (review the facts before selling) |
| wall_art | Quotes and mood |

**Same for every audience (15 types).** The files do not depend on who you pick: clipart, digital paper, cut files, coloring pages, kids coloring, sticker sheets, oracle decks, activity books, learning workbooks, character clipart, icon stickers, Montessori cards, classroom packs, visual schedules and presentation templates. These are listed **without the niche word** in the title, tags and copy ("Sage Seamless Digital Paper Pack", not "Nurse Digital Paper Pack"). The audience only nudges the colour mood. Their titles are named after the design instead, and repeat packs get "Vol. 2", "Vol. 3" so each listing is distinct.

In the wizard those cards carry a small **"Same for every audience"** label, and step 3's summary says so. If you pick "ADHD" and then "Digital paper pack", you get a digital paper pack; ADHD does not appear in it.

**What this means for you:** for a niche-free type you can type any audience (or pick the first card) and spend your effort on the *look* and the *theme* options instead. For audience-specific types the audience is the whole point, so choose it carefully.

**Not every product belongs to every audience, and the wizard knows it.** When you pick an audience card, the product grid shrinks to the products that fit that audience (for example a wedding couple sees budget tracker, checklists, journal, wall art, clipart, digital paper and cut files, but not classroom charts or Montessori cards). A line above the grid says how many are shown, and **Show all 25 products anyway** brings the rest back if you want one. If you type your own audience, you see the 10 audience-specific types first, with the rest behind the same button. The same rule applies to the Ideas page: its offline brainstorm only pairs an audience with products that suit it, and the AI brainstorm is told to do the same.

Each audience card also shows **"We'd make: X"**, the product MoneyHub thinks suits that group best.

---

## 5. The web app, page by page

### 5.1 Home (`/`)
The landing page: what the tool does, a video tour, the three-step overview, what you get with every product, the list of things you can make and common questions. Press **Make my first product** to start.

### 5.2 The wizard (`/make`)
Three steps. Everything you choose is also shown as the exact command at the end.

**Step 1: Who do you want to help, and what should we make for them?**

- **Idea cards.** 15 audiences, each with what they struggle with and a suggested product. Click one to choose both.
- **Surprise me.** Picks an audience and product for you.
- **Type my own audience.** Describe any group ("night-shift workers", "new gardeners").
- **Suggested products ("make next").** After you have recorded sales or views (section 16), cards appear here with the reason.
- **What should we make for them?** The grid of all 25 product types, each with a one-sentence plain description. A **Suggested** tag marks the one matching the audience card. Types with the **Same for every audience** label ignore the audience (section 4).

**Step 2: Pick a look.**

- **Options for this product** (shown first, only when the product has some): picture theme, line thickness and pages for kids books and stickers; icon set, search word and badge shape for icon stickers; word language, difficulty, focus, grade and pages for workbooks and activity books; student names for classroom packs; deck kind and card size for oracle decks. These appear whether you choose "Choose for me" or "I'll pick".
- Colour palette (12 of them), or **your brand colour** (any hex; MoneyHub builds a matching palette).
- **E-ink tablet** version (reMarkable, Kindle Scribe, Boox): black and white, hyperlinked.
- Font pairs (editorial, modern, friendly, classic, clean, warm).
- **Page layout** for planners: ready-made presets, generated layouts (`auto:N`), or describe one in words ("big priorities on the left, habit row at the bottom"). A live thumbnail shows the page.
- Advanced look: header style, corner radius, grid lines, art motif, seed.
- **Product options** that appear only for the type you chose (number of weeks or pages, theme, age level, grade, language, names, card size and so on). They are listed per type in section 6.
- Page sizes: Letter, A4, tablet, e-ink, or the type's own format (PNG, JPG, SVG, deck).

**Step 3: Make it.**
A summary in plain words, the equivalent `moneyhub make ...` command (copy it if you like), the AI writer to use, and which marketplaces to write guides for. Press **Make my product**. A progress log runs (about a minute for most products, longer with images and video). When it finishes you land on the product page.

### 5.3 My products (`/products`)
Your catalogue with thumbnails. Each card shows title, niche, type and status. Open one to see everything about it.

### 5.4 The product page (`/product/<id>`)
This is where you work after making something. From the top:

- **Preview.** Page images of the main PDF, or the art for image products.
- **Quality checks.** Pass, warn or fail lines (section 9). A product is "ready" only when nothing fails.
- **Files you will sell.** The exact files buyers get, with a file viewer. Nothing else is in the buyer's download.
- **Listing copy.** Title, tags, description, price suggestion, FAQ and terms for the marketplaces. A **risk** scan flags brand names, "inspired by" phrasing and rights language.
- **Images by marketplace.** Etsy photos (numbered, in upload order), Gumroad cover and thumbnail, Payhip cover, Ko-fi square, Pinterest pins, and the videos.
- **Launch video (brag).** Make a short promo with music and optional voice-over (section 12).
- **Visual editing.** Export layered SVGs to edit in Penpot, Inkscape or Open Design, then import your edits (section 13).
- **Upload guides.** One step-by-step guide per marketplace.
- **Sell it on...** One zip per platform with the download, the photos and the text (section 11). A button per platform.
- **Sell it somewhere else.** KDP (paperback), Notion and Canva exports where the product supports them.
- **Track it.** Mark it approved, record where you listed it (with the URL and price), record sales and views. This feeds the Sales & learning page.
- **Make a new variation of this** (regenerate): a new seed, look and copy for the same audience and type.
- **Delete.** Removes the product and its files from the catalogue.

### 5.5 Ideas (`/ideas`)
Brainstorms audience and product ideas with an AI writer. Optional **focus** (for example "pets, students, health professionals") and **how many** (5 to 30). The results are **hypotheses from general knowledge, not live search data.** Before you build, type the suggested phrases into Etsy and Pinterest search, look at autocomplete and the number of results, then make two or three products and see which one gets views.

### 5.6 Sales & learning (`/report`)
Which audience, product type and look is working, based on the sales and views *you* recorded. It also feeds the "make next" cards.

### 5.7 Settings (`/settings`)
- **AI writing helpers.** Paste keys for Anthropic, Gemini, Groq, OpenRouter and others; test each one. Keys are written to a git-ignored `.env` file with owner-only permissions, never to yaml or code. These endpoints only answer from your own computer.
- **AI artwork for wall art.** Optional image providers (Hugging Face, Together, OpenAI, a local server) and "Claude draws vector art".
- **Second-opinion tools (optional).** Master switch and one switch per craft tool (section 18). All off by default.
- **Extra files to build.** The extra deliverable kinds (vectors, sheets, pdfs, docx) and "build them automatically".
- **Output.** Where products are saved.

### 5.8 Docs (`/docs`)
The short in-app guide with the video tour, glossary and troubleshooting.

### 5.9 Video tutorials (`/tutorials`)
One narrated video per feature, recorded from the real app (section 28). The page groups them: making a product, checking and selling it, ideas and settings and extras, and the command line.

---

## 6. Every product type

Prices are the suggested range MoneyHub shows; they are starting points, not data. "Niche" says whether the audience changes the content (section 4).

### Planners, trackers and journals (audience-specific)

| Type | You get | Notable options |
|---|---|---|
| **weekly_planner** ($6-15) | Undated weekly pages, monthly overviews, goals, notes. Printable PDF plus a hyperlinked tablet version. Sizes: Letter, A4, tablet, e-ink. | `--weeks` (4-60), `--page-layout`, `--layout-prompt`, `--eink`, `--decor` and `--decor-*` (also on the other planners, journals, trackers, checklists, worksheets and guides) |
| **daily_planner** ($5-12) | One page per day: hourly schedule, priorities, to-do list, audience boxes. | `--days` (7-120), page layouts |
| **habit_tracker** ($4-10) | An interactive spreadsheet (tick boxes, automatic percentages, chart) plus 12 printable monthly trackers. | `--gsheet-link` |
| **budget_tracker** ($7-18) | A spreadsheet with transactions, budget vs actual, savings goals, debt payoff and a dashboard, plus printable budget pages. | `--gsheet-link` |
| **guided_journal** ($5-12) | 30 days of prompts with gratitude, mood and a small-step box, plus weekly check-ins. | |

Spreadsheet products add a Google Sheets help block to the Start-Here page. Cells with formulas are protected (Review > Unprotect Sheet, no password). Recalculation in Excel and Numbers has not been verified on a real machine yet.

### Printable text products (audience-specific)

| Type | You get | Notes |
|---|---|---|
| **checklist_pack** ($3-9) | A bundle of audience-specific checklists: routines, prep lists, resets, supplies. | |
| **worksheet_pack** ($3-9) | Printable worksheets with directions and an answer key. | Classroom, homeschool or self-guided |
| **card_deck** ($3-8) | A printable deck (affirmations, prompts or flashcards), 9 per sheet, with cut guides. | |
| **ebook_guide** ($4-14) | A short beginner guide: chapters, key points, a takeaway and action steps. Four page layouts. | **Review every fact before selling.** Health, money and legal topics get a "general information only" disclaimer. |
| **wall_art** ($4-12) | A set of typographic quote posters with procedural art, as high-resolution JPG packs in 5 print ratios (2:3, 3:4, 4:5, 5:7, ISO A). | `--motif`, including `icon:<set>/<name>`; `--ai-art`; room mockups for the listing |

### Art and craft files (same for every audience)

| Type | You get | Notable options |
|---|---|---|
| **clipart_pack** ($5-16) | Abstract boho clipart: transparent PNGs in several colourways, SVG vectors, a commercial licence PDF. | |
| **character_clipart** ($4-14) | Cute coloured characters (animals, vehicles, seasonal, fantasy): PNG, SVG, licence. | `--theme`, `--count` (12-60) |
| **digital_paper** ($4-12) | Seamless 12 x 12 in patterns as 3600 px JPGs, plus a commercial licence. A QA check verifies the tiles join without a seam. | |
| **cut_files** ($4-14) | Single-outline designs as SVG, DXF, EPS and PNG for Cricut and Silhouette, with a licence. A round-trip check re-reads the files the way cutting software does; the DXF declares inches. | `--figures` (build the designs from the kids figures), `--theme` |
| **sticker_sheets** ($3-8) | Colourful die-cut stickers: printable sheets for sticker paper plus transparent PNGs for GoodNotes. | `--stickers` (12-48), `--theme`, `--print-then-cut` (also writes print-then-cut sheets and cut-line SVGs) |
| **icon_pack** ($3-8) | Die-cut icon stickers made from open-source line icons, with the icon licence notice. | `--collection`, `--query`, `--shape`, `--count` (12-120) |

### Kids and classroom (same for every audience)

| Type | You get | Notable options |
|---|---|---|
| **coloring_pages** ($3-9) | Mandala, pattern and shape pages as clean line art. KDP-ready. | `--pages` (10-40) |
| **kids_coloring** ($3-9) | Bold, friendly animals, sea life, vehicles and treats plus shape, counting and tracing pages. KDP-ready. Different figures every time. | `--theme`, `--age` (kids or toddler), `--pages` |
| **activity_book** ($3-9) | Mazes with answers, dot-to-dot, tracing, odd-one-out. KDP-ready. | `--level` (toddler, kids, big) |
| **learning_workbook** ($3-10) | Ages 3-7 worksheets. Focuses: mixed, colours, words, numbers, time, feelings, handwriting, cursive, sightwords, stem. | `--focus`, `--grade` (prek, k, 1, 2, 3 for sight words), `--language` (en, es, fr, de) |
| **montessori_cards** ($3-9) | Three-part matching cards (control, picture, name) with cut guides. | `--language` |
| **classroom_pack** ($3-8) | Name tags, desk plates, reward, behaviour and chore charts, a calendar set, birthday chart, star-of-the-week posters. | `--names` (up to 30; blank lines to write in if omitted), `--theme` |
| **visual_schedule** ($3-8) | Routine boards, first-then, now/next/later, choice board, feelings board, picture cards with hook-and-loop dot guides. (Never write the trademark "Velcro" in listing text.) | `--theme` |

### Cards and templates (same for every audience)

| Type | You get | Notable options |
|---|---|---|
| **oracle_deck** ($4-12) | Illustrated tarot-style (22 archetype cards) or oracle (gentle message cards) deck with cut guides, a how-to page and card backs. For reflection and entertainment. | `--deck` (oracle or tarot), `--card-size` (tall 2.5 x 4.5 or poker 2.5 x 3.5), `--cards` (12-36) |
| **presentation_template** ($5-15) | An editable 12-slide widescreen `.pptx` (title, agenda, section, two columns, quote, key numbers, process, image gallery, before and after, team, pricing, thank you), a PDF preview and an editing guide. Built with the deckcraft tool (must be installed; the craft on/off switches do not matter). Every object is a text box or shape in the product's palette. The fonts are free Google Fonts and are **not** included; the guide names them. | Look options only |

---

## 7. Looks, layouts, e-ink and brand colour

`moneyhub styles` prints every look option. The main ones:

- **Palettes (12):** sage, terracotta, ocean, blush, lavender, charcoal, forest, sunset, denim, mocha, mint, plum. Every palette is checked for contrast (ink on paper at least 7, accent text at least 4.5); a failing palette fails QA.
- **Brand colour:** `--brand '#2F6B57'` builds a matching palette from your hex. The wizard has a colour picker.
- **Fonts (6 pairs):** editorial (Playfair Display + DM Sans), modern (Fraunces + Inter), friendly (Nunito), classic (Lora + Inter), clean (Poppins + DM Sans), warm (Fraunces + DM Sans). The files are bundled for the PDFs. Buyers who get editable files (slides, SVG) must install the free fonts themselves; font files are never put in a download (licences, see `docs/licenses.md`).
- **Header:** band, rule or box. **Radius:** 0, 6, 12, 18 px. **Grid:** solid, dotted, dashed.
- **Motif (wall art):** background art styles, or `icon:lucide` (a random simple icon) / `icon:tabler/home` (a specific icon) once the icon set is installed.
- **Seed:** same seed and options give the same look. Change only the seed for a fresh variation.

**Page layouts** (weekly and daily planners): presets, `auto:N` (generated layout number N), or a description in words. `moneyhub layouts weekly_planner --count 8` writes a contact sheet so you can pick a number, then `--page-layout auto:5`. A layout that does not fit a page size falls back to the first preset and the product page says so.

**E-ink:** `--eink` makes black-and-white, hyperlinked pages sized for reMarkable, Kindle Scribe or Boox. Not yet checked on a real device.

**Page decoration (optional, all off by default).** Planners, journals, trackers, checklists, worksheets and guides are plain white pages unless you ask for decoration. It has three separate layers, and each has its own style:

| Layer | What it is | Styles |
|---|---|---|
| **Corner art** | Faint line art in a corner of every page (a watermark) | themed, botanical, floral, waves, sparkles, geometric |
| **Title-bar pictures** | A small row of pictures in the page title bar | themed, botanical, floral, sparkles, hearts, waves |
| **Background** | A pale pattern or watercolour wash behind the page. Writing boxes stay white. **Uses more ink.** | themed, watercolor, dots, leaves, daisies, waves, sparkles, diamonds, terrazzo, hearts, stars, confetti |

Shared settings: **strength** (light, medium, bold), **corner position** (bottom-right, top-right, bottom-left, top-left, or opposite corners) and the **theme** for the "themed" style. A themed picture set follows the audience: a stethoscope, heart and pulse line for nurses; books, a pencil and an apple for teachers and students; a sprout and flowers for gardeners; coins and a chart for money; rings and a dove for weddings; a paw for pet owners; and so on (14 themes, `--decor-theme` overrides). The pictures are simple original line drawings made for MoneyHub, so there is nothing to credit.

Three ways to set it:

```bash
moneyhub make "nurse" weekly_planner --decor all                      # themed corner + title bar + watercolour background
moneyhub make "nurse" weekly_planner --decor-corner floral --decor-corner-at opposite --decor-strength medium
moneyhub make "nurse" daily_planner --decor-header themed             # only the title-bar pictures
```

or the **Decoration** block on step 2 of the wizard (with *Light touch*, *Fully decorated* and *No decoration* buttons and a live example page), or the `decor:` section of `moneyhub.yaml` for defaults. Options you give always win over the file. Backgrounds are kept faint on purpose: the strongest tint of every palette is tested so that body text and small grey text stay easy to read. When a background is on, the listing description and the Start-Here page add a short note suggesting grayscale or economy printing. E-ink versions are always plain. Asking for decoration on a product that does not support it (clipart, digital paper and so on) is an error; defaults from the yaml file are simply skipped there.

**Why flex and not grid inside tables:** a known WeasyPrint issue can make a grid page with nested flex tables take about 15 minutes to lay out. The budget pages use flex rows for that reason. This only matters if you edit templates.

---

## 8. What is inside a finished product

Every product is a folder under `out/products/<timestamp>-<niche>-<type>/`:

```
product/            the files buyers receive (and nothing else)
  00-Start-Here.pdf   what you have, how to open/print it, licence (skipped for some types)
  ...                 the PDFs, spreadsheets, zips, PNG/JPG packs, .pptx
  Editable-files/     only if you built extra files (section 18)
images/
  etsy/               numbered listing photos (10 max on Etsy)
  gumroad/ payhip/ kofi/   cover / thumbnail / square
  pinterest/          1000 x 1500 pins
  video/              pin video and listing video
listing/
  etsy-description.txt, etsy-tags.txt, listing.json, pins.json
  guide-etsy.md ... guide-pinterest.md   one guide per marketplace
art/                  working art used for previews (not sold)
packs/                per-platform zips after `export pack`
editable/             layered SVGs after `edit export`
spec.json             exactly what was made (reproducible)
craft-build.json      report of extra files (if any)
upload-package.zip    everything the marketplaces need in one zip
```

The buyer only ever receives what is in `product/`. A failed generation removes its own folder, so no empty folders appear.

Statuses: **draft** (just made), **approved** (you reviewed it; `moneyhub approve <id>`), **listed** (you recorded a listing).

---

## 9. Quality checks (QA) explained

Every product gets a list of checks. **Pass** is fine, **warn** is advice, **fail** blocks "ready". What they cover:

- **Colour contrast** of the palette.
- **For every PDF:** page count (minimum 3, or 1 for Start-Here and licence pages), file size under 20 MB (Etsy's per-file limit), fonts embedded, possible blank pages, internal links on hyperlinked planners.
- **For spreadsheets:** the workbook opens, expected sheets and formulas exist.
- **For zips:** size under 20 MB, images present, image resolution, transparency on PNG packs.
- **For slide decks:** valid `.pptx` package, slide count matches, size under 20 MB.
- **Cut files:** thinnest gap between cuts at least 1.5 mm; SVG and DXF round-trip ("Opens in cutting software").
- **Seamless papers:** the join between opposite edges looks like any other join.
- **Translations reviewed** (bilingual products, section 21).
- **Spelling** (warn only; a flagged word may be a niche term).
- **Uniqueness:** warns when the product is too similar to one already in your catalogue (change the audience angle or regenerate). Cross-type uniqueness records figures used in stickers and Montessori cards.
- **Risk** scan of the listing text: brand and trademark terms, "inspired by" phrasing, risky claims, rights language (section 10).
- **Second opinion** and **Editable formats**: warn-only lines from the optional craft tools (section 18).

---

## 10. The listing kit and marketplace rules

For each product MoneyHub writes: a title, 13 tags, a description, a FAQ, terms, pin titles and headlines, a pin description and a price suggestion with a launch-discount idea.

Rules it follows, and that you should too:

- **AI disclosure.** Etsy requires saying AI tools were used, in the **description** (not tags or photos). The description ends with a disclosure line and the Etsy guide says to tick the matching box. Keep that line.
- **No trademarked or brand terms.** `moneyhub risk <id>` (or `--text "..."`) scans for them: entertainment characters, sports leagues, brands, ambiguous words and generic words that are trademarks (for example "Velcro"). Tool and platform names are fine in a description ("for GoodNotes") but avoid them in titles and tags. Add your own terms under `risk.extra_terms` in `moneyhub.yaml`. Disclaimers do not protect you; scanners match the word.
- **Pinterest text safe zone:** pin text stays outside the bottom 20%.
- **Niche-free titles** never contain the audience.
- **Licence wording** comes from the product type: personal use by default; commercial use for clipart, digital paper, cut files and similar (with what is allowed and not allowed spelled out); an own-presentations licence for slide templates.
- **Fonts are never in the download.**
- **Nothing is invented:** the guide and wall-art content avoid made-up statistics, studies and quotes; health, money and legal topics get a general-information disclaimer.

MoneyHub's research and price ranges are general guidance. Check current marketplace rules and limits before you rely on them: they change.

---

## 11. What to upload on each platform

MoneyHub never uploads for you. Run:

```bash
moneyhub export pack <id> etsy        # or gumroad, payhip, kofi
```

or press the platform button under **Sell it on...** on the product page. Each pack is one zip:

```
1-DOWNLOAD/        what buyers receive. Upload as the listing's digital files
2-LISTING-IMAGES/  listing photos, in upload order
3-LISTING-TEXT/    step-by-step guide, title, tags, description, price
README.txt
```

Files that do not fit the platform's limits are grouped into zips automatically, or the README warns you.

| Platform | Limits MoneyHub checks (confirm them yourself) | Photos | Text |
|---|---|---|---|
| **Etsy** | 5 files, 20 MB each, 100 MB total | 10 numbered photos + optional 1920 x 1080 listing video | Title (max 140 chars), 13 tags, description with the AI line, price |
| **Gumroad** | 16 GB per file (free items 25 MB) | `cover-1280x720.png`, `thumbnail-600x600.png` | `guide-gumroad.md` |
| **Payhip** | 5 GB per file | `cover-1600x1067.png` | `guide-payhip.md` |
| **Ko-fi** | about 1 GB per file (secondary source) | `square-1000x1000.png` | `guide-kofi.md` |
| **Pinterest** | not a store: it sends people to your listing | 1000 x 1500 pins, pin video | `guide-pinterest.md` |

For a presentation template the buyer's download is three files: the `.pptx`, the PDF preview and the Editing-Guide-and-License PDF. The Etsy guide for it asks you to copy the category of similar best-selling listings, because MoneyHub cannot know Etsy's current category tree.

No platform requires an editable format (PSD, Word). See `docs/what-to-upload.md` for the table by product type.

---

## 12. Images, pins and videos

**Listing photos** (Etsy): hero, what's included, a look inside, sizes and formats, how it works, a detail, then in-use mockups (pages on a desk, a tablet, a fan of pages; clipart on cards and gift tags; cut files on mugs and shirts; wall art in rooms). All are drawn flat in the product's own colours; they are illustrations of use, not photographs. For image products (wall art, papers, slide decks) the previews are rendered pictures, with overview sheets for slide decks.

**Spreadsheet products** also get a drawn illustration with sample numbers. Add one or two **real screenshots** of the workbook open in Excel or Google Sheets as extra photos; buyers trust them.

**Pins:** six 1000 x 1500 pins with different headlines. Pinterest text stays out of the bottom 20%.

**Videos:** a short pin video and an Etsy listing video are made automatically (needs ffmpeg). Skip them with `--no-video`, skip all images with `--no-images`.

**Brag (launch video):**

```bash
moneyhub brag <id> --tone cinematic --format all --duration 20 --voice auto --captions
moneyhub brag --shop 3,4,5            # a collection video
moneyhub brag --url https://...       # from a website (needs Playwright + Chromium)
```

Tones: polished, playful, cinematic, chaotic, app-store, or free text like "calm and cosy". Formats: vertical, landscape, square, all. Music: generated, none, or your own licensed file (`--music file --music-file x.mp3`). Voice: kokoro, say, espeak or auto. `--preview` makes a quick half-size draft. See `docs/brag.md`.

---

## 13. Editing the art yourself

```bash
moneyhub edit export <id>       # layered, editable SVGs + fonts + a design brief into <product>/editable/
moneyhub edit import <id>       # replace listing images with your edits (matched by file name)
```

The SVGs open in Penpot, Inkscape or Open Design. Every object is its own named group (Background, Motif-3, Quote...). Only **posters** are truly editable art; pins and hero are mockups with embedded page pictures. Fonts for your own editing are copied into the folder but are never part of the buyer's download. Penpot SVG import has not been checked on a real Penpot yet. See `docs/editing.md`.

---

## 14. Exports

| Command | For | Notes |
|---|---|---|
| `moneyhub export kdp <id> --trim 6x9 --paper white` | Amazon KDP paperback | Print-ready interior, a finished full-wrap cover plus guide-line template, and a KDP guide. Trims: 5.5x8.5, 6x9, 7x10, 8x10, 8.5x11. Paper: white, cream, color. `--cover-image` uses your own front art. **Gutter, paper thickness and bleed numbers come from KDP's help pages; confirm them before relying on them.** Supported for planners and the KDP-ready coloring, activity and learning books. |
| `moneyhub export notion <id>` | Notion | Markdown pages and CSV databases to import |
| `moneyhub export canva <id> --link <url>` | Canva | PDF and page images, a brand kit, a buyer "template link" page and a how-to |
| `moneyhub export pack <id> <platform>` | Etsy/Gumroad/Payhip/Ko-fi | Section 11 |
| `moneyhub export craft <id> --kinds ...` | Extra editable files | Section 18 |

How these behave inside Canva, Notion and KDP's previewer has not been verified on the real services.

---

## 15. Working at scale

- **Variations:** `moneyhub regenerate <id>` (new seed, look and copy), or `moneyhub make-many "nurse" weekly_planner --count 10 --vary look` which prints a table of id, title, QA and uniqueness. `--vary` can be look, theme or seed.
- **Batch:** `moneyhub batch "nurse,teacher" --products weekly_planner,habit_tracker` makes every combination. A good way to get the first 5 to 10 products to test demand.
- **Bundles:** `moneyhub bundle 3,4,5 --name "Nurse Starter Kit" --discount 0.3` combines existing products into one zip and listing kit with fee-aware pricing. `moneyhub bundle halloween` or `moneyhub bundle nurse` makes the products and bundles them (default types: for a theme, coloring book + activity book + sticker sheets + character clipart; for a niche, weekly planner + habit tracker + budget tracker + checklist pack). Bundles are CLI only.
- **Free sample:** `moneyhub sample <id> --pages 2` writes a preview PDF of the first pages for email or Pinterest lead magnets.

---

## 16. Learning what sells

Everything you record stays on your machine.

```bash
moneyhub approve 12                                   # you reviewed it
moneyhub listed 12 etsy https://etsy.com/listing/... --price 9.99
moneyhub sale 12 etsy 9.99 --units 1                  # add --day for an older date
moneyhub report                                       # which audience/type/look works
moneyhub next                                         # what to make next
```

Also: `moneyhub calendar --months 4` (seasonal opportunities to prepare, general guidance, not sales data), `moneyhub keywords "planner"` (search-phrase ideas to check by hand; `--suggest` also asks Google autocomplete and sends your seed text to Google, so it is off by default), `moneyhub ideas --focus pets --n 15` (also on the Ideas page).

On the product page, **Track it** records views and sales. A fair method: make 3 different products, list them, wait, and let `report` show which got views before making more of the same kind.

---

## 17. AI services and keys

`moneyhub types` shows which writers are available (a tick means usable). The chain per task is in `moneyhub.yaml` under `llm.tasks` (content, listing, research, motion, art). Each task tries its providers in order and falls through on error; `builtin` always works offline.

Providers: `claude_cli` (`claude -p`), `anthropic`, `gemini`, `groq`, `openrouter`, `ollama` (local). Add keys in **Settings** (or the `.env` file); MoneyHub never puts keys in yaml or code and never commits them. Use `--llm claude_cli,builtin` or `--llm builtin` on any command to override.

AI image providers for wall-art backgrounds (Hugging Face, Together, OpenAI, local) are off by default (`--ai-art`, `--art-provider`). Check each provider's terms before selling its output. `claude_svg` (Claude draws vector art) works; the live image providers have not been verified here.

---

## 18. The optional craft tools

Third-party command-line programs (vectorcraft, pdfcraft, gridcraft, photocraft, wordcraft, deckcraft, soundcraft, cadcraft, plus lightcraft, designcraft, effectcraft, filmcraft). They are **unaudited and optional**, installed by `scripts/install_craft_tools.sh` (checksum-verified) into the git-ignored `tools/craft/`. `moneyhub tools` lists them. With the cadcraft switch on, `moneyhub verify <id>` (and the after-make check) also compares each cut-file DXF's size and unit with its SVG and warns if they differ.

**Everything is off by default.** With the master switch off no tool is ever started and output is byte-for-byte the same. A missing, slow or failing tool is skipped and never fails a product.

```bash
moneyhub tools --master --enable pdfcraft,gridcraft --verify-after-make
moneyhub verify <id>                     # open the product's files with the matching tool; advisory only
moneyhub craft pdfcraft -- info file.pdf # run one tool directly
```

**Second opinion** (`verify`): opens PDFs, spreadsheets, editable SVGs, listing images and DXFs and writes `craft-verify.json`. It is never part of the QA gate.

**Extra deliverables** (`moneyhub export craft <id> --kinds ...`, or `moneyhub tools --outputs vectors,docx --outputs-after-make`). Written to `product/Editable-files/`, each file re-opened and checked, failures dropped and listed in `craft-build.json`:

| Kind | Tool | Result |
|---|---|---|
| `vectors` | vectorcraft | Per poster design: SVG, AI, EPS, PDF and a layered PSD (at least 2 layers, else deleted). With photocraft on, the PSD's quote and small text become live text layers. |
| `sheets` | gridcraft | CSV and HTML copy of every sheet (up to 12) |
| `pdfs` | pdfcraft | Title and author set on each PDF, swapped in only if page count and page 1 match |
| `docx` | wordcraft | An editable .docx of the text of guides, worksheets, checklists and journals (not the print design) |

Verified on real files so far: `docx`, `sheets`, `pdfs` and `vectors` (including live-text PSD layers) were run for real; opening the results in Word, Excel, Numbers, Photoshop or Photopea is still yours to check. Full detail: `docs/craft-tools.md`.

**Presentation templates** use deckcraft as part of the product itself (not an extra).

Claude Code's permission check blocks running unaudited tool binaries, so if you work with Claude Code, it writes the code and you run the tool commands with the `!` prefix.

---

## 19. Video engines and voices

Video engines (`render.motion` in `moneyhub.yaml`, or `--motion remotion,pillow`): **pillow** (built in, default), **remotion** (React; needs a licence if your company has 4 or more people), **manim** (Python), **hyperframes** (HTML; telemetry is switched off in code).

```bash
moneyhub engines status
moneyhub engines install remotion          # or manim, hyperframes
moneyhub engines test pillow --out engine-test.mp4
moneyhub voices status
moneyhub voices install                    # downloads the Kokoro voice model (~350 MB, Apache-2.0)
```

Voice-over engines: kokoro (best), say (macOS), espeak.

---

## 20. Icons and licences

```bash
moneyhub assets list                        # installed sets, licences, what can be fetched
moneyhub assets fetch tabler --limit 600    # or tabler-filled, lucide
moneyhub assets add ./my-icons --name my-icons --license CC0-1.0 --source https://...
```

Accepted licences: MIT, ISC, Apache-2.0, CC0, public domain, CC-BY 4.0. Refused: CC-BY-SA, any non-commercial licence, GPL, because products made from them could not be sold safely. Attribution licences need the credit kept in the listing text. Icon stickers and wall-art icon motifs are recoloured and cut, never resold as raw copies. Details in `docs/licenses.md`.

---

## 21. Translations guardrail

The bilingual word lists (Spanish, French, German) in the learning workbook and Montessori cards are guarded. **QA fails until the list has been AI-checked and a person has approved it.**

```bash
moneyhub translations status
moneyhub translations check --lang es     # AI proofreads (or --lang all); it reports problems, never edits the words
moneyhub translations approve --lang es --by "Name"   # YOU (or a native speaker) record that it was proofread
```

An approval stops counting if the word list changes. A native speaker's approval is still outstanding.

---

## 22. Configuration files and folders

| File | Purpose |
|---|---|
| `moneyhub.yaml` | Defaults, checked in. Output folder, LLM chains, render settings, craft switches, shop details, default sizes and marketplaces. |
| `moneyhub.local.yaml` | Your private overrides (git-ignored). Settings saved from the app go here. |
| `.env` | API keys, git-ignored, owner-only permissions. Never put keys anywhere else. |
| `out/` | Everything generated (not committed): `out/products/...` and the catalogue database. Point it elsewhere with `MONEYHUB_OUT=/path`. |
| `tools/craft/` | Installed craft tools (git-ignored). |

`shop:` in the yaml (name, email, url) is printed on the Start-Here page and licence PDFs and used as the PDF author.

**Use a scratch folder when experimenting:** `MONEYHUB_OUT=/some/scratch/dir moneyhub make ...` keeps your real catalogue untouched. Put it on the same line as the command; an `export` does not persist between separate commands in some tools.

The data volume can run near full on a laptop; delete scratch folders after tests.

---

## 23. Command reference

Run `moneyhub <command> --help` for any command.

**Making**

| Command | What it does |
|---|---|
| `make <niche> [product]` | One product with images, copy and guides. Options: `--sizes --seed --palette --fonts --page-layout --layout-prompt --brand --eink --header --radius --grid --motif --decor --decor-corner --decor-header --decor-background --decor-strength --decor-corner-at --decor-theme --art-provider --marketplaces --llm --weeks --days --pages --language --level --focus --grade --deck --card-size --cards --count --collection --query --shape --stickers --theme --age --figures --print-then-cut --names --no-research --gsheet-link --no-images --no-video --motion --ai-art` |
| `regenerate <id>` | A fresh variation of a product |
| `make-many <niche> <product> --count N --vary look,theme,seed` | Several distinct variations plus a summary table |
| `batch <niches> --products ...` | Every product for every niche |
| `bundle <ids|theme|niche> --name --discount --types ...` | One zip and listing kit |
| `sample <id> --pages 2` | Free preview PDF |

**Looking things up**

| Command | What it does |
|---|---|
| `types` | Product types, niches, sizes, LLM providers |
| `styles` | Every look option |
| `layouts <product> --count --first --out` | Contact sheet of generated layouts |
| `niche <text> [--research]` | The profile used for a niche |
| `list` | The catalogue |

**Selling and learning**

| Command | What it does |
|---|---|
| `risk <id>` or `risk --text "..."` | Brand/trademark and claims scan |
| `approve <id>`, `listed <id> <marketplace> <url> --price`, `sale <id> <marketplace> <revenue> --units --day` | Record status, listings, sales |
| `report`, `next`, `calendar`, `keywords <seed> [--suggest]`, `ideas [--focus --n]` | Learning and research |
| `delete <id> [-y]` | Remove a product and its files |

**Exports and editing**

| Command | What it does |
|---|---|
| `export kdp / notion / canva / pack / craft` | Section 14 |
| `edit export <id>`, `edit import <id> [folder]` | Section 13 |

**Video**

| Command | What it does |
|---|---|
| `brag <id>` and options | Launch video |
| `engines status/install/test`, `voices status/install` | Video engines and voices |

**Tools and checks**

| Command | What it does |
|---|---|
| `doctor` | Machine check |
| `tools`, `verify <id>`, `craft <tool> -- ...` | Craft tools (section 18) |
| `assets list/fetch/add` | Icon sets |
| `translations status/check/approve` | Word-list guardrail |
| `ui [--host --port]` | The web app |

---

## 24. Step-by-step recipes

### A. Your very first product (10 minutes)
1. `moneyhub doctor`, fix what it says.
2. `moneyhub ui`, open `/make`.
3. Pick an audience card (its suggested product is pre-marked).
4. Next, pick a palette, Next, press **Make my product**.
5. On the product page read the **Quality checks**, open the files, read the listing copy and the risk scan.
6. Press the **Etsy** button under Sell it on... and follow `guide-etsy.md`.
7. Back on the product page record the listing URL under **Track it**.

### B. Test demand with five products
1. `moneyhub ideas --focus "health professionals"` or the Ideas page, and check the phrases on Etsy.
2. `moneyhub batch "nurse,teacher" --products weekly_planner,habit_tracker,guided_journal`
3. Review each one, `approve`, list them, and wait for views.
4. `moneyhub report` and `moneyhub next`; make more of what got views.

### C. A niche-free shop line (kids and craft)
1. `moneyhub make-many "x" digital_paper --count 6 --vary look` (the audience is ignored; "Vol. N" titles keep them distinct).
2. `moneyhub bundle halloween` for a themed bundle.
3. Check the licence PDF wording, then list the bundle and the singles.

### D. A KDP coloring book
1. `moneyhub make "x" kids_coloring --pages 30 --theme animals`
2. `moneyhub export kdp <id> --trim 8.5x11 --paper white`
3. Confirm the gutter, paper thickness and bleed numbers on KDP's pages, then follow the generated KDP guide.

### E. A slide-template listing
1. Install the tools once: `bash scripts/install_craft_tools.sh`.
2. `moneyhub make "x" presentation_template`.
3. Open the `.pptx` in PowerPoint, Keynote or Google Slides and check fonts and spacing (not verified here yet).
4. `moneyhub export pack <id> etsy` and upload the three files.

### F. A launch video and pins
1. `moneyhub brag <id> --tone playful --format vertical --captions --voice auto`
2. Upload the pin images and video from `images/pinterest` and `images/video` using `guide-pinterest.md`.

### G. Editable Word and spreadsheet copies
1. `moneyhub export craft <id> --kinds docx,sheets` (text products and trackers).
2. Open the files in Word / Excel / Numbers and check them before selling them as extras.

---

## 25. Troubleshooting

| Problem | What to do |
|---|---|
| "Internal Server Error" in the app | Restart `moneyhub ui`. Old Python with new templates breaks pages. |
| A product takes very long to render | A known WeasyPrint grid-with-nested-tables issue (about 15 minutes, random). Cancel and regenerate; prefer the flex layouts. |
| UI crashed when a page loaded many previews | Fixed: PDFium is not thread-safe and all calls go through one lock (`render/pdfium_safe.py`). Keep PDF rendering on pypdfium2. |
| No video | Install ffmpeg or `pip install imageio-ffmpeg`; check `moneyhub doctor`. |
| A font looks wrong in a PDF | Check `moneyhub doctor`; the bundled fonts live in `assets/fonts`. |
| "Could not build the slide deck: deckcraft is not installed" | Run `bash scripts/install_craft_tools.sh`, then `moneyhub tools`. |
| QA says "Translations reviewed: fail" | Section 21: check, then have a person approve. |
| Uniqueness warning | The product matches one you already made. Change the audience angle, the seed, or use `regenerate`. |
| Spelling warns on a font or niche word | Warn only. Ignore it or add the word to the allow list in `spellcheck.py`. |
| A craft tool does nothing | The master switch is off, or the tool is not installed. `moneyhub tools` shows both. |
| Disk nearly full | Delete scratch folders and old products (`moneyhub delete <id>`). Tests need free space (the HyperFrames render test skips below 1 GB). |
| You changed code and tests fail strangely | Use `pytest -q --basetemp=<scratch dir>` and delete it afterwards. |

---

## 26. What still needs a real device or app

MoneyHub is honest about what it could not verify. These need you:

- Opening results in the real apps: the `.pptx` in PowerPoint, Keynote and Google Slides; the `.docx` in Word; spreadsheets in Excel and Numbers (formula recalculation); PSD/AI files in Photoshop, Illustrator or Photopea.
- Notion, Canva and KDP imports; Penpot SVG import.
- GoodNotes link behaviour; e-ink tablets.
- Printing and cutting test sheets; print-then-cut on a real machine; test cuts of cut files.
- Live image-AI providers (Hugging Face, Together, OpenAI).
- A native speaker approving the Spanish, French and German word lists; a cursive reviewer.
- Pushing the git branch so CI runs (MoneyHub never pushes by itself).

`docs/owner-verification.md` is the checklist for these.

---

## 27. Glossary

- **Niche / audience:** the group of people you help.
- **Product type:** what you make (planner, clipart pack...).
- **Niche-free:** a product type whose files and listing do not depend on the audience.
- **Palette / look:** colours, fonts, header, radius, grid, motif.
- **Seed:** a number that reproduces a look.
- **QA:** the automatic quality checks; pass, warn or fail.
- **Listing kit:** title, tags, description, FAQ, terms, pins, price.
- **Pack:** one zip for one platform (download, photos, text).
- **Upload package:** everything for the marketplaces in one zip.
- **Etsy AI disclosure:** the line in the description saying AI tools were used.
- **Mockup:** a flat illustration of the product in use, used as a listing photo.
- **KDP:** Amazon Kindle Direct Publishing, for paperbacks.
- **Gutter / bleed:** the inner margin and the printed area that runs past the trim edge in a book.
- **Craft tools:** the optional third-party command-line programs (section 18).
- **Live text:** text in a design file that you can still retype, as opposed to text baked into a picture.
- **Hook-and-loop:** the generic name for the fastener; never use the trademark in listings.
- **Brag:** MoneyHub's launch-video feature.

---

## 28. The video tutorials

Open **Video tutorials** in the menu (`/tutorials`). Seventeen narrated videos, each 1 to 3 minutes:

| Group | Videos |
|---|---|
| Make a product | Pick an audience and a product; Product options; Colours, fonts, layouts and e-ink; Page decoration |
| Check it and sell it | The product page; What to upload on each platform; Canva, Notion and KDP; Track sales and learn |
| Ideas, settings and extras | The Ideas page; Settings, AI keys and tools; Variations and the catalogue; Edit the art yourself; The launch video |
| The command line | The basics; Listing and learning; Many products at once; Tools and extras |

They are recorded by the real app against a throwaway offline copy (built-in writer, a temporary output folder), so your catalogue and AI accounts are never touched. The command-line videos replay the real output of the real commands in a terminal window.

Re-record after you change the wizard, Settings or the product page:

```bash
python scripts/record_tour.py                         # the original tour (about 6 minutes)
python scripts/record_tutorials.py                    # all tutorials (30-40 minutes)
python scripts/record_tutorials.py --only look,sell-on   # just these
python scripts/record_tutorials.py --list
```

Needs the project venv, `playwright install chromium` and ffmpeg. A natural voice is used when Kokoro is installed (`moneyhub voices install`), otherwise the Mac voice. One broken tutorial does not stop the others; a failure screenshot is written to the system temp folder.
