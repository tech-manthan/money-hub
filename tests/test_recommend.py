from moneyhub.growth import recommend
from moneyhub.store import Store


def _product(st: Store, niche: str, ptype: str, style: str = "sage-modern-rule") -> int:
    return st.add_product(slug=f"{niche}-{ptype}-{len(st.products())}", title=f"{niche} {ptype}", niche=niche.lower(), niche_name=niche, product_type=ptype,
                          style=style, status="draft", folder="x", price=5.0, qa=[], fingerprint="f", content_source="builtin", listing_source="builtin", spec="{}")


def test_without_data_it_suggests_untried_products_and_says_so(tmp_path):
    r = recommend(Store(tmp_path / "a.sqlite"))
    assert r["basis"] == "none" and r["make_next"] and "No results recorded" in r["note"]


def test_a_sale_steers_suggestions_toward_what_worked(tmp_path):
    st = Store(tmp_path / "b.sqlite")
    winner = _product(st, "Nurse", "weekly_planner", "plum-classic-box")
    _product(st, "Teacher", "habit_tracker")
    st.add_sale(winner, "etsy", "2026-10-01", 3, 21.0)
    r = recommend(st)
    assert r["basis"] == "sales" and "3 recorded sale" in r["note"]
    first = r["make_next"][0]
    assert first["niche"] == "Nurse" and first["product_type"] != "weekly_planner" and first["kind"] == "same audience"
    assert any(x["kind"] == "new audience" and x["product_type"] == "weekly_planner" for x in r["make_next"])
    assert r["good_looks"][0] == "plum"


def test_views_alone_are_labelled_a_weak_signal(tmp_path):
    st = Store(tmp_path / "c.sqlite")
    p = _product(st, "Nurse", "weekly_planner")
    st.add_metric(p, "etsy", "2026-10-01", 200, 12, 5)
    assert recommend(st)["basis"] == "engagement" and "weak signal" in recommend(st)["note"]
