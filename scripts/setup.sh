#!/usr/bin/env bash
# MoneyHub setup for macOS (Apple Silicon or Intel) and Linux.  Usage: bash scripts/setup.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> System libraries"
if [[ "$(uname)" == "Darwin" ]]; then
  if ! command -v brew >/dev/null; then echo "Install Homebrew first: https://brew.sh"; exit 1; fi
  brew list pango >/dev/null 2>&1 || brew install pango
  command -v ffmpeg >/dev/null || brew install ffmpeg
else
  echo "On Debian/Ubuntu: sudo apt install -y libpango-1.0-0 libpangoft2-1.0-0 ffmpeg   (skip if already installed)"
fi

echo "==> Python environment"
PY=${PYTHON:-python3}
$PY -m venv .venv
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -e ".[anthropic,chromium,video,dev]"

echo "==> Optional: Chromium for the alternate PDF engine (skip with Ctrl-C)"
playwright install chromium || true

echo
moneyhub doctor || true
cat <<'MSG'

Done. Next:
  source .venv/bin/activate
  moneyhub ui                                  # web studio at http://127.0.0.1:8765
  moneyhub make "nurse" weekly_planner         # or use the CLI

Optional AI providers: export ANTHROPIC_API_KEY / GEMINI_API_KEY / GROQ_API_KEY, or just log in to Claude Code (`claude`).
MSG
