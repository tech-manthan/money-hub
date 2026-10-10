"""Optional second opinion from the storytold craft command-line tools (pdfcraft, gridcraft, vectorcraft, ...).

Installed by `scripts/install_craft_tools.sh` into tools/craft/<name>/current/. They are third-party programs, so everything here is
advisory: a missing tool, a crash or a timeout never fails a product, and nothing here is part of the QA gate. `verify_product` opens a
finished product's PDFs, spreadsheets and editable SVGs with the tools and reports whether each one reads cleanly."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

TOOLS = ["vectorcraft", "pdfcraft", "gridcraft", "photocraft", "wordcraft", "deckcraft", "filmcraft", "soundcraft", "lightcraft", "cadcraft",
         "designcraft", "effectcraft"]


# the tools that have a real check in verify_product (the others are only reachable with `moneyhub craft`)
CHECKERS = ["vectorcraft", "pdfcraft", "gridcraft", "photocraft", "wordcraft", "deckcraft", "soundcraft", "cadcraft"]


def _cfg(key: str, default):
    from .config import get_config
    return get_config().get(f"craft.{key}", default)


def master_enabled() -> bool:
    return bool(_cfg("enabled", False))


def is_enabled(tool: str) -> bool:
    """A tool is used automatically only when the master switch and its own switch are both on."""
    return master_enabled() and bool((_cfg("tools", {}) or {}).get(tool, False))


def settings_view() -> dict:
    tools = _cfg("tools", {}) or {}
    return {"enabled": master_enabled(), "verify_after_make": bool(_cfg("verify_after_make", False)), "timeout": float(_cfg("timeout", 90)),
            "tools": [{"tool": t, "enabled": bool(tools.get(t, False)), "installed": find_tool(t) is not None, "version": version(t)} for t in CHECKERS]}


def save_settings(enabled: bool | None = None, verify_after_make: bool | None = None, tools: dict[str, bool] | None = None) -> dict:
    """Write craft settings to moneyhub.local.yaml (git-ignored)."""
    from .config import save_local_setting
    if enabled is not None:
        save_local_setting("craft.enabled", bool(enabled))
    if verify_after_make is not None:
        save_local_setting("craft.verify_after_make", bool(verify_after_make))
    for t, on in (tools or {}).items():
        if t not in CHECKERS:
            raise ValueError(f"unknown tool '{t}'. Choose from: {', '.join(CHECKERS)}")
        save_local_setting(f"craft.tools.{t}", bool(on))
    return settings_view()


def tools_dir() -> Path:
    """tools/craft next to the project, or MONEYHUB_CRAFT_DIR."""
    env = os.environ.get("MONEYHUB_CRAFT_DIR")
    return Path(env) if env else Path(__file__).resolve().parents[2] / "tools" / "craft"


def find_tool(name: str) -> Path | None:
    base = tools_dir() / name
    hits = sorted((base / "current").glob(f"*/{name}-cli")) + sorted((base / "current").glob(f"{name}-cli"))
    for h in hits:
        if h.is_file() and os.access(h, os.X_OK):
            return h
    on_path = shutil.which(f"{name}-cli")
    return Path(on_path) if on_path else None


def version(name: str) -> str:
    v = tools_dir() / name / "VERSION"
    return v.read_text(encoding="utf-8").strip() if v.exists() else ""


def status() -> list[dict]:
    return [{"tool": n, "path": str(p) if (p := find_tool(n)) else "", "version": version(n)} for n in TOOLS]


@dataclass
class Run:
    ok: bool
    code: int
    out: str
    err: str


def run(name: str, args: list[str], timeout: float = 60.0) -> Run:
    """Run `<name>-cli args...`. Never raises: a missing tool, a crash or a timeout comes back as ok=False."""
    exe = find_tool(name)
    if exe is None:
        return Run(False, -1, "", f"{name} is not installed (run scripts/install_craft_tools.sh)")
    try:
        p = subprocess.run([str(exe), *args], capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return Run(False, -2, "", f"{name} timed out after {timeout:g}s")
    except OSError as e:
        return Run(False, -3, "", f"{name} could not start: {e}")
    return Run(p.returncode == 0, p.returncode, p.stdout, p.stderr)


def _finding(file: Path, tool: str, r: Run, what: str) -> dict:
    detail = (r.out if r.ok else (r.err or r.out)).strip().replace("\n", " ")[:300]
    return {"file": file.name, "tool": tool, "check": what, "ok": r.ok, "detail": detail}


def verify_product(folder: Path, timeout: float = 90.0, only: list[str] | None = None) -> list[dict]:
    """Open each PDF, spreadsheet and editable SVG of a product with the matching tool and report whether it reads cleanly.
    `only` limits the run to those tools (the automatic check passes the ones switched on in settings)."""
    folder = Path(folder)
    out: list[dict] = []

    def on(tool: str) -> bool:
        return only is None or tool in only

    if on("pdfcraft"):
        for f in sorted((folder / "product").glob("*.pdf")):
            out.append(_finding(f, "pdfcraft", run("pdfcraft", ["info", str(f)], timeout), "opens and summarises"))
            with tempfile.TemporaryDirectory() as td:
                png = Path(td) / "p1.png"
                r = run("pdfcraft", ["render", str(f), "--page", "1", "--dpi", "48", "--out", str(png)], timeout)
                r.ok = r.ok and png.exists() and png.stat().st_size > 200
                out.append(_finding(f, "pdfcraft", r, "page 1 renders"))
    if on("gridcraft"):
        for f in sorted((folder / "product").glob("*.xlsx")):
            out.append(_finding(f, "gridcraft", run("gridcraft", ["info", str(f), "--json"], timeout), "opens and lists sheets"))
    if on("vectorcraft"):
        for f in sorted((folder / "editable").rglob("*.svg"))[:12]:
            out.append(_finding(f, "vectorcraft", run("vectorcraft", ["info", str(f)], timeout), "opens as a vector document"))
    if on("wordcraft"):
        for f in sorted((folder / "product").glob("*.docx")):
            out.append(_finding(f, "wordcraft", run("wordcraft", ["info", str(f)], timeout), "opens as a document"))
    if on("deckcraft"):
        for f in sorted((folder / "product").glob("*.pptx")):
            out.append(_finding(f, "deckcraft", run("deckcraft", ["info", str(f)], timeout), "opens as a presentation"))
    if on("soundcraft"):
        for f in [p for ext in ("wav", "mp3", "m4a", "flac") for p in sorted(folder.rglob(f"*.{ext}"))][:3]:
            out.append(_finding(f, "soundcraft", run("soundcraft", ["info", str(f)], timeout), "opens as audio"))
    if on("cadcraft"):
        for z in sorted((folder / "product").glob("*.zip"))[:6]:   # cut files ship their DXF files zipped
            try:
                with zipfile.ZipFile(z) as zf, tempfile.TemporaryDirectory() as td:
                    for n in [n for n in zf.namelist() if n.lower().endswith(".dxf")][:3]:
                        dst = Path(td) / Path(n).name
                        dst.write_bytes(zf.read(n))
                        r = _finding(dst, "cadcraft", run("cadcraft", ["info", str(dst)], timeout), "opens as a drawing")
                        r["file"] = f"{z.name}:{Path(n).name}"
                        out.append(r)
            except (zipfile.BadZipFile, OSError):
                out.append({"file": z.name, "tool": "cadcraft", "check": "zip opens", "ok": False, "detail": "not a readable zip file"})
    if on("photocraft"):
        for f in [p for ext in ("jpg", "png") for p in sorted((folder / "images").rglob(f"*.{ext}"))][:6]:
            out.append(_finding(f, "photocraft", run("photocraft", ["info", str(f), "--compact"], timeout), "opens as an image"))
    return out


def polish_wav(wav: Path, rate: int | None = None, headroom: float = 0.9, timeout: float = 120.0) -> bool:
    """Level a narration WAV with soundcraft (`convert --normalize`) and replace it in place. Only when the master switch and the
    soundcraft switch are both on; returns True when the file was replaced. Any problem (tool missing, failed, silent or much
    shorter output) leaves the original file untouched. The result is scaled back to `headroom` so the AAC encode cannot clip."""
    import wave
    try:
        if not is_enabled("soundcraft") or find_tool("soundcraft") is None:
            return False
        wav = Path(wav)
        out = wav.with_suffix(".polished.wav")
        args = ["convert", str(wav), str(out), "--bit-depth", "16", "--normalize"] + (["--rate", str(rate)] if rate else [])
        r = run("soundcraft", args, timeout)
        if not (r.ok and out.exists() and out.stat().st_size > 1000):
            out.unlink(missing_ok=True)
            return False
        with wave.open(str(wav)) as a, wave.open(str(out)) as b:
            if b.getsampwidth() != 2 or b.getnframes() < 0.95 * a.getnframes() * b.getframerate() / a.getframerate():
                out.unlink(missing_ok=True)
                return False
            params, frames = b.getparams(), b.readframes(b.getnframes())
        import numpy as np
        x = np.frombuffer(frames, dtype="<i2").astype(np.float32)
        peak = float(np.abs(x).max()) / 32768 if len(x) else 0.0
        if peak < 0.01:   # silence: do not replace good narration with nothing
            out.unlink(missing_ok=True)
            return False
        if peak > headroom:
            x *= headroom / peak
        with wave.open(str(out), "wb") as w:
            w.setparams(params)
            w.writeframes(np.clip(x, -32768, 32767).astype("<i2").tobytes())
        out.replace(wav)
        return True
    except Exception:   # noqa: BLE001 - an optional polish step must never break the caller
        return False


def second_opinion(folder: Path):
    """The automatic quality check run after a product is made, or None when the integration is off or nothing was checked.
    Warn-only by design: it can never fail a product, and any error inside it is swallowed."""
    try:
        from .qa import Check
        if not (master_enabled() and _cfg("verify_after_make", False)):
            return None
        tools = [t for t in CHECKERS if is_enabled(t) and find_tool(t)]
        if not tools:
            return None
        findings = verify_product(folder, float(_cfg("timeout", 90)), only=tools)
        if not findings:
            return None
        write_report(folder, findings)
        bad = [f for f in findings if not f["ok"]]
        if not bad:
            return Check("Second opinion (craft tools)", "pass",
                         f"{len(findings)} checks passed with {', '.join(sorted({f['tool'] for f in findings}))}")
        return Check("Second opinion (craft tools)", "warn",
                     "; ".join(f"{f['tool']}: {f['file']} {f['check']} failed" for f in bad[:5]) + " (advisory, see craft-verify.json)")
    except Exception:   # noqa: BLE001 - an optional extra must never break generation
        return None


def passthrough(name: str, args: list[str], timeout: float = 300.0) -> Run:
    """Run any craft tool with your own arguments (with the same timeout and no-crash behaviour as the checks)."""
    if name not in TOOLS:
        return Run(False, -4, "", f"unknown tool '{name}'. Choose from: {', '.join(TOOLS)}")
    return run(name, args, timeout)


def write_report(folder: Path, findings: list[dict]) -> Path:
    p = Path(folder) / "craft-verify.json"
    p.write_text(json.dumps({"tools": status(), "findings": findings}, indent=2), encoding="utf-8")
    return p
