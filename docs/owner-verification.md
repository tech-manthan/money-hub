# Owner verification guide (items that need a real device, account or key)

These checks cannot be done by Claude Code because they need your accounts, keys or hardware. Do them in any order. After each one, note what worked and what looked wrong, then give that note to Claude Code (a screenshot or the exact error text is best) and it will fix the generator and add a test.

**Before you start**
```bash
cd ~/social-media/money-hub && source .venv/bin/activate
moneyhub doctor                      # fix anything it reports first
moneyhub ui --port 8766              # RESTART the UI after any code change (Ctrl+C, then run again).
                                     # A UI left running from before an update shows "Internal Server Error".
```
Make one product of each type to test with. Product ids are shown on the home page and in `moneyhub list`:
```bash
moneyhub make "nurse" weekly_planner --llm builtin --sizes letter,tablet,eink
moneyhub make "nurse" habit_tracker  --llm builtin
moneyhub make "nurse" guided_journal --llm builtin
```
`--llm builtin` is offline and free, which is fine for layout checks.

---

## 5. Verify on real platforms

### 5a. Notion import
1. `moneyhub export notion <id>` (or **Sell it somewhere else > Notion** on the product page).
2. The pack is `<product folder>/exports/<name>-notion-import.zip`; a `...-notion-guide.md` sits beside it.
3. In Notion: sidebar **Import** (bottom of the left sidebar, or `...` menu > Import) > **Text & Markdown** > choose the zip.
4. Check: the **Start Here** page opens first; pages are in sensible order; the CSV files became databases (Weeks, Habits, etc.) with the right columns; links between pages work; checkboxes appear as checkboxes, not text.
5. Note what is broken (for example "database columns all text", "images missing").

### 5b. Canva import
1. `moneyhub export canva <id>`. Files go in `exports/canva/`: `...-for-canva.pdf`, `brand-kit.json`, `HOW-TO-CANVA.md`, a template-link PDF.
2. In Canva: **Create a design > Import file** > the `-for-canva.pdf`. Open the result.
3. Check: each page is its own Canva page; text is **editable text** (click it) and not one flattened image; fonts match or are replaced by something close; page size is right.
4. Create the buyer template link: Share > Template link > copy. Run `moneyhub export canva <id>` again with the link in the UI box (or the CLI `--link` option if you have it), and open the generated link PDF to see it is clickable.

### 5c. KDP (Amazon paperback)
1. `moneyhub export kdp <id> --trim 6x9 --paper white`. Optional: `--cover-image my-art.jpg` (JPG/PNG, ideally about 1,000 px wide per inch of front cover at 300 dpi; the check tells you) and `--no-cover-text` if your art already has the title.
2. Files in `exports/kdp/`: the interior PDF, the finished cover PDF (`...-cover-6x9.pdf`), a guide-line template, `cover-spec.json`, `KDP-GUIDE.md`. Read `KDP-GUIDE.md` first.
3. Go to kdp.amazon.com > **Create > Paperback**. Fill details. In **Content**: choose your trim size and paper to match the export, bleed **No bleed** for the interior, upload the interior PDF, then upload the cover PDF (choose "Upload a cover you already have").
4. Click **Launch Previewer**. Check every page for: content inside the blue/safe lines, no text near the gutter, the right page count, spine text readable (only allowed from 79 pages), nothing in the barcode area on the back cover.
5. KDP shows the exact spine width. **Compare it with `cover-spec.json` (`spine_in`).** If they differ, tell Claude Code both numbers so the paper-thickness constant can be fixed. Do not publish the book; you can stop at the previewer or save as draft.
6. Order a proof copy before selling anything.

### 5d. E-ink devices (reMarkable, Kindle Scribe, Boox)
1. Make the e-ink size (shown above) or tick **e-ink** in the wizard. File is `...-eink-hyperlinked.pdf`.
2. Copy to the device (reMarkable: desktop app or my.remarkable.com; Kindle Scribe: Send to Kindle; Boox: USB or its app).
3. Check: page fits without tiny margins; lines are dark enough but not heavy; tab links jump to the right pages; text is readable at the device's zoom.

### 5e. GoodNotes / Notability links
1. Make the **tablet** size (`--sizes tablet`) and AirDrop or email the `...-tablet-hyperlinked.pdf` to your iPad.
2. Open in **GoodNotes** (Import) and in **Notability** if you have it.
3. Check: tapping the Home / Goals / Months / Weeks / Notes tabs jumps to the right page in **read mode** (links often only work outside pen mode); the cover buttons work; handwriting does not move the links.

### 5f. Spreadsheets (habit tracker, budget tracker)
1. Open the `.xlsx` in **Excel** and in **Numbers**, and upload to **Google Sheets** (File > Import).
2. Check: checkboxes tick; percentages and totals update; charts draw; drop-down lists work; the sheet protection lets you type only in the input cells; conditional colours appear. Numbers and Sheets handle some Excel features differently, so list anything that shows `#NAME?`, `#VALUE!` or plain `0`.

---

## 6. CI on GitHub (your call to push)
The branch is ahead of GitHub by several commits. Pushing makes them public on your repo, so do it only when you are happy.
```bash
git status                             # should be clean
git push origin claude/pinterest-monetization-research-yya9cv
```
1. Open https://github.com/tech-manthan/money-hub > **Actions** > the **tests** run. It runs 8 jobs (Ubuntu and macOS x Python 3.11 to 3.14). The first run takes 10 to 20 minutes.
2. Green means done. If a job is red, click it, expand the failing step, and copy the last 40 lines (or use **Download log archive**). Paste them to Claude Code and it will fix them.
3. Typical causes: a missing system library on Linux (WeasyPrint needs Pango), a fonts difference, or a test that assumes macOS paths.
4. Optional: in the repo **Settings > Branches**, protect `main` so only green runs can merge.

---

## 7. Image-AI providers (Hugging Face, Together, OpenAI)
These make AI backgrounds for **wall art**. They cost money or use a free quota, so check each provider's pricing page first.
1. Create a key: Hugging Face https://huggingface.co/settings/tokens (a "Read" token is enough for inference; free quota is small), Together https://api.together.ai/settings/api-keys, OpenAI https://platform.openai.com/api-keys (needs billing set up).
2. In the UI open **Settings**, paste the key in its box, **Save**, then press **Test**. The result says ok or gives the provider's error (bad key, no credit, model not enabled). Keys are saved to the git-ignored `.env` (file mode 0600), never in code.
   Or do it by hand: add a line such as `HF_TOKEN=hf_xxx` to `.env`, then restart the UI.
3. Make a wall-art set with the provider:
   ```bash
   moneyhub make "gardening" wall_art --llm builtin --art-provider huggingface
   moneyhub make "gardening" wall_art --llm builtin --art-provider together
   moneyhub make "gardening" wall_art --llm builtin --art-provider openai
   ```
   `moneyhub styles` lists which providers are ready (`ok`) and which are not (`--`). Local option: run your own image server and set `MONEYHUB_ART_URL`.
4. Open the previews. Check: the picture is behind the text and not over it; text is still readable (a light overlay is added); no artefacts at the edges; the image is sharp when printed at 12x18 in.
5. Report: provider, the error text from **Test**, and a screenshot if the art looks wrong. Also check the provider's licence terms before selling images made with it (you are responsible for that).

---

## 8. Penpot (editing the SVGs)
1. Export editable files: `moneyhub edit export <id>` (or the button on the product page). Output: `<product folder>/editable/` with `pins/`, `listing/`, `posters/` (wall art), `fonts/`, `BRIEF.md`.
2. Get Penpot: hosted at https://penpot.app (free account), or locally with Docker Desktop running: `bash editor/penpot/run.sh`, then open http://localhost:9001.
3. Create a project and a file. Drag a few SVGs from `pins/`, `listing/` and `posters/` onto the canvas.
4. Check: text is still **editable text** (double-click it); layers have names such as `title`, `badge-1`, `motif`; shapes are separate objects; fonts look right. If they are missing, upload the files in `editable/fonts/` under Team > Fonts (for editing only, never sell them).
5. Change a headline and a colour, then **export the board as PNG/JPG with the same file name** as the SVG into `editable/edited/`.
6. `moneyhub edit import <id>` and confirm the product images were replaced and `upload-package.zip` was rebuilt.
7. Report what broke on import: for example "text became curves", "clipping lost", "gradient missing", "fonts wrong".

---

## 9. Cut files in Cricut Design Space / Silhouette Studio (needs a cutting machine)
MoneyHub checks the files itself ("Opens in cutting software" in QA re-reads every SVG and DXF), but only the real apps and a real blade prove they cut well.
1. Make a bundle: `moneyhub make "x" cut_files --llm builtin`. Unzip the `-SVG.zip` and `-DXF.zip` from `out/products/<id>/product/`.
2. **Cricut Design Space** (free, https://design.cricut.com): New Project > Upload > Upload Image > pick two or three `.svg` files > Save > Add to canvas. Check: the size reads 6 in, holes (stars, hearts with a hole) are see-through, nothing is merged into one blob.
3. **Silhouette Studio** (free Basic Edition; DXF needs Designer Edition or higher, SVG needs Designer Edition): File > Open the `.dxf`. Check the same three things, and that Cut Style shows lines around every outline.
4. Test-cut one design on scrap cardstock or cheap vinyl at 3-4 in. Check: small points and thin bridges come away clean, the holes drop out, the blade does not tear the thinnest part.
5. Report: app and version, file name, and what you saw. If a bridge tore, tell me the design name; I will raise the minimum gap (now 1.5 mm).
Free alternative to look at files without a machine: Inkscape (https://inkscape.org) opens both SVG and DXF.

---

## What to send back
For each item above: **what you did, what you expected, what you saw** (screenshot or exact error text), and the product id. One short note per failing check is enough.
