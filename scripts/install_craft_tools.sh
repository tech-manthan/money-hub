#!/bin/bash
# Installs (and later updates) the macOS releases of the storytold "craft" apps into ./tools/craft/ next to this project.
#
#   bash scripts/install_craft_tools.sh              # all repos below
#   bash scripts/install_craft_tools.sh pdfcraft     # only some
#
# For each repo it: finds the latest release, picks the macOS asset, verifies it against the release's
# checksum file when one is published, and replaces the old copy only when the checksum matches.
# Re-run it any time to update. Nothing is executed from the downloads; zip / tar / dmg are only unpacked
# (a dmg is mounted read-only, copied, and unmounted). Run the tools yourself once you are happy with them.
# These are third-party, unaudited programs: read the repo before you run anything.
set -u
ORG=storytold
DEFAULT_REPOS="vectorcraft pdfcraft photocraft wordcraft gridcraft deckcraft filmcraft soundcraft lightcraft cadcraft artcraft designcraft effectcraft craft-launcher"
REPOS="${*:-$DEFAULT_REPOS}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)/tools/craft"
mkdir -p "$ROOT"
command -v gh >/dev/null || { echo "Install the GitHub CLI first: brew install gh && gh auth login"; exit 1; }

install_one() {
  local r="$1" new old tmp assets asset sums dest
  new=$(gh release view -R "$ORG/$r" --json tagName -q .tagName 2>/dev/null)
  if [ -z "$new" ]; then echo "[$r] no release published, skipped (build from source if you need it)"; return; fi
  old=$(cat "$ROOT/$r/VERSION" 2>/dev/null)
  if [ "$new" = "$old" ]; then echo "[$r] up to date ($new)"; return; fi
  assets=$(gh release view -R "$ORG/$r" --json assets -q '.assets[].name')
  # prefer a universal or arm64 command-line build, then any macOS archive or dmg
  asset=$(echo "$assets" | grep -i -E 'macos|darwin|osx|\.dmg$' | grep -v -E '\.(sha256|sig|asc|zsync)$' | \
          grep -i -E 'cli.*(universal|arm64|aarch64)|(universal|arm64|aarch64).*cli' | head -1)
  [ -z "$asset" ] && asset=$(echo "$assets" | grep -i -E 'macos|darwin|osx|\.dmg$' | grep -v -E '\.(sha256|sig|asc|zsync)$' | grep -i -E 'universal|arm64|aarch64' | head -1)
  [ -z "$asset" ] && asset=$(echo "$assets" | grep -i -E 'macos|darwin|osx|\.dmg$' | grep -v -E '\.(sha256|sig|asc|zsync)$' | head -1)
  if [ -z "$asset" ]; then echo "[$r] $new has no macOS download, skipped"; return; fi
  echo "[$r] ${old:-none} -> $new  ($asset)"
  tmp=$(mktemp -d)
  gh release download "$new" -R "$ORG/$r" -p "$asset" -D "$tmp" || { echo "[$r] download failed"; rm -rf "$tmp"; return; }
  sums=$(echo "$assets" | grep -i -E 'sha256|checksum' | head -1)
  if [ -n "$sums" ]; then
    gh release download "$new" -R "$ORG/$r" -p "$sums" -D "$tmp" || { echo "[$r] checksum file download failed, not installing"; rm -rf "$tmp"; return; }
    if ! (cd "$tmp" && grep -F "$asset" "$sums" | shasum -a 256 -c -); then
      echo "[$r] CHECKSUM FAILED, kept the old version"; rm -rf "$tmp"; return
    fi
  else
    echo "[$r] WARNING: no checksum file published; the download is NOT verified"
  fi
  dest="$ROOT/$r/current"
  rm -rf "$dest"; mkdir -p "$dest"
  case "$asset" in
    *.zip) unzip -q "$tmp/$asset" -d "$dest" ;;
    *.tar.gz|*.tgz) tar -xzf "$tmp/$asset" -C "$dest" ;;
    *.dmg)
      mnt=$(mktemp -d)
      if hdiutil attach -readonly -nobrowse -mountpoint "$mnt" "$tmp/$asset" >/dev/null; then
        cp -R "$mnt"/. "$dest"/ ; hdiutil detach "$mnt" >/dev/null
      else
        echo "[$r] could not open the dmg; kept the file only"; cp "$tmp/$asset" "$dest"/
      fi ;;
    *) cp "$tmp/$asset" "$dest"/ ;;
  esac
  echo "$new" > "$ROOT/$r/VERSION"
  rm -rf "$tmp"
  echo "[$r] installed in tools/craft/$r/current"
}

for r in $REPOS; do install_one "$r"; done
echo
echo "Installed under: $ROOT"
ls -1 "$ROOT" 2>/dev/null | while read -r d; do [ -f "$ROOT/$d/VERSION" ] && echo "  $d  $(cat "$ROOT/$d/VERSION")"; done
