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
# Prefer a well-supported Python (3.12/3.13/3.11); CI tests 3.11-3.14. Override with PYTHON=/path/to/python.
PY=${PYTHON:-}
if [[ -z "$PY" ]]; then
  for c in python3.12 python3.13 python3.11 python3; do
    if command -v "$c" >/dev/null; then PY=$c; break; fi
  done
fi
echo "Using $($PY --version) ($PY)"
$PY -m venv .venv
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -e ".[anthropic,chromium,video,dev]"

if [[ "${1:-}" == "--full" ]]; then
  echo "==> Optional engines (--full): HyperFrames, Remotion, voice, LibreOffice"
  moneyhub engines install hyperframes || true
  moneyhub engines install remotion || true
  pip install kokoro-onnx && moneyhub voices install || true
  if [[ "$(uname)" == "Darwin" ]]; then brew list --cask libreoffice >/dev/null 2>&1 || brew install --cask libreoffice || true; fi
fi

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
