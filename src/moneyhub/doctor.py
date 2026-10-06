"""`moneyhub doctor`: check the machine can render everything and show what is configured."""
from __future__ import annotations

import os
import platform
import shutil
import sys
from dataclasses import dataclass

from .config import get_config
from .paths import FONT_DIR


@dataclass
class Item:
    name: str
    ok: bool
    detail: str
    required: bool = False
    fix: str = ""


def run() -> list[Item]:
    items: list[Item] = []
    items.append(Item("Python", sys.version_info >= (3, 10), platform.python_version(), True, "Install Python 3.10+"))
    try:
        import weasyprint
        weasyprint.HTML(string="<p>x</p>").write_pdf()
        items.append(Item("WeasyPrint (PDF engine)", True, f"v{weasyprint.__version__}", True))
    except Exception as e:  # noqa: BLE001
        fix = "brew install pango" if sys.platform == "darwin" else "sudo apt install libpango-1.0-0 libpangoft2-1.0-0"
        items.append(Item("WeasyPrint (PDF engine)", False, str(e)[:120], True, fix))
    n_fonts = len(list(FONT_DIR.glob("*.ttf"))) if FONT_DIR.exists() else 0
    items.append(Item("Bundled fonts (SIL OFL)", n_fonts >= 20, f"{n_fonts} files", True, "Run: python scripts/make_static_fonts.py"))
    for mod, label in (("xlsxwriter", "XlsxWriter"), ("openpyxl", "openpyxl"), ("PIL", "Pillow"), ("pypdfium2", "pypdfium2"), ("fastapi", "FastAPI")):
        try:
            __import__(mod)
            items.append(Item(label, True, "ok", True))
        except ImportError:
            items.append(Item(label, False, "missing", True, "pip install -e ."))
    from .render import motion
    items.append(Item("ffmpeg (video pins)", motion.ffmpeg_exe() is not None, motion.ffmpeg_exe() or "not found", False,
                      "brew install ffmpeg   (or pip install imageio-ffmpeg)"))
    for e in motion.engine_status():
        if e["name"] == "pillow":
            continue
        items.append(Item(f"Video engine: {e['name']} (optional)", e["available"], e["note"] if not e["available"] else ("ready" + (", in chain" if e["enabled"] else ", not in render.motion chain")), False,
                          f"moneyhub engines install {e['name']}"))
    try:
        import playwright  # noqa: F401
        from .render.pdf import chromium_executable
        items.append(Item("Playwright / Chromium (alt. PDF engine)", True, chromium_executable() or "playwright-managed browser", False, "playwright install chromium"))
    except ImportError:
        items.append(Item("Playwright / Chromium (alt. PDF engine)", False, "not installed (optional)", False, "pip install -e '.[chromium]' && playwright install chromium"))
    lo = shutil.which("soffice") or shutil.which("libreoffice") or ("/Applications/LibreOffice.app/Contents/MacOS/soffice" if os.path.exists("/Applications/LibreOffice.app/Contents/MacOS/soffice") else None)
    items.append(Item("LibreOffice (spreadsheet recalculation check)", bool(lo), lo or "not found (optional)", False, "brew install --cask libreoffice"))
    from .llm import get_router
    for row in get_router().status():
        items.append(Item(f"LLM: {row['name']}", row["available"], row["model"], False,
                          {"anthropic": "export ANTHROPIC_API_KEY=...", "gemini": "export GEMINI_API_KEY=...", "groq": "export GROQ_API_KEY=...",
                           "openrouter": "export OPENROUTER_API_KEY=...", "ollama": "brew install ollama && ollama serve && ollama pull llama3.1",
                           "claude_cli": "install Claude Code and run `claude` once to log in"}.get(row["name"], "")))
    from .art import art_status
    for a in art_status():
        items.append(Item(f"Art provider: {a['name']}", a["available"], "enabled" if a["enabled"] else "key present, not enabled in render.art" if a["available"] else "no key", False,
                          {"huggingface": "export HF_TOKEN=...", "together": "export TOGETHER_API_KEY=...", "openai": "export OPENAI_API_KEY=...",
                           "local_http": "export MONEYHUB_ART_URL=http://localhost:PORT/generate"}.get(a["name"], "")))
    items.append(Item("Output folder", True, str(get_config().output_dir), False))
    return items
