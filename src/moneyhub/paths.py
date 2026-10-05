"""Filesystem locations shared across the package."""
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent.parent
FONT_DIR = REPO_ROOT / "assets" / "fonts" / "static"
GUIDE_DIR = PACKAGE_DIR / "listing" / "guides"
