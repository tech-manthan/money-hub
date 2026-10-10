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
        min_pages = 1 if ("Start-Here" in f.path.name or "License" in f.path.name) else build.meta.get("min_pages", 3)
        checks.append(Check(f"{f.path.name}: pages", "pass" if n >= min_pages else "fail", f"{n} pages"))
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
    for f in [x for x in build.files if x.kind == "pptx"]:
        checks += _pptx_checks(f.path, build.meta.get("slides", 0))
    for f in [x for x in build.files if x.kind == "zip"]:
        checks += _zip_checks(f.path, build.meta.get("min_px", 2000))
    if "cut_min_gap_mm" in build.meta:   # cut files: the thinnest bridge between two cuts must survive a real cutting mat
        g = build.meta["cut_min_gap_mm"]
        checks.append(Check("Cut-ready", "pass" if g >= 1.5 else "fail", f"thinnest gap between cuts {g} mm (1.5 mm or more holds on a mat)"))
    if "cut_roundtrip_problems" in build.meta:   # SVG and DXF read back the way Cricut / Silhouette software reads them
        bad = build.meta["cut_roundtrip_problems"]
        checks.append(Check("Opens in cutting software", "fail" if bad else "pass", "; ".join(bad) if bad else "SVG and DXF re-read cleanly: closed outlines, real inch size, same shape in both"))
    lang = build.meta.get("language")
    if lang and lang != "en":   # bilingual products: the word list must have been proofread
        from .translations import review_status
        st, msg = review_status(lang)
        checks.append(Check("Translations reviewed", st, msg))
    if "seam_excess" in build.meta:   # seamless patterns: the join between opposite edges must look like any other join
        v = build.meta["seam_excess"]
        checks.append(Check("Seamless tiling", "pass" if v <= 12 else "warn", f"edge join {v:+.1f} vs neighbouring pixels (12 or less is clean)"))
    return checks


def _pptx_checks(path: Path, slides: int) -> list[Check]:
    import re
    import zipfile

    size_mb = path.stat().st_size / 1e6
    out = [Check(f"{path.name}: size", "pass" if size_mb < 20 else "fail", f"{size_mb:.1f} MB (Etsy limit 20 MB per file)")]
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            n = len([x for x in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", x)])
            ok = "ppt/presentation.xml" in names and n >= 1 and (not slides or n == slides)
            out.append(Check(f"{path.name}: slides", "pass" if ok else "fail", f"{n} slides" + ("" if ok else f" (expected {slides}) or missing presentation.xml")))
    except (zipfile.BadZipFile, OSError) as e:
        out.append(Check(f"{path.name}: opens", "fail", f"not a valid .pptx package: {e}"))
    return out


def _zip_checks(path: Path, min_px: int = 2000) -> list[Check]:
    import zipfile

    from PIL import Image

    size_mb = path.stat().st_size / 1e6
    out = [Check(f"{path.name}: size", "pass" if size_mb < 20 else "fail", f"{size_mb:.1f} MB (Etsy limit 20 MB per file)")]
    with zipfile.ZipFile(path) as z:
        jpgs = [n for n in z.namelist() if n.lower().endswith((".jpg", ".png"))]
        svgs = [n for n in z.namelist() if n.lower().endswith((".svg", ".dxf", ".eps"))]
        out.append(Check(f"{path.name}: images", "pass" if jpgs or svgs else "fail", f"{len(jpgs)} image files" + (f", {len(svgs)} vector files" if svgs else "")))
        if jpgs:
            with z.open(jpgs[0]) as fh:
                im = Image.open(fh)
                out.append(Check(f"{path.name}: resolution", "pass" if min(im.size) >= min_px else "warn", f"{im.size[0]}x{im.size[1]} px"))
                if jpgs[0].lower().endswith(".png"):
                    out.append(Check(f"{path.name}: transparency", "pass" if im.mode == "RGBA" and im.getchannel("A").getextrema()[0] == 0 else "fail",
                                     "transparent background" if im.mode == "RGBA" else "no alpha channel"))
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


def media_checks(folder: Path) -> list[Check]:
    """Listing images and videos against marketplace limits."""
    out: list[Check] = []
    big = [f.name for f in sorted((folder / "images" / "etsy").glob("*.jpg")) if f.stat().st_size > 1_000_000]
    n = len(list((folder / "images" / "etsy").glob("*.jpg")))
    if n:
        out.append(Check("Etsy photos under 1 MB each", "pass" if not big else "warn", f"{n} photos" if not big else f"too large: {', '.join(big)}"))
    from PIL import Image
    small = []
    for f in sorted((folder / "images" / "etsy").glob("*.jpg")):
        with Image.open(f) as im:
            if min(im.size) < 2000:
                small.append(f.name)
    if n:
        out.append(Check("Etsy photos at least 2000 px (shortest side)", "pass" if not small else "warn", "ok" if not small else ", ".join(small)))
    from .render import motion
    for v in sorted((folder / "images" / "video").glob("*.mp4")):
        dur = motion.video_duration(v)
        if dur is None:
            continue
        if "listing" in v.name:
            out.append(Check(f"{v.name}: 5-15 s for Etsy", "pass" if 5 <= dur <= 15 else "warn", f"{dur:.1f} s, {v.stat().st_size / 1e6:.1f} MB (limit 100 MB)"))
        else:
            out.append(Check(f"{v.name}: 6-15 s works best on Pinterest", "pass" if 4 <= dur <= 15 else "warn", f"{dur:.1f} s"))
    return out
