"""PDF rendering backends. Several can be configured; the first that is available (and succeeds) wins."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from ..config import get_config

log = logging.getLogger("moneyhub.render")


class PDFBackend(ABC):
    name = "base"

    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def render(self, html: str, out: Path, *, page_css_size: str) -> None: ...


class WeasyPrintBackend(PDFBackend):
    name = "weasyprint"

    def available(self) -> bool:
        try:
            import weasyprint  # noqa: F401
            return True
        except Exception:  # missing system libs also raise OSError
            return False

    def render(self, html: str, out: Path, *, page_css_size: str) -> None:
        from weasyprint import HTML

        HTML(string=html, base_url=str(out.parent)).write_pdf(str(out))


def chromium_executable() -> str | None:
    """Explicit path from config/env, else a Playwright-managed browser (None lets Playwright find its own)."""
    import glob
    import os

    explicit = os.environ.get("MONEYHUB_CHROMIUM") or get_config().get("render.chromium_path")
    if explicit:
        return explicit
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    for pattern in (f"{base}/chromium-*/chrome-linux/chrome", f"{base}/chromium-*/chrome-linux64/chrome"):
        found = sorted(glob.glob(pattern))
        if found:
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    if os.path.exists(p.chromium.executable_path):
                        return None
            except Exception:  # noqa: BLE001
                pass
            return found[-1]
    return None


class ChromiumBackend(PDFBackend):
    name = "chromium"

    def available(self) -> bool:
        try:
            import playwright  # noqa: F401
            return True
        except ImportError:
            return False

    def render(self, html: str, out: Path, *, page_css_size: str) -> None:
        from playwright.sync_api import sync_playwright

        tmp = out.with_suffix(".tmp.html")
        tmp.write_text(html, encoding="utf-8")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(args=["--allow-file-access-from-files"], executable_path=chromium_executable())
                page = browser.new_page()
                page.goto(tmp.as_uri())
                page.evaluate("document.fonts.ready")
                page.pdf(path=str(out), prefer_css_page_size=True, print_background=True)
                browser.close()
        finally:
            tmp.unlink(missing_ok=True)


BACKENDS: dict[str, PDFBackend] = {b.name: b for b in (WeasyPrintBackend(), ChromiumBackend())}


def render_pdf(html: str, out: Path, *, page_css_size: str, backends: list[str] | None = None) -> str:
    """Render HTML to PDF; returns the name of the backend used."""
    names = backends or get_config().get("render.pdf", ["weasyprint"])
    out.parent.mkdir(parents=True, exist_ok=True)
    last: Exception | None = None
    for n in names:
        b = BACKENDS.get(n)
        if not b or not b.available():
            continue
        try:
            b.render(html, out, page_css_size=page_css_size)
            return b.name
        except Exception as e:  # noqa: BLE001 - fall through to the next backend
            log.warning("pdf backend %s failed: %s", n, e)
            last = e
    raise RuntimeError(f"no PDF backend could render the document: {last}")
