"""Sticker art: the friendly children's figures from kidsart.py, filled with a palette's colours instead of left white, plus little
decorations (stars, hearts, suns, clouds, flowers). Each sticker gets a white die-cut border so it reads as a real sticker, and stickers are
packed onto printable sheets. Everything is seeded, so every pack is different."""
from __future__ import annotations

import random
import re

from PIL import Image, ImageFilter

from . import kidsart
from .design import Palette

DECOR = ["star", "heart", "sun", "cloud"]
BORDER_IN = 0.07   # white die-cut margin around each sticker


def _mix(a: str, b: str, t: float) -> str:
    ra, rb = [int(a.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)], [int(b.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ra, rb))


def fills(pal: Palette) -> list[str]:
    return [pal.accent, pal.accent2, _mix(pal.accent, "#ffffff", .55), pal.soft, _mix(pal.accent2, "#ffffff", .5), _mix(pal.accent, pal.accent2, .5)]


def recolor(inner: str, pal: Palette, seed: int) -> str:
    """Replace the white fills (and the white core of limbs) with palette colours, and the dark ink with the palette's ink."""
    rng = random.Random(seed)
    cols = fills(pal)
    start = rng.randrange(len(cols))
    n = {"i": start}

    def nxt(m: re.Match) -> str:
        n["i"] += 1
        return f"{m.group(1)}'{cols[n['i'] % len(cols)]}'"
    inner = re.sub(r"(fill=)'#ffffff'", nxt, inner)
    inner = re.sub(r"(stroke=)'#ffffff'", lambda m: f"{m.group(1)}'{cols[start]}'", inner)
    return inner.replace(kidsart.INK, pal.ink)


def sticker_svg(i: int, seed: int, theme: str, pal: Palette) -> tuple[str, str]:
    """(name, svg) for sticker number i: three in four are figures from the theme, the rest decorations."""
    pool = list(kidsart.THEMES.get(theme, kidsart.THEMES["mixed"])[1])
    random.Random(seed).shuffle(pool)
    rng = random.Random(seed * 211 + i)
    if i % 4 == 3:
        kind = DECOR[(i // 4 + seed) % len(DECOR)]
        p = kidsart.Pen(rng, 12)
        kidsart._decor(p, (500, 500), kind, 640 if kind != "cloud" else 620)
        name = kind
        inner = p.svg()
    else:
        kind = pool[(i - i // 4) % len(pool)]
        name = kidsart.NAMES[kind]
        inner = kidsart.figure(kind, seed * 977 + i, 12, False)
    return name, f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 1000'>{recolor(inner, pal, seed * 13 + i)}</svg>"


def die_cut(im: Image.Image, dpi: int = 300) -> Image.Image:
    """Trim to the artwork and add the white sticker border (transparent outside)."""
    im = im.convert("RGBA")
    box = im.getchannel("A").getbbox()
    if not box:
        return im
    im = im.crop(box)
    r = round(BORDER_IN * dpi)
    pad = r + 4
    canvas = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    canvas.paste(im, (pad, pad), im)
    alpha = canvas.getchannel("A").point(lambda v: 255 if v > 20 else 0)
    grown = alpha.filter(ImageFilter.MaxFilter(2 * r + 1 if (2 * r + 1) % 2 else 2 * r + 3)).filter(ImageFilter.GaussianBlur(1.2)).point(lambda v: 255 if v > 127 else 0)
    out = Image.new("RGBA", canvas.size, (255, 255, 255, 0))
    out.paste(Image.new("RGBA", canvas.size, (255, 255, 255, 255)), (0, 0), grown)
    out.alpha_composite(canvas)
    return out


def pack_layout(sizes: list[tuple[int, int]], w_px: int, h_px: int, margin_px: int, cols: int = 3, rows: int = 4) -> list[tuple[int, int, int, int]]:
    """(x, y, width, height) of each sticker on a sheet: scaled to fit its grid cell and centred in it (never enlarged beyond the cell)."""
    cw, ch = (w_px - 2 * margin_px) / cols, (h_px - 2 * margin_px) / rows
    out = []
    for k, (iw, ih) in enumerate(sizes[: cols * rows]):
        s = min((cw - 40) / iw, (ch - 40) / ih)
        tw, th = max(1, round(iw * s)), max(1, round(ih * s))
        out.append((round(margin_px + (k % cols) * cw + (cw - tw) / 2), round(margin_px + (k // cols) * ch + (ch - th) / 2), tw, th))
    return out


def pack_sheet(stickers: list[Image.Image], w_px: int, h_px: int, margin_px: int, cols: int = 3, rows: int = 4, bg: str | None = None) -> Image.Image:
    """Lay stickers out in a grid (white sheet, or transparent when bg is "transparent")."""
    transparent = bg == "transparent"
    sheet = Image.new("RGBA", (w_px, h_px), (255, 255, 255, 0)) if transparent else Image.new("RGB", (w_px, h_px), bg or "#ffffff")
    for im, (x, y, tw, th) in zip(stickers, pack_layout([i.size for i in stickers], w_px, h_px, margin_px, cols, rows)):
        t = im.resize((tw, th), Image.LANCZOS)
        if transparent:
            sheet.alpha_composite(t, (x, y))
        else:
            sheet.paste(t, (x, y), t)
    return sheet


# --------------------------------------------------------------------------- cut lines (print then cut)
def _rdp(pts, eps: float):
    """Ramer-Douglas-Peucker simplification of an open polyline (list of (x, y))."""
    import numpy as np
    pts = np.asarray(pts, dtype=float)
    if len(pts) < 3:
        return pts.tolist()
    keep = np.zeros(len(pts), bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = pts[i], pts[j]
        ab = b - a
        n = np.hypot(*ab) or 1.0
        d = np.abs(ab[0] * (pts[i + 1:j, 1] - a[1]) - ab[1] * (pts[i + 1:j, 0] - a[0])) / n
        k = int(np.argmax(d))
        if d[k] > eps:
            keep[i + 1 + k] = True
            stack += [(i, i + 1 + k), (i + 1 + k, j)]
    return pts[keep].tolist()


def trace_outline(mask) -> list[tuple[int, int]]:
    """Outer boundary (Moore-neighbour tracing) of the first blob found in a boolean mask, as (x, y) pixel coordinates."""
    import numpy as np
    pad = np.pad(np.asarray(mask, bool), 1)
    ys, xs = np.nonzero(pad)
    if not len(ys):
        return []
    ring = [(-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1)]   # clockwise from north-west
    start = (int(ys[0]), int(xs[0]))
    cur, back = start, 7   # the pixel to the west of the first one is background
    path = [start]
    for _ in range(pad.size * 2):
        found = None
        for k in range(1, 9):
            idx = (back + k) % 8
            ny, nx = cur[0] + ring[idx][0], cur[1] + ring[idx][1]
            if pad[ny, nx]:
                pidx = (back + k - 1) % 8   # the background pixel examined just before this one
                bg = (cur[0] + ring[pidx][0], cur[1] + ring[pidx][1])
                found = ((ny, nx), (bg[0] - ny, bg[1] - nx))
                break
        if found is None:
            break
        cur, delta = found
        back = ring.index(delta)
        if cur == start:
            break
        path.append(cur)
    return [(x - 1, y - 1) for y, x in path]


def cut_paths(sticker: Image.Image, x: int, y: int, w: int, h: int, px_per_in: float, scale_dpi: int = 150, eps: float = 0.9) -> list[str]:
    """SVG path data (inches, sheet coordinates) outlining a sticker placed at (x, y) with size (w, h) on a sheet of px_per_in pixels per inch."""
    import numpy as np
    from scipy import ndimage

    k = scale_dpi / px_per_in
    small = sticker.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS).getchannel("A")
    mask = np.asarray(small) > 127
    labels, n = ndimage.label(mask)
    paths = []
    for lab in range(1, n + 1):
        comp = labels == lab
        if comp.sum() < 30:
            continue
        ring = trace_outline(comp)
        if len(ring) < 8:
            continue
        far = max(range(len(ring)), key=lambda i: (ring[i][0] - ring[0][0]) ** 2 + (ring[i][1] - ring[0][1]) ** 2)   # a closed ring is split in two for RDP
        pts = _rdp(ring[:far + 1], eps)[:-1] + _rdp(ring[far:] + [ring[0]], eps)[:-1]
        ox, oy = x / px_per_in, y / px_per_in
        paths.append("M" + " L".join(f"{ox + px / scale_dpi:.4f} {oy + py / scale_dpi:.4f}" for px, py in pts) + " Z")
    return paths
