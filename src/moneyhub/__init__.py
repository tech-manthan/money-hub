"""MoneyHub: a local creator studio for sellable digital products."""
__version__ = "0.1.0"

try:   # PDFium crashes the process when used from several threads at once; serialise it for the whole app
    from .render.pdfium_safe import install as _install_pdfium_lock
    _install_pdfium_lock()
except ImportError:   # pypdfium2 missing: `moneyhub doctor` reports it
    pass
