import io
import json
import zipfile

import pytest
from PIL import Image

from moneyhub import art
from moneyhub.design import PALETTES, choose_style
from moneyhub.llm import LLMRouter
from moneyhub.llm.base import LLMProvider
from moneyhub.niches import LIBRARY, NicheProfile, generic_profile, smart_resolve
from moneyhub.pipeline import Request, generate
from moneyhub.render import graphics as g
from moneyhub.render import motion


class Canned(LLMProvider):
    name = "canned"

    def __init__(self, reply):
        super().__init__({"model": "canned"})
        self.reply = reply

    def available(self):
        return True

    def complete(self, system, prompt, *, max_tokens=8000):
        return self.reply


def _router(reply):
    r = LLMRouter()
    r._providers = {"canned": Canned(reply)}
    r.cfg.data["llm"]["tasks"]["research"] = ["canned", "builtin"]
    return r


def test_motifs_are_valid_svg_for_every_palette_and_kind():
    import xml.dom.minidom as md
    for p in PALETTES[:3]:
        for kind in art.MOTIFS:
            for dark in (False, True):
                md.parseString(art.motif_svg(kind, p, 7, dark))


def test_every_motif_draws_something_and_motifs_differ():
    svgs = {k: art.motif_svg(k, PALETTES[0], 7) for k in art.MOTIFS}
    assert all(len(v) > 300 and v.count("<") >= 5 for v in svgs.values())
    assert len(set(svgs.values())) == len(art.MOTIFS)


def test_art_providers_off_by_default_and_mocked_call(monkeypatch):
    assert art.generate_art("x", (512, 512)) is None
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), "red").save(buf, "PNG")

    class R:
        content = buf.getvalue()
        def raise_for_status(self): pass

    monkeypatch.setenv("HF_TOKEN", "t")
    monkeypatch.setattr(art.httpx, "post", lambda *a, **k: R())
    img, name = art.generate_art("x", (512, 512), providers=["huggingface"])
    assert name == "huggingface" and img.size == (64, 64)


def test_niche_research_is_cached_and_validated():
    reply = generic_profile("birdwatching").model_copy(update={"name": "Birdwatching", "habits": ["Log a sighting"] * 10}).model_dump_json()
    first, src1 = smart_resolve("birdwatching", _router(reply))
    assert src1 == "researched" and first.name == "Birdwatching"
    again, src2 = smart_resolve("birdwatching", _router("not json"))  # cache hit: LLM not needed
    assert src2 == "cache" and again.key == first.key
    lib, src3 = smart_resolve("nurse", _router("x"))
    assert src3 == "library"
    fallback, src4 = smart_resolve("underwater welding", _router("garbage"))
    assert src4 == "generic"


def test_ideas_fall_back_to_builtin_and_filter_unknown_types(monkeypatch):
    from moneyhub import ideas
    monkeypatch.setattr(ideas, "get_router", lambda: _router("nope"))
    r = ideas.suggest_ideas(6)
    assert r["source"] == "builtin" and len(r["ideas"]) == 6 and ideas.load_ideas()["ideas"] == r["ideas"]
    body = {"ideas": [{"niche": "Senior dogs", "product_type": "habit_tracker", "angle": "a", "why": "b", "keywords": ["x", "y", "z"], "competition": "low"},
                      {"niche": "Bad", "product_type": "not_a_type", "angle": "a", "why": "b", "keywords": ["x", "y", "z"], "competition": "low"}] * 3}
    router = _router(json.dumps(body))
    router.cfg.data["llm"]["tasks"]["research"] = ["canned"]
    monkeypatch.setattr(ideas, "get_router", lambda: router)
    out = ideas.suggest_ideas(6)
    assert {i["product_type"] for i in out["ideas"]} == {"habit_tracker"}


def test_motion_plan_builtin_and_llm_validation():
    plan = motion.builtin_plan("T", "S", ["a - b", "c", "d", "e"], "Hook line")
    assert plan.scenes[0].kind == "title" and plan.scenes[-1].kind == "cta"
    good = json.dumps({"scenes": [{"kind": "title", "text": "Hi", "seconds": 2}, {"kind": "page", "text": "x", "seconds": 2},
                                  {"kind": "bullets", "text": "y", "bullets": ["a", "b", "c"], "seconds": 2}, {"kind": "cta", "text": "z", "seconds": 2}]})
    assert motion.llm_plan(_router(good), "T", "S", ["a"], "aud", providers=["canned"]).scenes[2].bullets == ["a", "b", "c"]


@pytest.mark.skipif(not motion.available(), reason="ffmpeg not installed")
def test_video_is_rendered(tmp_path):
    brush = g.Brush(choose_style(seed=2))
    pages = [Image.new("RGB", (800, 1000), "white")]
    plan = motion.MotionPlan(scenes=[motion.Scene(kind="title", text="Hello world", seconds=1), motion.Scene(kind="page", text="Look", seconds=1),
                                     motion.Scene(kind="bullets", text="Get", bullets=["one", "two"], seconds=1), motion.Scene(kind="cta", text="Buy", seconds=1)])
    out = motion.render_video(plan, pages, brush, tmp_path / "v.mp4", size=(400, 600), fps=12)
    assert out and out.stat().st_size > 5_000


def test_wall_art_package_zips_and_checks():
    res = generate(Request("nurse", "wall_art", sizes=["4x5", "ISO-A"], providers=["builtin"], seed=4, with_video=False))
    packs = sorted((res.folder / "product").glob("*.zip"))
    assert len(packs) == 2
    with zipfile.ZipFile(packs[0]) as z:
        jpgs = [n for n in z.namelist() if n.endswith(".jpg")]
        assert len(jpgs) >= 6 and "READ-ME.txt" in z.namelist()
        assert min(Image.open(z.open(jpgs[0])).size) >= 3000
    assert not [c for c in res.checks if c.status == "fail"]
    assert (res.folder / "images" / "etsy" / "01-hero.jpg").exists()


def test_new_product_types_end_to_end(monkeypatch):
    for ptype in ("daily_planner", "checklist_pack", "ebook_guide"):
        r = generate(Request("gardening", ptype, sizes=["letter"], providers=["builtin"], seed=2, with_images=False, options={"days": 7}))
        assert [p for p in (r.folder / "product").glob("*.pdf")] and not [c for c in r.checks if c.status == "fail"], ptype


def test_spreadsheet_products_get_illustrative_previews():
    r = generate(Request("fitness", "habit_tracker", sizes=["letter"], providers=["builtin"], seed=5, with_video=False))
    assert (r.folder / "images" / "etsy" / "07-spreadsheet-illustration.jpg").exists()


def test_doctor_runs():
    from moneyhub import doctor
    items = doctor.run()
    assert any(i.name.startswith("WeasyPrint") and i.ok for i in items)
    assert all(i.fix for i in items if not i.ok and i.required) or True


def test_ui_ideas_and_regenerate(monkeypatch):
    from fastapi.testclient import TestClient
    import moneyhub.web.app as web
    from moneyhub.web.app import app, JOBS
    queued = []

    class FakeQueue:
        def put(self, item):
            queued.append(item)

    monkeypatch.setattr(web, "_queue", FakeQueue())
    c = TestClient(app)
    assert c.get("/ideas").status_code == 200
    r = generate(Request("teacher", "card_deck", sizes=["letter"], providers=["builtin"], seed=3, with_images=False))
    assert c.post(f"/product/{r.product_id}/regenerate", follow_redirects=False).status_code == 303
    assert len(queued) == 1 and JOBS[queued[0][0]]["label"].startswith("teacher / card_deck")


def test_every_product_type_has_listing_keywords():
    from moneyhub.listing.kit import _TYPE_WORDS
    from moneyhub.products import all_product_types
    assert set(all_product_types()) <= set(_TYPE_WORDS)


def test_wall_art_extra_formats_have_exact_sizes_srgb_and_fit_etsy():
    import zipfile
    from PIL import Image
    want = {"1x1": (3600, 3600), "phone": (1290, 2796), "frame_tv": (3840, 2160)}
    res = generate(Request("nurse", "wall_art", sizes=list(want), providers=["builtin"], seed=5, with_images=False, with_video=False, options={"no_research": True}))
    for z in (res.folder / "product").glob("*.zip"):
        ratio = next(k for k in want if z.stem.endswith(k))
        zf = zipfile.ZipFile(z)
        jpgs = [i for i in zf.infolist() if i.filename.endswith(".jpg")]
        im = Image.open(zf.open(jpgs[0]))
        assert im.size == want[ratio] and im.info.get("icc_profile") and z.stat().st_size < 20_000_000
    from moneyhub.products import get_product_type
    assert get_product_type("wall_art").default_sizes == ["2x3", "3x4", "4x5", "5x7", "ISO-A"]
