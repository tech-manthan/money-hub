

def test_pdfium_finalizer_takes_the_same_lock():
    from pypdfium2.internal import bases

    from moneyhub.render import pdfium_safe
    pdfium_safe.install()
    assert hasattr(bases._close_template, "__wrapped__")     # garbage-collected pages and bitmaps are closed under the lock too


def test_isolated_rendering_matches_in_process_rendering_and_survives_a_bad_pdf(tmp_path, monkeypatch):
    import pytest
    from pypdf import PdfWriter

    from moneyhub.render import raster
    pdf = tmp_path / "a.pdf"
    w = PdfWriter()
    for _ in range(3):
        w.add_blank_page(300, 400)
    w.write(pdf)
    normal = raster.render_pages(pdf, [0, 2, 9], scale=0.5)
    monkeypatch.setenv(raster.ISOLATE_ENV, "1")
    assert raster.isolated()
    child = raster.render_pages(pdf, [0, 2, 9], scale=0.5)         # page 9 does not exist: skipped, like in process
    assert [i.size for i in child] == [i.size for i in normal] == [(150, 200)] * 2
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.7\nthis is not a pdf")
    with pytest.raises(RuntimeError, match="could not render"):     # the reader fails in the child; the caller carries on
        raster.render_pages(bad, [0])
    monkeypatch.delenv(raster.ISOLATE_ENV)
    assert not raster.isolated()


def test_ui_command_switches_isolation_on(monkeypatch):
    import uvicorn
    from typer.testing import CliRunner

    from moneyhub.cli import app
    from moneyhub.render.raster import ISOLATE_ENV
    monkeypatch.delenv(ISOLATE_ENV, raising=False)
    seen = {}
    monkeypatch.setattr(uvicorn, "run", lambda *a, **k: seen.update(env=__import__("os").environ.get(ISOLATE_ENV)))
    assert CliRunner().invoke(app, ["ui", "--port", "8791"]).exit_code == 0 and seen["env"] == "1"
    monkeypatch.delenv(ISOLATE_ENV, raising=False)
