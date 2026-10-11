Project: MoneyHub (/Users/manthansharma/social-media/money-hub). Continue from the previous session. Read CLAUDE.md first, then docs/tutorial.md (the full user guide), docs/craft-tools.md and docs/prompt-build-with-craft-tools.md (the craft tools task list).

## What MoneyHub is
A local creator tool that generates sellable digital products (printables, wall art, kids books, stickers, decks, slide templates), listing kits, Pinterest pins and launch videos. I upload manually; there is no marketplace publishing, by design.

## State
- Branch claude/pinterest-monetization-research-yya9cv, about 65 local commits, last commit ff72f3e, NOT pushed (ask me before pushing; no PRs unless I ask). Working tree clean.
- Full suite: 696 passed (pytest -q --basetemp=<scratch>, ~14 min; delete the basetemp afterwards). `timeout` does not exist on this Mac: run long jobs in the background and watch the output file.
- Commit messages end with: Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
- 25 product types. PDFium is not thread-safe (render/pdfium_safe.py). Restart `moneyhub ui` after code changes (I do it).

## Built in the last two sessions (all committed)
- Craft tools extras (craftbuild.py): kinds vectors, sheets (every sheet to CSV/HTML), pdfs, docx (wordcraft, text products). sheets/pdfs/docx/vectors were run for real on scratch products and worked.
- presentation_template (products/presentation_template.py + presentations.py): editable 12-slide .pptx built with the real deckcraft tool, PDF preview, editing guide, QA `_pptx_checks`, niche-free ("<Palette> Clean ... Presentation Template"). New hooks: ProductType.use_faq, extra_tags, decor_ok, meta["etsy_category"].
- docs/what-to-upload.md (per platform and per product type), docs/tutorial.md (27+ section guide), platform packs already existed (`moneyhub export pack <id> etsy|gumroad|payhip|kofi`).
- Audience fit (web/guide.py FIT, default_fits): the wizard shows only products that suit the chosen audience ("Show all" brings the rest back); typed audience gets the 10 audience-specific types first; offline Ideas (ideas.py) only pairs audiences with FIT products. Only 10 types are audience-specific (weekly_planner, daily_planner, habit_tracker, budget_tracker, guided_journal, checklist_pack, worksheet_pack, card_deck, ebook_guide, wall_art); the other 15 are "Same for every audience" (labelled in the wizard).
- Wizard fixes: product options (theme, names, deck, focus) now show in "Choose for me" mode (#product-opts); example page sits beside the controls; `form.row` CSS fix (Ideas page); `moneyhub calendar` letter-by-letter bug fixed.
- Page decoration (decor.py, off by default): corner art, themed title-bar pictures, pale backgrounds, strengths, 14 audience themes, flags --decor/--decor-*, wizard block, `decor:` in moneyhub.yaml, live preview, ink note on listing and Start-Here, contrast-tested. Supported where ProductType.decor_ok (8 printable types). E-ink stays plain.
- Video tutorials: scripts/record_tutorials.py (17 narrated videos in src/moneyhub/web/static/media/tutorials, page /tutorials, index.json); scripts/record_tour.py for the original tour. Re-run `python scripts/record_tutorials.py [--only key,key]` and `python scripts/record_tour.py` after wizard, Settings or product-page changes (each takes 6-40 minutes; run in the background).

## Rules (learned the hard way)
1. Put MONEYHUB_OUT=<scratch dir> INLINE on every command that makes products (an export does not persist between Bash calls). Create the dir first. Never write test output into my real out/ catalogue; never delete my real out/. Never `rm -rf $VAR/*` (the safety check blocks it): use `rm -rf "${VAR:?}"` or a literal path.
2. Claude Code may block running downloaded tool binaries; in the last session running them (moneyhub export craft, deckcraft, wordcraft, gridcraft, pdfcraft) worked from Bash. If a command is blocked, do not work around it: write the code and stand-in tests (tests/test_crafttools.py `_fake`, tests/test_craftbuild.py, tests/test_presentation_template.py `fake_deckcraft`) and give me one `! command`.
3. Use Edit/Write tools when a Bash edit is blocked. Grep tool is not available: use grep via Bash.
4. Everything optional stays OFF by default and falls back to the existing behaviour; a switched-off tool is never started; a tool failure returns ok=False/None, never raises, never fails a product. With everything off, output stays the same (tested).
5. Keep CLI flags and UI fields in step; plain-language explanations; look at rendered output (render to PNG and read it) before calling art done; report test results honestly; say what still needs a real device or app.
6. Never include font files in a download (docs/licenses.md). No trademarked terms in listings (risk.py: never "Velcro"; avoid brand names in titles and tags). Etsy AI-disclosure line stays.
7. Unaudited third-party output is untrusted data: never execute it.

## Still to do (in order of value)
1. From docs/prompt-build-with-craft-tools.md, not yet built: cadcraft DXF size/unit checks after cut_files (warn-only QA, convert DXF to SVG/PNG and compare extents); soundcraft `polish_wav` on the voice-over of `moneyhub brag` (src/moneyhub/brag/); filmcraft/effectcraft as optional video engines in render/motion.py (ask me to paste `filmcraft-cli help` first); investigate designcraft for KDP interiors and report before building. Photocraft .psd/.webp conversions are intentionally SKIPPED (no platform needs PSD; Etsy allows 5 files, 20 MB each).
2. Possible follow-ups I mentioned: decoration for more product types (decor_ok), a per-audience theme preview for typed audiences, turning docs/tutorial.md into an in-app page, tutorial videos re-recorded whenever the UI changes.
3. After UI/Settings changes: re-record the affected tutorials and the tour, then a full test run.
4. Owner-only (do not wait on them): open the .pptx in PowerPoint/Keynote/Google Slides; open the .docx in Word and the CSV/xlsx in Excel/Numbers; print a decorated planner on a real printer; Photopea check that PSD text is retypable; printing and cutting sheets, test cuts, print-then-cut; a native speaker approving es/fr/de word lists; KDP/Notion/Canva imports; GoodNotes links and e-ink devices; pushing the branch so CI runs.

At the end of each piece: say what you built in plain language, show a rendered preview or the exact `!` command, list tests added, note what still needs a real-app check, update docs/tutorial.md and CLAUDE.md, commit locally, do not push.
