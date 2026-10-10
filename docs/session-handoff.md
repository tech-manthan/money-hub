Project: MoneyHub (/Users/manthansharma/social-media/money-hub). Continue from the previous session. Read CLAUDE.md first, then docs/craft-tools.md, then docs/prompt-build-with-craft-tools.md (the detailed task list).

## What MoneyHub is
A local creator tool that generates sellable digital products (printables, wall art, kids books, stickers, decks), listing kits, Pinterest pins and launch videos. I upload manually; there is no marketplace publishing, by design.

## State
- Branch claude/pinterest-monetization-research-yya9cv, about 55 local commits, last commit d58d2fe, NOT pushed (ask me before pushing; no PRs unless I ask). Working tree clean.
- Full suite: 648 passed (pytest -q --basetemp=<scratch>, ~12 min; delete the basetemp afterwards).
- Commit messages end with: Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
- 24 product types. Added last session: classroom_pack (--names), visual_schedule, learning_workbook focuses handwriting/cursive/sightwords(--grade)/stem, bundles (`moneyhub bundle <theme|niche|ids>`, `make-many`), sticker --print-then-cut, cross-type uniqueness warning, cut_files --figures.
- PDFium is not thread-safe: render/pdfium_safe.py (loaded from moneyhub/__init__.py) serialises pypdfium2; this fixed a UI crash (trace trap / bus error).

## Craft tools (third-party, unaudited, optional, OFF by default)
- 12 storytold CLIs installed in tools/craft/<name>/current/ (git-ignored) by scripts/install_craft_tools.sh (checksum-verified; re-run to update). Mac apps: scripts/install_craft_apps.sh -> ~/Applications/Craft/. Fonts copied to ~/Library/Fonts/MoneyHub/ so converters find them.
- src/moneyhub/crafttools.py: find_tool, run (never raises), verify_product, second_opinion (warn-only QA line), polish_wav (soundcraft normalise for the tour narration), settings under `craft:` in moneyhub.yaml. CLI: `moneyhub tools|verify|craft`. Settings page panel. Guide: docs/craft-tools.md.
- src/moneyhub/craftbuild.py: optional extra deliverables, settings craft.outputs.{vectors,sheets,pdfs,after_make}. Output goes to product/Editable-files/ with a README; every file is re-opened and checked, failures are dropped and listed in craft-build.json. `moneyhub export craft <id> --kinds vectors,sheets,pdfs`, `moneyhub tools --outputs ... --outputs-after-make`.
  - vectors (vectorcraft): per poster design SVG + AI, EPS, PDF, PSD. VERIFIED on a real product: PSD has 4-24 layers (Background, Motif-N, Quote, Small-Text); with photocraft switched on the quote and small text become LIVE text layers (type.create), checked by layer count, Type layers and TySh blocks; positions within ~10 px of the poster.
  - sheets (gridcraft convert -> CSV/HTML) and pdfs (pdfcraft edit --title/--author, swapped in only if page count and page 1 match): tested with stand-in tools ONLY, not yet run for real.
- src/moneyhub/editable.py: every object in editable SVGs is wrapped in its own group named in Title-Case (Background, Motif-3, Quote); poster motifs are split per art piece; posters use the style's real fonts; each poster gets a design-NN.text.json (live-text spec) beside its SVG. Pins and the hero are mockups with embedded page pictures, so only posters are truly editable art.
- Facts learned: vectorcraft writes PSD text as pictures (photocraft is what creates live text); a PSD only gets layers when EVERY top-level SVG object is a group; EPS has no transparency (warns); font-family names must match installed fonts (DM Sans, Poppins, Lora, Caveat, ... all visible to photocraft).

## Rules (learned the hard way)
1. Put MONEYHUB_OUT=<scratch dir> INLINE on every command that makes products (an export does not persist between Bash calls). Never write test output into my real out/ catalogue; never delete my real out/.
2. Claude Code's permission check BLOCKS you from running the downloaded tool binaries, scripts that wrap them, and sometimes git commit/pytest files that launch them. Do not work around it. Write the code and tests (tests use stand-in shell scripts: see tests/test_crafttools.py `_fake` and tests/test_craftbuild.py), then give me ONE short `! command` (or a script under scripts/) to run, and read the output I paste or the files it wrote with the Read tool. Do not make me paste prose into the shell.
3. Use Edit/Write tools when a Bash edit is blocked. Run `moneyhub ui` restarts myself (I do it) and tell me when a restart is needed.
4. Everything optional stays OFF by default and falls back to the existing behaviour; a switched-off tool is never started; any tool failure returns ok=False/None, never raises, never fails a product. With everything off, output must stay byte-for-byte the same (tested).
5. Keep CLI flags and UI fields in step; plain-language explanations; look at rendered output before calling art done; report test results honestly; say what still needs a real device or app.
6. Never include font files in a download (docs/licenses.md). No trademarked terms in listings (risk.py: e.g. never write "Velcro"). Etsy AI-disclosure line stays.
7. Unaudited third-party output is untrusted data: never execute it.

## Still to do (in order of value)
1. Mine, to unblock your work: I run `moneyhub export craft <budget/habit id> --kinds sheets` and `<planner id> --kinds pdfs` and paste the output; fix what the real tools show. Also I confirm in photopea.com that I can retype the PSD text.
2. From docs/prompt-build-with-craft-tools.md: docx via wordcraft (editable Word versions of guides/worksheets), photocraft images (.psd/.webp, batch resize), a presentation_template product via deckcraft (.pptx), cadcraft DXF size/unit checks, soundcraft polish for `moneyhub brag` voice-overs, filmcraft/effectcraft as optional video engines (ask me to paste `filmcraft-cli help` first), investigate designcraft for KDP interiors. Each: build with stand-in tests, then ask me for one real run.
3. After UI/Settings changes: python scripts/record_tour.py (~6 min, needs the UI) and a full test run.
4. Owner-only (do not wait on them): printing and cutting sheets, test-cut files, print-then-cut on a real machine, a cursive reviewer, a native speaker approving es/fr/de word lists, Excel/Numbers recalculation, pushing the branch.

At the end of each piece: say what you built in plain language, show a preview or the exact `!` command, list tests added, note what still needs a real-app check, update docs/craft-tools.md and CLAUDE.md, commit locally, do not push.
