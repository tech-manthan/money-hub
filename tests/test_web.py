

def test_my_products_has_a_filter_per_product_type(monkeypatch):
    from fastapi.testclient import TestClient

    from moneyhub.web import app as webapp
    rows = [{"id": i, "title": f"T{i}", "niche_name": "Nurse", "product_type": t, "price": 5, "status": "draft", "qa_status": "pass", "thumb": None}
            for i, t in enumerate(["wall_art", "wall_art", "oracle_deck"], 1)]
    monkeypatch.setattr(webapp, "_catalogue", lambda: rows)
    html = TestClient(webapp.app).get("/products").text
    assert "All (3)" in html and "Wall art (2)" in html and "Oracle deck (1)" in html
    assert html.count('data-kind="wall_art"') == 3   # the button and two cards
    monkeypatch.setattr(webapp, "_catalogue", lambda: rows[:1])
    assert 'id="kinds"' not in TestClient(webapp.app).get("/products").text   # one kind: no filter bar
