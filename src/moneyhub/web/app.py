"""Local web UI: create products, review them, copy listing text, track listings and sales."""
from __future__ import annotations

import json
import queue
import threading
import time
import traceback
import uuid
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..config import get_config
from ..design import PALETTES
from ..llm import get_router
from ..niches import LIBRARY, resolve_niche
from ..pipeline import Request as GenRequest, generate
from ..products import all_product_types
from ..render.html import PAGE_SIZES
from ..render.raster import pdf_page_count, render_pages
from ..store import Store

HERE = Path(__file__).resolve().parent
app = FastAPI(title="MoneyHub")
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")
templates = Jinja2Templates(directory=str(HERE / "templates"))

JOBS: dict[str, dict] = {}
_queue: "queue.Queue[tuple[str, object]]" = queue.Queue()


def _worker() -> None:
    while True:
        jid, fn = _queue.get()
        job = JOBS[jid]
        job["status"] = "running"
        try:
            job.update(fn(job))
            job["status"] = "done"
        except Exception as e:  # noqa: BLE001
            job.update(status="error", error=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-1500:])
        finally:
            job["finished"] = time.time()
            _queue.task_done()


threading.Thread(target=_worker, daemon=True).start()


def _store() -> Store:
    return Store()


def _ctx(request: Request, **kw):
    return {"request": request, **kw}


def _first_image(folder: str) -> str | None:
    f = Path(folder) / "images" / "etsy" / "01-hero.jpg"
    return "images/etsy/01-hero.jpg" if f.exists() else None


# ------------------------------------------------------------------ pages
def _submit(label: str, fn) -> str:
    jid = uuid.uuid4().hex[:8]
    JOBS[jid] = {"status": "queued", "log": [], "created": time.time(), "label": label}
    _queue.put((jid, fn))
    return jid


def _gen_fn(req: GenRequest):
    def run(job):
        res = generate(req, progress=lambda m: job["log"].append(m))
        return {"product_id": res.product_id, "qa": res.qa_status}
    return run


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    products = _store().products()
    for p in products:
        p["thumb"] = _first_image(p["folder"])
        qa = json.loads(p["qa"] or "[]")
        p["qa_status"] = "fail" if any(c["status"] == "fail" for c in qa) else "warn" if any(c["status"] == "warn" for c in qa) else "pass"
    return templates.TemplateResponse(request, "index.html", _ctx(
        request, products=products, types=all_product_types(), niches=sorted(LIBRARY), size_map={k: t.size_options() for k, t in all_product_types().items()}, palettes=PALETTES,
        providers=get_router().status(), jobs=sorted(JOBS.items(), key=lambda kv: -kv[1]["created"])[:6]))


@app.get("/product/{pid}", response_class=HTMLResponse)
def product(request: Request, pid: int):
    st = _store()
    p = st.product(pid)
    if not p:
        raise HTTPException(404)
    folder = Path(p["folder"])
    listing = json.loads((folder / "listing" / "listing.json").read_text()) if (folder / "listing" / "listing.json").exists() else {}
    spec = json.loads((folder / "spec.json").read_text()) if (folder / "spec.json").exists() else {}
    files = [{"rel": str(f.relative_to(folder)), "size": f.stat().st_size} for f in sorted((folder / "product").glob("*"))]
    pdfs = [f for f in files if f["rel"].endswith(".pdf")]
    pages = []
    if pdfs:
        n = pdf_page_count(folder / pdfs[0]["rel"])
        pages = [{"url": f"/preview/{pid}/{pdfs[0]['rel']}/{i}.png"} for i in range(min(n, 10))]
    elif (folder / "art").exists():
        pages = [{"url": f"/files/{pid}/art/{f.name}"} for f in sorted((folder / "art").glob("preview-*.png"))]
    images = {}
    for m in ("etsy", "gumroad", "payhip", "kofi", "pinterest", "video"):
        d = folder / "images" / m
        images[m] = [str(x.relative_to(folder)) for x in sorted(d.glob("*"))] if d.exists() else []
    guides = {}
    for g in sorted((folder / "listing").glob("guide-*.md")):
        guides[g.stem.replace("guide-", "")] = g.read_text()
    return templates.TemplateResponse(request, "product.html", _ctx(
        request, p=p, qa=json.loads(p["qa"] or "[]"), listing=listing, spec=spec, files=files, pages=pages,
        images=images, guides=guides, listings=st.listings(pid), size=pdfs[0]["rel"] if pdfs else ""))


@app.get("/ideas", response_class=HTMLResponse)
def ideas_page(request: Request):
    from ..ideas import load_ideas
    return templates.TemplateResponse(request, "ideas.html", _ctx(request, data=load_ideas(), types=all_product_types()))


@app.post("/api/ideas")
def make_ideas(n: int = Form(15), focus: str = Form(""), llm: str = Form("")):
    from ..ideas import suggest_ideas
    provs = [x.strip() for x in llm.split(",") if x.strip()] or None
    return {"job": _submit(f"ideas: {focus or 'any'}", lambda job: {"ideas": len(suggest_ideas(n, focus or None, provs)["ideas"])})}


@app.post("/product/{pid}/regenerate")
def regenerate(pid: int):
    p = _store().product(pid)
    if not p:
        raise HTTPException(404)
    spec = json.loads((Path(p["folder"]) / "spec.json").read_text())
    r = spec["request"]
    _submit(f"{r['niche']} / {r['product_type']} (new variation)", _gen_fn(GenRequest(
        niche=r["niche"], product_type=r["product_type"], sizes=r.get("sizes"), options=r.get("options") or {})))
    return RedirectResponse("/", status_code=303)


@app.get("/report", response_class=HTMLResponse)
def report(request: Request):
    return templates.TemplateResponse(request, "report.html", _ctx(request, rows=_store().performance()))


@app.get("/settings", response_class=HTMLResponse)
def settings(request: Request):
    cfg = get_config()
    return templates.TemplateResponse(request, "settings.html", _ctx(
        request, providers=get_router().status(), tasks=cfg.get("llm.tasks"), out=str(cfg.output_dir),
        renderers=cfg.get("render.pdf"), art=__import__("moneyhub.art", fromlist=["art_status"]).art_status()))


# ------------------------------------------------------------------ actions
@app.post("/api/jobs")
def create_job(niche: str = Form(...), product_type: str = Form(...), sizes: list[str] = Form(default=[]),
               palette: str = Form(""), llm: str = Form(""), weeks: str = Form(""), seed: str = Form(""),
               ai_art: str = Form(""), no_video: str = Form("")):
    ids = []
    for n in [x.strip() for x in niche.split(",") if x.strip()]:
        req = GenRequest(
            niche=n, product_type=product_type, sizes=sizes or None, palette=palette or None,
            providers=[x.strip() for x in llm.split(",") if x.strip()] or None,
            seed=int(seed) if seed.strip().isdigit() else None,
            options={**({"weeks": int(weeks)} if weeks.strip().isdigit() else {}), **({"ai_art": True} if ai_art else {})},
            with_video=not no_video,
        )
        ids.append(_submit(f"{n} / {product_type}", _gen_fn(req)))
    return {"jobs": ids}


@app.get("/api/jobs/{jid}")
def job(jid: str):
    j = JOBS.get(jid)
    if not j:
        raise HTTPException(404)
    return j


@app.get("/api/niche")
def niche_preview(q: str):
    n = resolve_niche(q)
    return {"key": n.key, "name": n.name, "audience": n.audience, "in_library": n.key in LIBRARY}


@app.get("/files/{pid}/{path:path}")
def files(pid: int, path: str, download: int = 0):
    p = _store().product(pid)
    if not p:
        raise HTTPException(404)
    root = Path(p["folder"]).resolve()
    f = (root / path).resolve()
    if root not in f.parents or not f.is_file():
        raise HTTPException(404)
    return FileResponse(f, filename=f.name if download else None)


@app.get("/preview/{pid}/{pdf:path}/{page}.png")
def preview(pid: int, pdf: str, page: int):
    p = _store().product(pid)
    if not p:
        raise HTTPException(404)
    root = Path(p["folder"]).resolve()
    f = (root / pdf).resolve()
    if root not in f.parents or not f.is_file():
        raise HTTPException(404)
    cache = root / "previews" / f"{f.stem}-{page}.png"
    if not cache.exists():
        cache.parent.mkdir(exist_ok=True)
        imgs = render_pages(f, [page], 1.3)
        if not imgs:
            raise HTTPException(404)
        imgs[0].save(cache)
    return FileResponse(cache)


@app.post("/product/{pid}/status")
def set_status(pid: int, status: str = Form(...), notes: str = Form("")):
    if status not in {"draft", "approved", "rejected", "listed"}:
        raise HTTPException(400)
    _store().set_status(pid, status, notes)
    return RedirectResponse(f"/product/{pid}", status_code=303)


@app.post("/product/{pid}/delete")
def delete(pid: int):
    st = _store()
    p = st.product(pid)
    if p:
        import shutil
        shutil.rmtree(p["folder"], ignore_errors=True)
        st.delete_product(pid)
    return RedirectResponse("/", status_code=303)


@app.post("/product/{pid}/listing")
def add_listing(pid: int, marketplace: str = Form(...), url: str = Form(...), price: float = Form(0)):
    _store().add_listing(pid, marketplace, url, price)
    return RedirectResponse(f"/product/{pid}", status_code=303)


@app.post("/product/{pid}/sale")
def add_sale(pid: int, marketplace: str = Form(...), revenue: float = Form(...), units: int = Form(1), day: str = Form("")):
    import datetime as dt
    _store().add_sale(pid, marketplace, day or dt.date.today().isoformat(), units, revenue)
    return RedirectResponse("/report", status_code=303)


@app.post("/product/{pid}/metric")
def add_metric(pid: int, marketplace: str = Form(...), views: int = Form(0), favourites: int = Form(0), pin_clicks: int = Form(0), day: str = Form("")):
    import datetime as dt
    _store().add_metric(pid, marketplace, day or dt.date.today().isoformat(), views, favourites, pin_clicks)
    return RedirectResponse("/report", status_code=303)
