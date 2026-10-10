#!/bin/bash
# Installs the macOS DESKTOP APPS of the storytold craft tools into ~/Applications/Craft/ (the command-line versions are
# installed separately by scripts/install_craft_tools.sh).
#
#   bash scripts/install_craft_apps.sh                 # all 12
#   bash scripts/install_craft_apps.sh vectorcraft     # only some
#
# For each app: downloads the latest macOS .dmg and the release checksum file, verifies it, mounts the dmg read-only, copies the
# .app into ~/Applications/Craft/, and unmounts. Nothing is launched. Run it again to update. These are third-party, unaudited
# apps: on first launch macOS may ask you to confirm (right-click the app, then Open).
set -u
ORG=storytold
DEFAULT_REPOS="vectorcraft pdfcraft gridcraft photocraft wordcraft deckcraft filmcraft soundcraft lightcraft cadcraft designcraft effectcraft"
REPOS="${*:-$DEFAULT_REPOS}"
DEST="$HOME/Applications/Craft"
STATE="$DEST/.versions"
mkdir -p "$DEST" "$STATE"
command -v gh >/dev/null || { echo "Install the GitHub CLI first: brew install gh && gh auth login"; exit 1; }

for r in $REPOS; do
  new=$(gh release view -R "$ORG/$r" --json tagName -q .tagName 2>/dev/null)
  [ -z "$new" ] && { echo "[$r] no release, skipped"; continue; }
  [ "$new" = "$(cat "$STATE/$r" 2>/dev/null)" ] && { echo "[$r] up to date ($new)"; continue; }
  asset=$(gh release view -R "$ORG/$r" --json assets -q '.assets[].name' | grep -i -E 'macos.*\.dmg$' | head -1)
  [ -z "$asset" ] && { echo "[$r] $new has no macOS .dmg, skipped"; continue; }
  echo "[$r] -> $new ($asset)"
  tmp=$(mktemp -d)
  gh release download "$new" -R "$ORG/$r" -p "$asset" -p 'SHA256SUMS*' -D "$tmp" || { echo "[$r] download failed"; rm -rf "$tmp"; continue; }
  if ls "$tmp"/SHA256SUMS* >/dev/null 2>&1; then
    (cd "$tmp" && grep -F "$asset" SHA256SUMS* | shasum -a 256 -c -) || { echo "[$r] CHECKSUM FAILED, nothing installed"; rm -rf "$tmp"; continue; }
  else
    echo "[$r] WARNING: no checksum file; the download is NOT verified"
  fi
  mnt=$(mktemp -d)
  if hdiutil attach -readonly -nobrowse -mountpoint "$mnt" "$tmp/$asset" >/dev/null; then
    app=$(find "$mnt" -maxdepth 2 -name '*.app' | head -1)
    if [ -n "$app" ]; then
      rm -rf "$DEST/$(basename "$app")"; cp -R "$app" "$DEST/" && echo "$new" > "$STATE/$r" && echo "[$r] installed $(basename "$app")"
    else
      echo "[$r] no .app inside the dmg"
    fi
    hdiutil detach "$mnt" >/dev/null
  else
    echo "[$r] could not open the dmg"
  fi
  rm -rf "$tmp"
done
echo; echo "Apps are in: $DEST"; ls -1 "$DEST"
