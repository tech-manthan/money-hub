"""Print the licences of MoneyHub's Python dependencies (from installed package metadata)."""
from importlib import metadata

DEPS = ["weasyprint", "xlsxwriter", "openpyxl", "pillow", "pypdf", "pypdfium2", "jinja2", "pydantic", "pyyaml", "httpx", "typer",
        "fastapi", "uvicorn", "python-multipart", "anthropic", "playwright", "imageio-ffmpeg", "cairosvg", "fonttools", "pytest"]


def lic(name: str) -> str:
    try:
        m = metadata.metadata(name)
    except metadata.PackageNotFoundError:
        return "(not installed)"
    expr = m.get("License-Expression")
    if expr:
        return expr
    cls = [c.split("::")[-1].strip() for c in (m.get_all("Classifier") or []) if c.startswith("License ::")]
    if cls:
        return "; ".join(cls)
    raw = (m.get("License") or "").strip().splitlines()
    return raw[0][:60] if raw else "unknown"


if __name__ == "__main__":
    for d in DEPS:
        print(f"{d:<18} {lic(d)}")
