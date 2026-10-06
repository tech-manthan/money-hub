import os
import stat

import pytest
from fastapi.testclient import TestClient

from moneyhub import keystore
from moneyhub.config import reload_config
from moneyhub.web.app import app


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("MONEYHUB_HOME", str(tmp_path))
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    keystore._from_file.clear()
    reload_config()
    yield tmp_path
    reload_config()


def test_saved_key_is_private_masked_and_removable(home):
    keystore.save("GROQ_API_KEY", "gsk_abcdef1234567890")
    f = home / ".env"
    assert stat.S_IMODE(f.stat().st_mode) == 0o600 and "gsk_abcdef1234567890" in f.read_text()
    row = next(r for r in keystore.status() if r["env"] == "GROQ_API_KEY")
    assert row["set"] and row["masked"].endswith("7890") and "abcdef" not in row["masked"] and row["source"] == ".env file"
    assert keystore.scrub("failed with gsk_abcdef1234567890") == "failed with ***"
    keystore.remove("GROQ_API_KEY")
    assert "GROQ_API_KEY" not in os.environ and "GROQ" not in f.read_text()


def test_only_known_settings_with_sane_values_are_accepted(home):
    for name, value in (("PATH", "x"), ("GROQ_API_KEY", ""), ("GROQ_API_KEY", "a\nb"), ("MONEYHUB_ART_URL", "ftp://x")):
        with pytest.raises(ValueError):
            keystore.save(name, value)


def test_saved_keys_load_at_startup_but_the_shell_wins(home, monkeypatch):
    (home / ".env").write_text("GROQ_API_KEY=from_file\nHF_TOKEN=hf_from_file\n")
    monkeypatch.setenv("HF_TOKEN", "from_shell")
    keystore.load_env()
    assert os.environ["GROQ_API_KEY"] == "from_file" and os.environ["HF_TOKEN"] == "from_shell"


def test_settings_api_works_locally_and_refuses_other_sites(home):
    local = TestClient(app, base_url="http://127.0.0.1:8766")
    assert local.post("/api/settings/key", data={"name": "GROQ_API_KEY", "value": "gsk_localtest12345"}).status_code == 200
    assert "gsk_localtest12345" not in local.get("/settings").text and "2345" in local.get("/settings").text
    cross_site = local.post("/api/settings/key", data={"name": "GROQ_API_KEY", "value": "evil"}, headers={"origin": "http://evil.example"})
    assert cross_site.status_code == 403
    assert TestClient(app, base_url="http://evil.example").post("/api/settings/key/remove", data={"name": "GROQ_API_KEY"}).status_code == 403
    assert local.post("/api/settings/key/remove", data={"name": "GROQ_API_KEY"}).status_code == 200


def test_art_choices_are_saved_to_the_local_config(home):
    local = TestClient(app, base_url="http://127.0.0.1:8766")
    r = local.post("/api/settings/art", data={"providers": ["claude_svg", "bogus"]})
    assert r.json()["providers"] == ["claude_svg"]
    assert "claude_svg" in (home / "moneyhub.local.yaml").read_text()
