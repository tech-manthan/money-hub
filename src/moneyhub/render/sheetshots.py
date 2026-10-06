"""Illustrative spreadsheet previews (spreadsheet-window look) for listings, drawn from the product's own content and
colours with sample numbers. They show the real layout, but replace them with real screenshots of your finished workbook
when you can; buyers trust those most."""
from __future__ import annotations

import random

from PIL import Image, ImageDraw

from . import graphics as g


def _window(size, brush: g.Brush, title: str):
    W, H = size
    img = g._bg(size, brush)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = int(W * 0.06), int(H * 0.08), int(W * 0.94), int(H * 0.93)
    s = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(s).rounded_rectangle((x0 + 8, y0 + 20, x1 + 8, y1 + 20), 28, fill=(0, 0, 0, 70))
    from PIL import ImageFilter
    img.alpha_composite(s.filter(ImageFilter.GaussianBlur(24)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x0, y0, x1, y1), 24, fill=(255, 255, 255, 255))
    d.rounded_rectangle((x0, y0, x1, y0 + 78), 24, fill=(238, 238, 240, 255))
    d.rectangle((x0, y0 + 40, x1, y0 + 78), fill=(238, 238, 240, 255))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse((x0 + 34 + i * 44, y0 + 26, x0 + 58 + i * 44, y0 + 50), fill=c + (255,))
    d.text(((x0 + x1) // 2, y0 + 40), title, font=brush.body(30, True), fill=(90, 90, 96), anchor="mm")
    return img, d, (x0, y0 + 78, x1, y1)


def habit_shot(habits: list[str], title: str, brush: g.Brush, seed: int, size=(2700, 2025)) -> Image.Image:
    rng = random.Random(seed)
    img, d, (x0, y0, x1, y1) = _window(size, brush, f"{title}.xlsx - Tracker")
    pad = 40
    d.text((x0 + pad, y0 + 34), title, font=brush.heading(64), fill=brush.accent)
    d.text((x0 + pad, y0 + 118), "Month  March      Year  2026      Days  31", font=brush.body(30, True), fill=brush.muted)
    top = y0 + 190
    name_w, cells, cw = 520, 21, 62
    rh = min(118, (y1 - top - 250) // max(1, min(len(habits), 9) + 1))
    d.rectangle((x0 + pad, top, x0 + pad + name_w + cells * cw + 220, top + rh), fill=brush.accent)
    d.text((x0 + pad + 16, top + rh // 2), "Habit", font=brush.body(30), fill=brush.accent_ink, anchor="lm")
    for c in range(cells):
        d.text((x0 + pad + name_w + c * cw + cw // 2, top + rh // 2), str(c + 1), font=brush.body(24), fill=brush.accent_ink, anchor="mm")
    d.text((x0 + pad + name_w + cells * cw + 110, top + rh // 2), "Done %", font=brush.body(28), fill=brush.accent_ink, anchor="mm")
    for r, h in enumerate(habits[:9]):
        y = top + rh * (r + 1)
        d.rectangle((x0 + pad, y, x0 + pad + name_w + cells * cw + 220, y + rh), outline=brush.line, width=2)
        d.text((x0 + pad + 16, y + rh // 2), h[:30], font=brush.body(28, True), fill=brush.ink, anchor="lm")
        rate = rng.uniform(0.45, 0.95)
        done = 0
        for c in range(cells):
            cx, cy = x0 + pad + name_w + c * cw + cw // 2, y + rh // 2
            on = rng.random() < rate
            done += on
            d.rounded_rectangle((cx - 15, cy - 15, cx + 15, cy + 15), 5, outline=brush.accent, width=3, fill=brush.soft if on else (255, 255, 255))
            if on:
                d.line((cx - 8, cy, cx - 2, cy + 7, cx + 9, cy - 8), fill=brush.accent, width=4)
        pct = done / cells
        bx = x0 + pad + name_w + cells * cw + 20
        d.rectangle((bx, y + rh // 2 - 14, bx + 180, y + rh // 2 + 14), fill=brush.soft)
        d.rectangle((bx, y + rh // 2 - 14, bx + int(180 * pct), y + rh // 2 + 14), fill=brush.accent)
        d.text((bx + 190, y + rh // 2), f"{pct:.0%}", font=brush.body(24, True), fill=brush.muted, anchor="lm")
    d.text((x0 + pad, y1 - 150), "Tick the boxes - percentages and the chart update automatically", font=brush.script(60), fill=brush.accent)
    for i, t in enumerate(["Start Here", "Tracker", "Insights"]):
        col = brush.accent if t == "Tracker" else (200, 200, 205)
        d.rounded_rectangle((x0 + 30 + i * 260, y1 - 52, x0 + 270 + i * 260, y1), 12, fill=col)
        d.text((x0 + 150 + i * 260, y1 - 26), t, font=brush.body(26, True), fill=brush.accent_ink if t == "Tracker" else (80, 80, 86), anchor="mm")
    return img.convert("RGB")


def budget_shot(groups: list[tuple[str, int]], title: str, brush: g.Brush, seed: int, size=(2700, 2025)) -> Image.Image:
    rng = random.Random(seed)
    img, d, (x0, y0, x1, y1) = _window(size, brush, f"{title}.xlsx - Dashboard")
    pad = 40
    d.text((x0 + pad, y0 + 30), "Dashboard", font=brush.heading(64), fill=brush.accent)
    income = rng.randint(3000, 4600)
    spent = int(income * rng.uniform(0.62, 0.88))
    left = income - spent
    kw = (x1 - x0 - pad * 2 - 3 * 30) // 4
    for i, (lab, val) in enumerate([("INCOME", f"${income:,}"), ("SPENT", f"${spent:,}"), ("LEFT OVER", f"${left:,}"), ("SAVINGS RATE", f"{left / income:.0%}")]):
        x = x0 + pad + i * (kw + 30)
        d.rounded_rectangle((x, y0 + 130, x + kw, y0 + 300), 18, fill=brush.soft)
        d.text((x + kw // 2, y0 + 170), lab, font=brush.body(26, True), fill=brush.muted, anchor="mm")
        d.text((x + kw // 2, y0 + 240), val, font=brush.heading(64), fill=brush.accent, anchor="mm")
    # doughnut
    cx, cy, R = x0 + pad + 420, y0 + 700, 300
    shares = [rng.uniform(0.6, 1.6) for _ in groups] or [1]
    tot = sum(shares)
    cols = [brush.accent, brush.accent2, brush.muted, brush.line, tuple(int(c * .6) for c in brush.accent), brush.soft]
    a = -90.0
    for i, s in enumerate(shares):
        sweep = 360 * s / tot
        d.pieslice((cx - R, cy - R, cx + R, cy + R), a, a + sweep, fill=cols[i % len(cols)])
        a += sweep
    d.ellipse((cx - R * 0.55, cy - R * 0.55, cx + R * 0.55, cy + R * 0.55), fill=(255, 255, 255))
    d.text((cx, cy - R - 50), "Where the money went", font=brush.body(32, True), fill=brush.ink, anchor="mm")
    for i, (name, _) in enumerate(groups[:6]):
        d.rectangle((cx - R, cy + R + 40 + i * 0, cx - R, cy + R + 40), fill=None)
    lx, ly = cx - R, cy + R + 50
    for i, (name, _) in enumerate(groups[:6]):
        xx = lx + (i % 3) * 270
        yy = ly + (i // 3) * 44
        d.rectangle((xx, yy, xx + 24, yy + 24), fill=cols[i % len(cols)])
        d.text((xx + 34, yy + 12), name[:14], font=brush.body(24), fill=brush.muted, anchor="lm")
    # planned vs actual bars
    bx0, by1 = x0 + pad + 1050, y0 + 1020
    d.text((bx0 + 420, y0 + 380), "Planned vs actual", font=brush.body(32, True), fill=brush.ink, anchor="mm")
    n = min(6, max(3, len(groups)))
    for i in range(n):
        planned = rng.randint(180, 520)
        actual = int(planned * rng.uniform(0.6, 1.25))
        x = bx0 + 40 + i * 150
        d.rectangle((x, by1 - planned, x + 52, by1), fill=brush.line)
        d.rectangle((x + 58, by1 - actual, x + 110, by1), fill=brush.accent)
        d.text((x + 55, by1 + 24), (groups[i][0] if i < len(groups) else "")[:9], font=brush.body(22), fill=brush.muted, anchor="mm")
    d.line((bx0, by1, bx0 + n * 150 + 40, by1), fill=brush.muted, width=2)
    for i, t in enumerate(["Start Here", "Dashboard", "Settings", "Transactions", "Budget", "Savings"]):
        col = brush.accent if t == "Dashboard" else (200, 200, 205)
        d.rounded_rectangle((x0 + 30 + i * 230, y1 - 52, x0 + 240 + i * 230, y1), 12, fill=col)
        d.text((x0 + 135 + i * 230, y1 - 26), t, font=brush.body(24, True), fill=brush.accent_ink if t == "Dashboard" else (80, 80, 86), anchor="mm")
    return img.convert("RGB")
