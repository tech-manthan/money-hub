# Digital art products: formats, sizes and what buyers expect

Research summary (October 2026). The sources are seller guides and marketplace pages, not platform rules, so **confirm anything that matters on the platform itself** before relying on it. Where MoneyHub already follows a point, the right column says how.

## File formats

| Format | Use it for | Notes | MoneyHub |
|---|---|---|---|
| JPG | Wall art, posters, photo-like art, wallpapers | Smaller and prints sharply; the default for art downloads. 300 DPI wall-art JPGs are typically 1-15 MB. | Wall art packs (JPG, 300 DPI) |
| PDF | Planners, worksheets, multi-page printables, print-at-home sheets | Best for anything with several pages or exact paper sizes. | All planner/printable products |
| PNG | Clipart, stickers, transparent elements | Needs a transparent background (PNG-24, RGB). Large 300 DPI PNGs often exceed Etsy's 20 MB file limit, so avoid PNG for big prints. | `clipart_pack`: 3000 px transparent PNGs (drops to 2400/2000 px if the zip would pass 19 MB) |
| SVG (+ DXF, PNG, EPS) | Cut files for Cricut / Silhouette | Etsy will not take a bare SVG: deliver inside a zip. Include SVG, DXF, PNG and EPS so both machine brands work. | `cut_files`: 24 single-outline designs (nothing to weld) as SVG, DXF (R12, inches), EPS and PNG zips, plus licence = Etsy's 5 files; QA checks the thinnest gap between cuts is at least 1.5 mm |
| PSD / Canva template | Editable templates | Sold as a link or file. Only your own designs; resold PLR templates must be changed substantially for Etsy. | Canva export |

## Print sizes (aspect ratios)

Five ratios cover most frames: **2:3** (4x6, 12x18, 20x30 in), **3:4** (9x12, 18x24 in), **4:5** (8x10, 16x20 in), **5:7** (5x7, 10x14 in) and **ISO A** (A5-A1). Add **1:1** square for gallery-wall sets. Metric buyers search by centimetres: 30x40 (3:4), 40x50 (4:5), 50x70 (5:7), 21x30 (A4) and 70x100 cm.

- Standard is **300 DPI at the largest size the file is sold for.** Low resolution is the main cause of refunds ("pixelated print").
- At 300 DPI, 1 mm is about 11.81 px. 50x70 cm = 5,906 x 8,268 px; 70x100 cm = 8,268 x 11,811 px.
- MoneyHub's packs are 3000-3600 px wide (36 in at 100 DPI, 12 in at 300 DPI), which prints well up to the sizes listed in each pack's README.

## Extra formats worth selling

- **Samsung The Frame TV art:** exactly **3840 x 2160 px**, 16:9, JPG (PNG also works), under 20 MB, sRGB. One pixel off (for example 3839 x 2160) makes the TV add a mat, so the size must be exact. Buyers want artwork only, no text. *MoneyHub: `--sizes frame_tv`, text-free, exact size.*
- **Phone wallpapers:** about 1290 x 2796 px (iPhone) up to 1440 x 3120 (many Android phones); packs of 10-25 sell. *MoneyHub: `--sizes phone` (1290 x 2796).*
- **Square 1:1:** gallery-wall sets of matching prints. *MoneyHub: `--sizes 1x1`.*
- **Digital paper / seamless patterns:** 12 x 12 in = 3600 x 3600 px, JPG, tile must repeat with no seam, state the true tile size. *MoneyHub: `moneyhub make <niche> digital_paper` makes 12 (up to 24, `papers` option) seamless papers from a pattern engine (`patterns.py`), checks the edge join, splits zips to stay under 20 MB, adds a Commercial-License PDF, and shows a 2 x 2 repeat in the listing photos.*
- **Clipart bundles:** transparent PNG-24 at 300 DPI, themed sets, plus a commercial licence PDF; commercial licences are commonly priced 2-3x personal use. *MoneyHub: `moneyhub make <niche> clipart_pack` (13 motifs x 3 colourways, `--` option `colourways`), with SVG vectors and a Commercial-License PDF. Have the licence wording reviewed before selling: it is a plain-language summary, not legal advice.*
- **Coloring pages:** PDF at Letter/A4 (KDP: 8.5 x 11 or 8.5 x 8.5 in), black line art on white, one design per page. *MoneyHub: `moneyhub make <niche> coloring_pages` (`pages` option, 10-40): mandalas, patterns and shape pictures from the engines, white-filled outlines so overlaps read correctly; `moneyhub export kdp` makes the coloring-book interior with a blank back for every design and no cover page.*

## Colour

- Make and deliver downloads in **sRGB** (embedded profile). It is what screens, print-on-demand sites and most home printers expect. *MoneyHub embeds the sRGB profile in every wall-art JPG.*
- Adobe RGB can give richer fine-art inkjet prints but looks flat on screens that do not manage colour; CMYK conversion is the print shop's job. Say in the listing that colours vary by screen and printer. *Pack README says this.*

## Etsy file and photo rules that affect art

- Digital files: up to **5 files, 20 MB each**. A zip counts as one file, so one zip per ratio fits the limit. *The Sell-on picker checks this and splits packs that are too big; the JPG quality loop keeps each pack under 19 MB.*
- Listing photos: at least **2000 px** on the longest side, JPG or PNG, up to 10 MB; 10 photo slots. Winning listings show 5-7 scenes: clean product shot, room mockup, frame variants, size comparison, "what you get", close-up detail, a scale reference.
- Include a **size guide image** listing every ratio and the sizes it prints at. *Wall-art listings now also get four generated room photos (living room, gallery wall, shelf, bedroom) with the real artwork framed in them, as Etsy photos 7-10.*

## AI disclosure and originality

- Etsy requires disclosing AI use **in the listing description** (and attributing the item as "designed by" you). AI-assisted digital downloads are allowed when you add real creative input.
- Selling collections of AI **prompts** as a product is not allowed on Etsy.
- Do not use trademarked or copyrighted characters, brands or famous artists' styles by name. *MoneyHub's risk scan and the AI disclosure line cover this.*

## Styles that sell (2026 reports)

Evergreen top sellers: minimalist line art, botanicals (muted "quiet luxury" watercolours in cream, sage, beige), abstract modern art, typography and quote prints (strong impulse buys), nursery sets, vintage and travel posters. Emerging: maximalist botanicals and dark moody abstracts. Sets of 3-10 matching pieces sell better than single prints.

## Sources
- Etsy digital download file size guide: https://snaptosize.com/etsy-digital-download-file-size
- Best file format for Etsy printables: https://snaptosize.com/best-file-format-etsy-printables
- Printable wall art sizes: https://www.bulkmockup.com/how-to-size-printable-wall-art-for-etsy/ and https://elistit.com/blog/etsy-wall-art-sizes-2026-complete-guide/
- Colour profiles for print: https://www.lumaprints.com/blog/webinar-preparing-your-image-file-for-a-successful-print/ and https://www.printful.com/blog/rgb-vs-cmyk-guide-to-color-systems
- Etsy mockup/photo requirements: https://psdmate.com/blog/etsy-image-size-requirements
- Etsy AI policy summaries: https://www.shieldmyshop.com/blog/2026-05-08-can-you-sell-ai-art-on-etsy-2026-policy-guide and https://www.growtsy.com/etsy-ai-policy
- Samsung Frame TV art specs: https://www.operastudio.io/blog/samsung-frame-tv-art-size-guide
- Clipart/PNG packaging: https://www.insightagent.app/guides/selling-png-files-etsy
- Seamless patterns / digital paper: https://www.listifyai.net/blog/how-to-sell-seamless-patterns-digital-paper-etsy
- SVG cut files: https://cutfileclassroom.com/which-file-types-to-include-for-selling-svg-files/
- Poster sizes in pixels: https://printshop.paperlust.co/blog/poster-size-in-pixels-and-dpi
- Coloring books: https://www.inkfluenceai.com/how-to-sell-coloring-books
- Style trends: https://printify.com/blog/leading-trends-for-etsy-sellers-in-2026/ and https://etsyhunt.com/best-etsy-wall-art

## Children's coloring books (niche notes, October 2026)
Sources are seller-education blogs, not platform data, so treat the numbers as directional. Check KDP's own help pages before uploading.
- **Demand:** one 2026 blog quotes Circana BookScan: about 16.7 million US children's coloring and activity print units in 2025, up 18% on the year (children's print overall up about 3%) ([promptspace](https://www.promptspace.in/blog/ai-coloring-page-prompts-etsy-sellers-printable-2026), [bookcoverslab](https://bookcoverslab.com/blog/low-competition-kdp-niches-2026)).
- **What kids' buyers want:** bold, simple outlines; dinosaurs, vehicles, animals, unicorns; multi-page bundles outsell single pages; seasonal drops do well. Adult buyers prefer fine detail, so kids' books should *not* look like the mandala pack.
- **Competition:** "coloring pages" alone is crowded. Stack audience + theme + line weight (for example "ocean animals, toddler, thick lines"). That is why MoneyHub has `--theme` (7 themes) and `--age toddler|kids` (line width 15 vs 10 units).
- **Interior for KDP:** 8.5 x 11 in is the usual size; art single-sided with a blank back because markers bleed through; no bleed, keep line work inside the margins; 24-page paperback minimum. MoneyHub's KDP export already adds the blank backs and checks margins and the page count.
- **Legal/listing:** no licensed characters (the figures here are original shapes); disclose AI assistance where the platform asks (the Etsy disclosure line is already in every listing).
- **What MoneyHub does:** `moneyhub make "x" kids_coloring --theme ocean --age toddler --pages 24` draws 16 figure types (cat, fish, butterfly, turtle, owl, snail, ladybug, whale, octopus, rocket, car, robot, dinosaur, flower, house, ice cream) with details that change every time (spots, bows, stripes, petals, faces), cycling so the same figure never repeats until the theme's list is used up, plus learning pages: shape faces (with names), count-and-colour (2-9), trace-the-dots and "color all the friends" scenes. Captions say what to colour. New figures: add a function in `kidsart.py` and list it in `KINDS`, `NAMES` and a theme.
- **Ideas not built yet:** seasonal packs (Halloween, Christmas, Easter) as extra themes; alphabet and number tracing books; connect-the-dots and mazes; "colour by number" pages.

## Tarot-style and oracle decks, sticker sheets
- **Oracle / tarot-style deck** (`oracle_deck`, `--deck oracle|tarot`, `--card-size tall|poker`, `--cards 12-36`): 28 original symbols in arched, starry windows (`oracle_art.py`); 22 traditional archetype names with original gentle messages, or 36 oracle messages; guide page, matching card backs, cut guides. Messages are reflection prompts, never predictions; the listing FAQ says so. The traditional card names are public domain; the artwork is original (no Rider-Waite or other published imagery).
- **Sticker sheets** (`sticker_sheets`, `--stickers 12-48`, `--theme`): the kids figures filled with the palette's colours plus decorations, white die-cut border, Letter/A4 sheets and transparent PNGs for GoodNotes. Personal-use licence. Not built: Cricut print-then-cut registration marks, cut-line SVGs.

## Bigger libraries (Oct 2026)
- **Kids figures:** 38 (was 16). New: frog, bunny, bear, penguin, duck, elephant, giraffe, lion, bee, crab, shark, airplane, sailboat, train, cupcake, mushroom, unicorn, pizza, apple, flying saucer, planet, balloons. Themes are now: mixed, animals, ocean, garden, vehicles, dinosaurs, treats, farm, jungle, space, arctic, transport, fairytale. Stickers use the same library.
- **Wall-art backgrounds with no AI key:** `--motif` now accepts 13 drawn motifs plus `window-<symbol>` (22 arched-window symbols such as lotus, moon, mountain), `nursery-<figure>` (32 colour-filled kids figures, good for nursery prints) and `pattern-<kind>` (10 seamless pattern panels). `moneyhub styles` lists them all. AI image providers remain optional.

## Kids learning and activity niches (what MoneyHub makes, and what is still open)
Built (all niche-free, printable PDF, Letter + A4, KDP-ready interiors, original artwork):
| Niche / buyer | Product | Command |
|---|---|---|
| Parents of 2-8s who want screen-free fun | Kids coloring book (80 figures, 26 themes incl. Halloween, Christmas, Easter, farm, ocean, space) | `kids_coloring --theme space --age toddler` |
| Parents and teachers of 2-9s: mazes, puzzles | Activity book: mazes with answer pages, dot-to-dot, letter and number tracing, odd-one-out | `activity_book --level toddler|kids|big` |
| Preschool, kindergarten-prep and homeschool | Learning workbook: colours, opposites, days, seasons, feelings, telling time, counting, shadow matching, patterns, word tracing | `learning_workbook --focus colours|words|numbers|time|feelings` |
| Planner kids, journal keepers, kids | Sticker sheets (printable + GoodNotes PNGs) | `sticker_sheets --theme farm` |
| Reflection and self-care | Oracle / tarot-style decks | `oracle_deck --deck tarot` |

Open niches worth adding next (not built): special-needs visual schedules and "first-then" cards; Montessori-style 3-part cards; bilingual (English/Spanish) flashcards; handwriting with cursive; sight-word packs by grade; seasonal bundles (Halloween/Christmas activity books use the same engines); Bible-story coloring (public-domain stories, original art); STEM (shapes, simple machines); classroom printables (name tags, reward charts, behaviour charts, calendar sets).
Notes: educational claims should stay modest ("practice", "ages 3-7"), never "will teach your child to read"; keep original art only (no licensed characters or school-curriculum brand names); the listing already carries the Etsy AI-disclosure line.

## Using open-source SVGs (licence rules)
"Free to download" is not the same as "free to resell". MoneyHub only accepts sets whose licence lets you reuse and redistribute with a notice, checks the licence on every import, and puts the licence text into the buyer's download (`LICENSES.txt`).
| Set | Licence | Status |
|---|---|---|
| Tabler Icons (5,000+ outline, 1,000+ filled) | MIT | built in: `moneyhub assets fetch tabler` / `tabler-filled` |
| Lucide (2,100+) | ISC | built in: `moneyhub assets fetch lucide` |
| Your own folder, CC0 / public domain / MIT / ISC / Apache-2.0 / CC BY 4.0 | as stated | `moneyhub assets add <folder> --name X --license MIT --source URL` |
| OpenMoji, anything CC BY-SA | share-alike | **refused**: derived products would have to carry the same licence |
| Anything CC BY-NC, GPL, unknown | non-commercial / copyleft | **refused** |
| game-icons.net | mostly CC BY 3.0 (per author) | not built in; add per-author CC0 files yourself if you want them |
What it makes: `icon_pack` (planner icon stickers: coloured die-cut badges, printable sheets, PNG, SVG). The icons are recoloured and cut, not resold as-is, and the pack is personal-use. Selling raw copies of someone else's icons as "your clipart" would be weak product and may break marketplace originality rules, so MoneyHub does not do that. Check each marketplace's current rules on third-party and open-source assets before listing. Attribution licences (CC BY) need the credit kept in the listing text as well.

## Bilingual, Montessori and icon posters
- **Bilingual workbook:** `learning_workbook --language es|fr|de`. Words (colours, days, seasons, feelings, opposites, word tracing) are in the language, instructions stay English. **Montessori three-part cards:** `montessori_cards --theme farm2 --language es --count 12` (control, picture and name cards, 4 pictures per sheet).
- **Translation guardrail (QA blocks unreviewed word lists).** A bilingual product shows a "Translations reviewed" QA check and cannot be "ready" until its word list was checked:
  1. `moneyhub translations check --lang all` asks your AI helper (claude CLI or a key) to proofread each list. It reports problems and never edits the words. The first run caught real errors (lowercase seasons in Spanish and French, Spain-only words, "Krake" for octopus, "endormi" for sleepy), now fixed in `src/moneyhub/translations.py`.
  2. An AI check alone gives a **warning**, not a pass: an AI is not a native speaker.
  3. A person proofreads, then `moneyhub translations approve --lang es --by "Name"` records the sign-off and the check passes.
  4. Any edit to the word list changes its fingerprint and cancels earlier reviews, so a changed list is blocked again until re-checked. `moneyhub translations status` shows where each language stands. Records are kept in `out/translations-review.json`.
- **Icon posters:** `--motif icon:lucide` (random simple icon) or `--motif icon:tabler/home` draws one large open-source icon in the palette. The set must be installed first (`moneyhub assets fetch tabler --limit 5200` gets every Tabler icon). **Filled icon stickers:** `icon_pack --collection tabler-filled`.


## Classroom printables
`moneyhub make x classroom_pack --theme farm --names "Ava, Ben, Chloe"` makes one Letter/A4 PDF: name tags (8 per sheet) and fold-over desk plates, four reward charts (stars, numbered steps, sticker boxes, goal tallies), a weekly behaviour chart (traffic-light circles), a faces chart, a chore chart, 12 undated calendar pages, a birthday chart and two star-of-the-week posters. Pictures come from the kids library (`--theme`).
- `--names` (up to 30, comma or new-line separated; the UI has a box) prints each name on a tag and a desk plate. Without names you get 24 blank tags and 4 blank plates with write-in lines. Names are trimmed to 20 characters.
- Calendars are undated on purpose so one pack lasts every year. The charts are one-child-each; print as many as needed.
- Listed without the niche word (`niche_in_copy = False`), like the other kids products. No KDP export (these are cut-and-use sheets, not a book).
- Needs a real-printer check: tag and plate sizes were laid out for 8.5 x 11 in and A4 at Actual size, with about 0.4 in clear margin; confirm your printer does not clip the dashed cut lines.

## Visual schedules
`moneyhub make x visual_schedule --theme treats` makes a 12-page Letter/A4 PDF: a daily routine board (two strips of four steps plus "All done!"), first-then boards (three per page), now / next / later boards, a choice board (one "I want" space plus nine choices), a feelings board, 24 routine picture cards, 15 choice cards (kids-library pictures, `--theme`), 12 feelings cards and a sheet of blank cards.
- Pictograms are drawn in `schedules.py` (flat, soft colours, always the same drawing so a card keeps its meaning). Add a routine step by writing one drawing function and adding it to `ROUTINE`.
- Board spaces and cards are the same size (2.3 x 1.85 in, 15 per sheet). Each has a dashed circle where a small hook-and-loop dot goes (about 3/8 in / 10 mm). The word "Velcro" is a trademark and is flagged by `risk.py`, so listings say "hook-and-loop".
- Wording stays plain: picture cards and boards, no therapy, diagnosis or outcome claims (and no condition names in tags).
- Needs a real check: print, cut and laminate a sheet, fit dots, and confirm the dashed circle sits where a dot fits on your printer's actual-size output.

## Handwriting, sight words and STEM shapes (learning workbook focuses)
`moneyhub make x learning_workbook --focus handwriting|cursive|sightwords|stem [--grade prek|k|1|2|3]`. All four are English only (a bilingual run is refused with a plain message) and each page is a square drawing, so they are KDP-ready like the other focuses.
- **handwriting / cursive** (`handwriting.py`): 26 letter pages (A a ... Z z) with numbered start dots and arrows, traced letters and a practice word on three-line paper, then alternating word-tracing and blank lined pages when you ask for more than 26 pages. Letters are stroke paths, not a font. Print capitals and lower case are drawn in simple ball-and-stick form; cursive is joined lower case only (capitals are not included).
- **sightwords** (`learning.py`, `DOLCH`): the Dolch lists, mapped prek = pre-primer (40 words), k = primer (52), 1 = grade 1 (41), 2 = grade 2 (46), 3 = grade 3 (41). Page types: trace, missing letter, rainbow write, look-cover-write-check. The title carries the grade ("2nd Grade Sight Words Workbook for Kids"). Dolch is a widely used public word list; the listing says "Dolch list" and makes no claim about test results.
- **stem**: 2D shape names, 3D solids with "like a ball" hints, count-the-shapes pages, simple machines (lever, wheel and axle, pulley, inclined plane, wedge, screw) and pattern pages.
- Needs a human eye: the cursive shapes are my own simple strokes. Have someone who teaches cursive check the letters you plan to sell, and compare print letter formation with the style your school uses (D'Nealian and Zaner-Bloser differ).

## Bundles and batches (CLI)
- `moneyhub bundle halloween` (any kids theme: halloween, christmas, easter, valentine, ...) makes a coloring book, activity book, sticker sheets and character clipart with one shared palette, font pair and header, then packs them into `out/bundles/<date>-<name>/`: the zip, `listing.md` (Etsy title, tags, description, price with fee estimates, AI line), `bundle-cover.jpg` and `bundle.json`. Change what goes in with `--types a,b,c`.
- `moneyhub bundle nurse` (any other word) makes a starter kit: weekly planner, habit tracker, budget tracker, checklist pack. `moneyhub bundle 3,4,5 --name "My Bundle"` still combines products you already made.
- `moneyhub make-many x sticker_sheets --count 10 --vary look,theme` makes 10 variations (palette and fonts cycle with `look`, kids themes cycle with `theme`; layouts and art always change) and prints a table of id, QA status, uniqueness and title.
- Each product in a bundle keeps its own licence file. Copy the strictest wording into the listing.
- The wizard and web UI do not have a bundle form yet; these are CLI only.
