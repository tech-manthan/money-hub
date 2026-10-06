from fastapi.testclient import TestClient

from moneyhub.web.app import app

client = TestClient(app)


def test_every_page_renders():
    for url in ("/", "/make", "/docs", "/products", "/advanced", "/ideas", "/settings", "/report"):
        r = client.get(url)
        assert r.status_code == 200, url


def test_wizard_offers_ready_made_ideas_and_every_product_type():
    html = client.get("/make").text
    assert html.count('class="idea"') >= 10
    assert 'name="product_type"' in html and "Surprise me" in html


def test_docs_lists_real_cli_options():
    html = client.get("/docs").text
    for flag in ("--palette", "--fonts", "--motif", "moneyhub styles", "moneyhub doctor"):
        assert flag in html


def test_job_api_rejects_unknown_look_values():
    r = client.post("/api/jobs", data={"niche": "nurse", "product_type": "weekly_planner", "fonts": "nope"})
    assert r.status_code == 422
