"""PDFium is not thread-safe, and the web UI uses it from many threads at once (a page of preview thumbnails plus a job rendering a
product). Concurrent calls crash the whole process (trace trap / bus error). Importing this module wraps every pypdfium2 method in one
re-entrant lock, so all of MoneyHub's PDF rendering is serialised without changing the code that calls it."""
from __future__ import annotations

import functools
import inspect
import threading

import pypdfium2 as pdfium

LOCK = threading.RLock()
_KEEP = {"__init__", "__getitem__", "__len__", "__iter__"}
_done = False


def _wrap(fn):
    @functools.wraps(fn)
    def locked(*args, **kwargs):
        with LOCK:
            return fn(*args, **kwargs)
    return locked


def install() -> None:
    """Wrap the methods of PdfDocument, PdfPage, PdfTextPage and PdfBitmap once."""
    global _done
    if _done:
        return
    for name in ("PdfDocument", "PdfPage", "PdfTextPage", "PdfBitmap"):
        cls = getattr(pdfium, name, None)
        if cls is None:
            continue
        for attr, value in list(vars(cls).items()):
            if not inspect.isfunction(value):
                continue
            if attr.startswith("_") and attr not in _KEEP:
                continue
            setattr(cls, attr, _wrap(value))
    _done = True
