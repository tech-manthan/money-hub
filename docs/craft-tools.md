# Craft tools: the complete guide

MoneyHub can use a set of third-party command-line programs (the "craft" tools, from the `storytold` GitHub organisation) as a
**second opinion** on the files it makes, and to polish the sound of the tour video. They are optional, **off by default**, and
MoneyHub works exactly as before without them.

Contents: [What they are](#what-they-are) · [Safety](#safety-read-this-first) · [Install and update](#install-and-update) ·
[Switching them on](#switching-them-on) · [Everyday commands](#everyday-commands) · [What each tool checks](#what-each-tool-checks) ·
[The automatic second opinion](#the-automatic-second-opinion) · [Better sound in the tour](#better-sound-in-the-tour) ·
[Using a tool directly](#using-a-tool-directly) · [Troubleshooting](#troubleshooting) · [For developers](#for-developers) ·
[What is not done](#what-is-not-done)

## What they are

Twelve command-line programs, each a "clean-room" re-implementation of a well-known desktop app, written in Rust. Their
descriptions, from their own repositories:

| Tool | Stands in for | In MoneyHub it is used for |
|---|---|---|
| `pdfcraft` | PDF editor | Opens every PDF and renders its first page |
| `gridcraft` | Spreadsheet | Opens every `.xlsx` and lists its sheets |
| `vectorcraft` | Vector editor | Opens the editable SVGs from `moneyhub edit export` |
| `photocraft` | Image editor | Opens the listing images |
| `cadcraft` | CAD / DXF | Opens the DXF files inside cut-file zips |
| `wordcraft` | Word processor | Opens `.docx` files if a product has one |
| `deckcraft` | Slides | Opens `.pptx` files if a product has one |
| `soundcraft` | Audio editor | Opens audio files; levels the tour narration |
| `filmcraft`, `lightcraft`, `designcraft`, `effectcraft` | Video, photo, layout and effects editors | Not used automatically yet (see [What is not done](#what-is-not-done)) |

Two more repositories in the same organisation, `artcraft` and `craft-launcher`, are desktop apps, not command-line tools.

## Safety: read this first

- These are **third-party programs that nobody here has audited**. MoneyHub runs them only on your own files, with a time limit,
  and treats everything they say as advice.
- **They can never fail a product.** A missing, slow, crashing or disagreeing tool is skipped. The most the automatic check can
  do is add one warning line.
- Nothing is sent anywhere by MoneyHub. Whether a tool itself uses the network is a question for its own repository.
- The installer downloads only from the GitHub releases of `github.com/storytold/*`, and checks each download against the
  checksum file the release publishes. A mismatch keeps your old version and installs nothing.
- Read the project before you trust it: `https://github.com/storytold/<tool>`.
- Claude Code's own safety check blocks Claude from running these programs. When you work with Claude, you run them yourself
  by starting the line with `!`, and Claude reads the output.

## Install and update

You need the GitHub command line (`brew install gh`, then `gh auth login`).

```
bash scripts/install_craft_tools.sh                 # all of them
bash scripts/install_craft_tools.sh pdfcraft gridcraft   # only some
```

What it does, per tool:

1. Finds the latest release and the macOS download (it prefers a universal or arm64 command-line build).
2. Downloads it and the release's checksum file, and verifies it. If the release has no checksum file it **warns that the
   download is not verified**.
3. Unpacks it into `tools/craft/<tool>/current/` and writes the version to `tools/craft/<tool>/VERSION`.
4. Skips repositories with no release or no macOS file, and tells you.

**Updating is running the same command again.** A tool is only replaced when its newest release tag differs from the one in
`VERSION`, and only after the checksum matches. To check for updates weekly, add a line with `crontab -e`:

```
0 9 * * 1 cd ~/social-media/money-hub && bash scripts/install_craft_tools.sh >> ~/craft-update.log 2>&1
```

`tools/` is in `.gitignore`, so the programs are never committed.

## Switching them on

Everything is off by default. There are three ways to change the same settings; use whichever you like.

**1. Settings page** (`/settings` in the web app), panel **Second-opinion tools**:

- **Use them** is the master switch.
- **Check every new product** adds the automatic check after each product is made.
- One tick-box per tool, with a badge showing whether it is installed and its version.

**2. Command line:**

```
moneyhub tools                                   # what is installed and what is switched on
moneyhub tools --master --enable pdfcraft,gridcraft,photocraft --verify-after-make
moneyhub tools --enable all                      # every checker
moneyhub tools --disable soundcraft              # one off
moneyhub tools --no-master                       # everything off at once
```

**3. File:** `moneyhub.local.yaml` (hidden from git; the shipped defaults are in `moneyhub.yaml`):

```yaml
craft:
  enabled: true             # master switch
  verify_after_make: true   # the automatic check after each new product
  timeout: 90               # seconds per tool call
  tools:
    pdfcraft: true
    gridcraft: true
    soundcraft: true
```

A tool is used automatically only when **both** the master switch and its own switch are on. A switched-off tool is never
started.

## Everyday commands

```
moneyhub tools                  # list the tools, versions, paths, and which are on
moneyhub verify 12              # open product 12's files with the tools and print ok / FAIL per file
moneyhub craft pdfcraft info x.pdf       # run any tool yourself (see "Using a tool directly")
```

`moneyhub verify <id>` ignores the on/off switches, because you asked for it explicitly. It prints one line per check and
writes `craft-verify.json` into the product's folder. It exits with status 1 when something could not be opened, so you can use
it in a script.

## What each tool checks

`moneyhub verify` looks in the product folder and sends each file to the matching tool:

| Files | Tool | Check | Command it runs |
|---|---|---|---|
| `product/*.pdf` | pdfcraft | opens and summarises | `pdfcraft-cli info FILE` |
| `product/*.pdf` | pdfcraft | page 1 renders to an image | `pdfcraft-cli render FILE --page 1 --dpi 48 --out x.png` |
| `product/*.xlsx` | gridcraft | opens and lists sheets | `gridcraft-cli info FILE --json` |
| `editable/**/*.svg` (up to 12) | vectorcraft | opens as a vector document | `vectorcraft-cli info FILE` |
| `images/**/*.jpg, *.png` (up to 6) | photocraft | opens as an image | `photocraft-cli info FILE --compact` |
| DXF inside `product/*.zip` (up to 3 per zip) | cadcraft | opens as a drawing | `cadcraft-cli info FILE.dxf` |
| `product/*.docx` | wordcraft | opens as a document | `wordcraft-cli info FILE` |
| `product/*.pptx` | deckcraft | opens as a presentation | `deckcraft-cli info FILE` |
| audio files (up to 3) | soundcraft | opens as audio | `soundcraft-cli info FILE` |

**"ok" means the tool opened the file and exited cleanly.** It is a second reader agreeing the file is not broken. It is not
proof that the file looks right, that formulas recalculate in Excel or Numbers, or that a cutting machine will cut it. Those
still need a real device.

Real output seen on a finished product: `pdfcraft` reports annotations, bookmarks, encryption and form fields; `cadcraft`
reports entity counts and extents (a cut-file star came back as one polyline 4.7 x 5.4 in); `vectorcraft` reports artboards and
fonts.

## The automatic second opinion

When **Use them**, **Check every new product** and at least one tool are on, every product made by `moneyhub make`, the web
wizard, `batch`, `bundle` and `make-many` gets one extra line in its quality checks:

- `Second opinion (craft tools)`: **pass**, with how many checks passed and which tools did them; or
- **warn**, naming the files a tool could not open, with a pointer to `craft-verify.json`.

Rules that keep your products safe:

- It is **warn-only**. It can never make a product "not ready".
- Tools that are off are not started. Tools that are not installed are skipped silently.
- Any error inside it is swallowed; generation carries on.
- The result is also saved in the product folder as `craft-verify.json` (tool list plus every finding, with the tool's own
  output trimmed to 300 characters).

## Better sound in the tour

`python scripts/record_tour.py` records the narrated tour videos. Its narration is built as one mixed WAV file. With
`soundcraft` switched on, that file is levelled by `soundcraft-cli convert IN OUT --bit-depth 16 --rate 44100 --normalize`,
scaled back to a peak of 0.9 so the video encoder cannot clip, and used for the video.

- It uses the same switches as everything else: master switch plus the `soundcraft` tick.
- If `soundcraft` is off, missing, fails, returns silence or returns a clearly shorter file, the original narration is used
  unchanged.
- The script prints `narration levelled with soundcraft` when it was used.
- The tour records against a throwaway copy of MoneyHub, so the switches you save during the recorded Settings segment never
  touch your own settings. The sound step reads **your** settings.

The tour also has its own short segment (`tools.mp4`, shown in the docs page) that shows the Settings panel being switched on.

## Using a tool directly

`moneyhub craft <tool> <arguments>` runs any of the twelve tools, with a time limit (`--timeout`, default 300 seconds) and
without ever raising an error in MoneyHub:

```
moneyhub craft pdfcraft info my.pdf
moneyhub craft pdfcraft combine a.pdf b.pdf --out both.pdf
moneyhub craft pdfcraft extract in.pdf --pages 1,3,5 --out some.pdf
moneyhub craft pdfcraft text my.pdf
moneyhub craft gridcraft cat my.xlsx --range A1:D20
moneyhub craft gridcraft convert my.xlsx my.csv
moneyhub craft vectorcraft convert in.svg out.pdf
moneyhub craft vectorcraft commands
moneyhub craft cadcraft convert cut.dxf cut.png
moneyhub craft photocraft convert in.png out.jpg --quality 85
moneyhub craft wordcraft convert in.docx out.pdf
moneyhub craft soundcraft convert in.wav out.wav --normalize
```

Each tool prints its full usage with `--help`, for example `moneyhub craft pdfcraft --help`. The usage text for all twelve was
saved while this was built in `tools/craft-help.txt` (if you ran the help-gathering command).

Two of the tools can also act as an **MCP server** for Claude Code (`vectorcraft-cli mcp`, `pdfcraft-cli mcp`,
`gridcraft-cli mcp` and others), so Claude could edit a file with them directly. That changes your Claude Code configuration, so
it is not set up for you. If you want it:

```
claude mcp add vectorcraft -- ~/social-media/money-hub/tools/craft/vectorcraft/current/vectorcraft-cli-0.8.0-macos-universal/vectorcraft-cli mcp
```

The path contains the version, so point it at the folder under `current/` and re-run it after an update.

## Troubleshooting

| What you see | What it means | Fix |
|---|---|---|
| `moneyhub tools` shows `-- ... not installed` | The tool is not under `tools/craft/` | Run `bash scripts/install_craft_tools.sh <tool>` |
| Installer says `has no macOS download, skipped` | That repository does not publish a macOS file | Build it from source, or leave it out |
| Installer says `CHECKSUM FAILED` | The download does not match the published checksum | Nothing was installed. Try again later; if it repeats, do not use that release |
| `WARNING: no checksum file published` | The release has no checksum file | You decide whether to trust it; MoneyHub installed it unverified |
| `verify` shows `FAIL ... timed out` | The tool took longer than `craft.timeout` | Raise `timeout` in settings, or check the file is not huge |
| `verify` shows `FAIL ... could not start` | macOS refused to run the file | Open System Settings, Privacy and Security, and allow it, or run it once from Terminal |
| No "Second opinion" line on a new product | Master switch, `verify_after_make` or every tool is off, or none are installed | `moneyhub tools` shows the state |
| Settings panel shows a tool as installed but `verify` skips it | The tool is installed but switched off | Tick it (only the automatic check needs the tick; `verify` uses all) |
| The tour is silent | No voice engine was found | `moneyhub voices install`, then record again |
| The tour sound did not change | `soundcraft` is off, or the tool failed and the original was kept | Check `moneyhub tools`, run the tour again and look for `narration levelled` |

## For developers

- Code: `src/moneyhub/crafttools.py`. Locating a tool (`find_tool`), running one without raising (`run`), the checks
  (`verify_product`), the settings (`settings_view`, `save_settings`), the automatic check (`second_opinion`) and the sound step
  (`polish_wav`).
- Where tools are looked up: `MONEYHUB_CRAFT_DIR` if set, else `tools/craft` next to the project, else `<name>-cli` on `PATH`.
- Settings keys: `craft.enabled`, `craft.verify_after_make`, `craft.timeout`, `craft.tools.<name>`.
- The automatic check is called once in `pipeline.generate`, just before the risk scan. Nothing else in the pipeline knows about
  the tools.
- **Adding a check:** add a block in `verify_product` guarded by `on("<tool>")`, add the tool to `CHECKERS` if it is new, and
  add a test in `tests/test_crafttools.py`. Tests use stand-in shell scripts (`_fake`), so they need no real tool.
- **Rules:** a tool that is off must never be started; every failure mode returns `ok=False` or `None` and never raises; the
  automatic check may only `pass` or `warn`.

## What is not done

- `filmcraft`, `lightcraft`, `designcraft` and `effectcraft` have no automatic job. They are editors and renderers that
  produce files, so using them needs a decision about which output they should change. They work through `moneyhub craft`.
- The automatic check does not look inside every zip (only the first three DXF files per zip are opened).
- Only `soundcraft` normalising is used for sound. The launch videos made by `moneyhub brag` are not run through it yet.
- Nothing here replaces the real-device checks in `docs/owner-verification.md`: printing, cutting, Excel or Numbers
  recalculation, and a native speaker for the translations.
