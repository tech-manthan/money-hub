import os

import pytest


@pytest.fixture(autouse=True)
def isolated_output(tmp_path, monkeypatch):
    monkeypatch.setenv("MONEYHUB_OUT", str(tmp_path / "out"))
    yield
