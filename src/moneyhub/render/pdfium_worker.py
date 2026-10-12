"""Child process used by `raster.render_pages` when the web UI isolates pdfium: `python -m moneyhub.render.pdfium_worker PDF SCALE OUTDIR PAGE...`
writes OUTDIR/<page>.png for every page that exists and prints those page numbers."""
from __future__ import annotations

import sys
from pathlib import Path

import pypdfium2 as pdfium


def main(argv: list[str]) -> int:
    pdf, scale, out = argv[0], float(argv[1]), Path(argv[2])
    doc = pdfium.PdfDocument(pdf)
    try:
        done = []
        for i in map(int, argv[3:]):
            if 0 <= i < len(doc):
                doc[i].render(scale=scale).to_pil().convert("RGB").save(out / f"{i}.png")
                done.append(i)
        print(*done)
    finally:
        doc.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
