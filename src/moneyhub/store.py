"""SQLite catalog: products, listings and sales, so you can learn which niche/product/style sells."""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .config import get_config

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT UNIQUE, title TEXT, niche TEXT, niche_name TEXT, product_type TEXT, style TEXT,
  status TEXT DEFAULT 'draft', created REAL, folder TEXT, price REAL, qa TEXT, fingerprint TEXT,
  content_source TEXT, listing_source TEXT, spec TEXT, notes TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS listings (
  id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, marketplace TEXT, url TEXT, price REAL, listed REAL
);
CREATE TABLE IF NOT EXISTS sales (
  id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, marketplace TEXT, day TEXT, units INTEGER, revenue REAL
);
CREATE TABLE IF NOT EXISTS metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, marketplace TEXT, day TEXT, views INTEGER, favourites INTEGER, pin_clicks INTEGER
);
"""


class Store:
    def __init__(self, path: Path | None = None):
        self.path = Path(path or get_config().db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def conn(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    def add_product(self, **f) -> int:
        f.setdefault("created", time.time())
        for k in ("qa", "spec"):
            if k in f and not isinstance(f[k], str):
                f[k] = json.dumps(f[k])
        cols = ", ".join(f)
        with self.conn() as c:
            cur = c.execute(f"INSERT INTO products ({cols}) VALUES ({', '.join('?' for _ in f)})", list(f.values()))
            return cur.lastrowid

    def products(self, status: str | None = None) -> list[dict]:
        q, args = "SELECT * FROM products", []
        if status:
            q, args = q + " WHERE status=?", [status]
        with self.conn() as c:
            return [dict(r) for r in c.execute(q + " ORDER BY created DESC", args)]

    def product(self, pid: int) -> dict | None:
        with self.conn() as c:
            r = c.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
            return dict(r) if r else None

    def set_status(self, pid: int, status: str, notes: str | None = None) -> None:
        with self.conn() as c:
            c.execute("UPDATE products SET status=? WHERE id=?", (status, pid))
            if notes is not None:
                c.execute("UPDATE products SET notes=? WHERE id=?", (notes, pid))

    def delete_product(self, pid: int) -> None:
        with self.conn() as c:
            for t in ("listings", "sales", "metrics"):
                c.execute(f"DELETE FROM {t} WHERE product_id=?", (pid,))
            c.execute("DELETE FROM products WHERE id=?", (pid,))

    def add_listing(self, pid: int, marketplace: str, url: str, price: float) -> None:
        with self.conn() as c:
            c.execute("INSERT INTO listings (product_id, marketplace, url, price, listed) VALUES (?,?,?,?,?)",
                      (pid, marketplace, url, price, time.time()))
            c.execute("UPDATE products SET status='listed' WHERE id=?", (pid,))

    def listings(self, pid: int) -> list[dict]:
        with self.conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM listings WHERE product_id=?", (pid,))]

    def add_sale(self, pid: int, marketplace: str, day: str, units: int, revenue: float) -> None:
        with self.conn() as c:
            c.execute("INSERT INTO sales (product_id, marketplace, day, units, revenue) VALUES (?,?,?,?,?)",
                      (pid, marketplace, day, units, revenue))

    def add_metric(self, pid: int, marketplace: str, day: str, views: int, favourites: int, pin_clicks: int) -> None:
        with self.conn() as c:
            c.execute("INSERT INTO metrics (product_id, marketplace, day, views, favourites, pin_clicks) VALUES (?,?,?,?,?,?)",
                      (pid, marketplace, day, views, favourites, pin_clicks))

    def performance(self) -> list[dict]:
        """Per product: views, favourites, units and revenue so you can see what to make more of."""
        with self.conn() as c:
            rows = c.execute("""
              SELECT p.id, p.title, p.niche_name, p.product_type, p.style, p.status,
                     COALESCE((SELECT SUM(units) FROM sales s WHERE s.product_id=p.id),0) AS units,
                     COALESCE((SELECT SUM(revenue) FROM sales s WHERE s.product_id=p.id),0) AS revenue,
                     COALESCE((SELECT SUM(views) FROM metrics m WHERE m.product_id=p.id),0) AS views,
                     COALESCE((SELECT SUM(favourites) FROM metrics m WHERE m.product_id=p.id),0) AS favourites
              FROM products p ORDER BY revenue DESC, views DESC""")
            return [dict(r) for r in rows]

    def fingerprints(self) -> list[tuple[int, str, str]]:
        with self.conn() as c:
            return [(r["id"], r["title"], r["fingerprint"] or "") for r in c.execute("SELECT id, title, fingerprint FROM products")]
