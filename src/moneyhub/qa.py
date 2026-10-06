"""Automated quality checks run on every build (visible in the review screen)."""
from __future__ import annotations

import subprocess
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path

from .design import Style
from .products.base import BuildResult
from .render.raster import pdf_page_count, render_pages


@dataclass
class Check:
    name: str
    status: str   # pass | warn | fail
    detail: str = ""

    def to_dict(self):
        return asdict(self)


def _pdf_fonts_embedded(pdf: Path) -> tuple[int, int]:
    from pypdf import PdfReader

    r = PdfReader(str(pdf))
    total = embedded = 0
    seen = set()
    for page in r.pages[:6]:
        res = page.get("/Resources")
        fonts = (res.get_object().get("/Font") if res else None) or {}
        for ref in fonts.values():
            f = ref.get_object()
            key = str(f.get("/BaseFont"))
            if key in seen:
                continue
            seen.add(key)
            total += 1
            desc = f.get("/FontDescriptor")
            descendants = f.get("/DescendantFonts")
            if descendants:
                desc = descendants[0].get_object().get("/FontDescriptor")
            if desc is not None:
                d = desc.get_object()
                if any(k in d for k in ("/FontFile", "/FontFile2", "/FontFile3")):
                    embedded += 1
    return total, embedded


def _blank_pages(pdf: Path, sample: int = 12) -> list[int]:
    n = pdf_page_count(pdf)
    idx = sorted(set([0, n - 1] + [int(i * (n - 1) / max(1, sample - 1)) for i in range(sample)]))
    blanks = []
    for i, img in zip(idx, render_pages(pdf, idx, scale=0.25)):
        lo, hi = img.convert("L").getextrema()
        if hi - lo < 8:
            blanks.append(i + 1)
    return blanks


def _links(pdf: Path) -> int:
    from pypdf import PdfReader

    r = PdfReader(str(pdf))
    return sum(len(p.get("/Annots") or []) for p in r.pages[:3])


def run_checks(build: BuildResult, style: Style, expected_sizes: list[str], spec_pages_hint: int | None = None) -> list[Check]:
    checks: list[Check] = []
    issues = style.palette.issues()
    checks.append(Check("Colour contrast", "pass" if not issues else "fail", "ink/paper ≥ 7, accent text ≥ 4.5" if not issues else ", ".join(issues)))
    pdfs = [f for f in build.files if f.kind == "pdf"]
    for f in pdfs:
        n = pdf_page_count(f.path)
        size_mb = f.path.stat().st_size / 1e6
        checks.append(Check(f"{f.path.name}: pages", "pass" if n >= 3 else "fail", f"{n} pages"))
        checks.append(Check(f"{f.path.name}: size", "pass" if size_mb < 20 else "fail", f"{size_mb:.1f} MB (Etsy limit 20 MB per file)"))
        total, emb = _pdf_fonts_embedded(f.path)
        checks.append(Check(f"{f.path.name}: fonts embedded", "pass" if total == emb else "fail", f"{emb}/{total} fonts embedded"))
        blanks = _blank_pages(f.path)
        checks.append(Check(f"{f.path.name}: blank pages", "pass" if not blanks else "warn", "none in sample" if not blanks else f"possible blank pages: {blanks}"))
        if "hyperlinked" in f.path.name:
            links = _links(f.path)
            checks.append(Check(f"{f.path.name}: internal links", "pass" if links else "fail", f"{links} link annotations on first pages"))
    for f in [x for x in build.files if x.kind == "xlsx"]:
        checks += _xlsx_checks(f.path)
    for f in [x for x in build.files if x.kind == "zip"]:
        checks += _zip_checks(f.path)
    return checks


def _zip_checks(path: Path) -> list[Check]:
    import zipfile

    from PIL import Image

    size_mb = path.stat().st_size / 1e6
    out = [Check(f"{path.name}: size", "pass" if size_mb < 20 else "fail", f"{size_mb:.1f} MB (Etsy limit 20 MB per file)")]
    with zipfile.ZipFile(path) as z:
        jpgs = [n for n in z.namelist() if n.lower().endswith(".jpg")]
        out.append(Check(f"{path.name}: images", "pass" if jpgs else "fail", f"{len(jpgs)} JPG files"))
        if jpgs:
            with z.open(jpgs[0]) as fh:
                im = Image.open(fh)
                out.append(Check(f"{path.name}: resolution", "pass" if min(im.size) >= 2400 else "warn", f"{im.size[0]}x{im.size[1]} px"))
    return out


def _xlsx_checks(path: Path) -> list[Check]:
    import warnings

    import openpyxl

    out = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            wb = openpyxl.load_workbook(path)
        except Exception as e:  # noqa: BLE001
            return [Check(f"{path.name}: opens", "fail", str(e)[:200])]
    out.append(Check(f"{path.name}: opens", "pass", f"sheets: {', '.join(wb.sheetnames)}"))
    formulas = missing = 0
    names = set(wb.sheetnames)
    import re

    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    formulas += 1
                    for ref in re.findall(r"([A-Za-z ]+)!", c.value):
                        if ref.strip("' ") not in names:
                            missing += 1
    out.append(Check(f"{path.name}: formulas", "pass" if formulas and not missing else "fail", f"{formulas} formulas, {missing} broken sheet references"))
    errs = _libreoffice_errors(path)
    if errs is None:
        out.append(Check(f"{path.name}: recalculation", "warn", "LibreOffice not available - open the file in Excel/Sheets once and confirm no #errors before listing"))
    else:
        out.append(Check(f"{path.name}: recalculation", "pass" if not errs else "fail", "no formula errors after recalculation" if not errs else f"{len(errs)} error cells, e.g. {errs[:3]}"))
    return out


def _libreoffice_errors(path: Path) -> list[str] | None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    import tempfile
    import warnings

    import openpyxl

    with tempfile.TemporaryDirectory() as td:
        try:
            r = subprocess.run([soffice, "--headless", "--norestore", "--convert-to", "xlsx", "--outdir", td, str(path)],
                               capture_output=True, text=True, timeout=120)
        except (subprocess.TimeoutExpired, OSError):
            return None
        out = Path(td) / path.name
        if r.returncode != 0 or not out.exists():
            return None
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            wb = openpyxl.load_workbook(out, data_only=True)
        errs = []
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for c in row:
                    if isinstance(c.value, str) and c.value.startswith("#"):
                        errs.append(f"{ws.title}!{c.coordinate}={c.value}")
        return errs


def summarize(checks: list[Check]) -> str:
    if any(c.status == "fail" for c in checks):
        return "fail"
    if any(c.status == "warn" for c in checks):
        return "warn"
    return "pass"
