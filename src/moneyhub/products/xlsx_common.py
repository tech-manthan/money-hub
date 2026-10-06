"""Shared spreadsheet styling."""
from __future__ import annotations

from dataclasses import dataclass

from ..design import Palette

_FONT = {
    "DMSans": "DM Sans", "Inter": "Inter", "Nunito": "Nunito", "Lora": "Lora",
    "PlayfairDisplay": "Playfair Display", "Fraunces": "Fraunces", "Poppins": "Poppins",
}


@dataclass
class XlsxTheme:
    palette: Palette
    font: str

    @classmethod
    def from_palette(cls, palette: Palette, font_family: str) -> "XlsxTheme":
        # Spreadsheets open on machines without our fonts; fall back to Calibri/Arial-safe names.
        return cls(palette, "Calibri")

    def formats(self, wb) -> dict:
        p, fn = self.palette, self.font

        def mk(**kw):
            base = {"font_name": fn, "font_size": 11, "valign": "vcenter", "font_color": p.ink}
            base.update(kw)
            return wb.add_format(base)

        border = {"border": 1, "border_color": p.line}
        unlocked = {"locked": False}
        return {
            # --- editable (unlocked) variants: cells the buyer is meant to type in or tick ---
            "text_u": mk(**border, **unlocked),
            "habit_u": mk(**border, **unlocked),
            "cell_u": mk(align="center", **border, **unlocked),
            "date_u": mk(num_format="yyyy-mm-dd", align="center", **border, **unlocked),
            "money_u": mk(num_format='$#,##0.00', **border, **unlocked),
            "money_in_u": mk(num_format='$#,##0.00', bg_color="#FFF8DC", **border, **unlocked),
            "input_u": mk(bold=True, bg_color=p.soft, align="center", **border, **unlocked),
            "notebox_u": mk(**border, bg_color="#FFFFFF", **unlocked),
            "title": mk(font_size=22, bold=True, font_color=p.accent),
            "tagline": mk(font_size=12, italic=True, font_color=p.muted),
            "body": mk(text_wrap=True, valign="top"),
            "note": mk(italic=True, font_color=p.muted),
            "label": mk(bold=True, font_color=p.accent, font_size=10),
            "input": mk(bold=True, bg_color=p.soft, align="center", **border),
            "calc": mk(bg_color=p.soft, align="center", font_color=p.muted, **border),
            "th": mk(bold=True, bg_color=p.accent, font_color=p.accent_ink, **border),
            "th_c": mk(bold=True, bg_color=p.accent, font_color=p.accent_ink, align="center", **border),
            "habit": mk(**border),
            "cell": mk(align="center", **border),
            "cell_c": mk(align="center", **border),
            "pct": mk(num_format="0%", align="center", **border),
            "bigpct": mk(num_format="0%", font_size=20, bold=True, font_color=p.accent, align="center"),
            "notebox": mk(**border, bg_color="#FFFFFF"),
            "greyed": wb.add_format({"bg_color": p.line, "font_color": p.line}),
            "done": wb.add_format({"bg_color": p.soft}),
            "money": mk(num_format='$#,##0.00', **border),
            "money_in": mk(num_format='$#,##0.00', bg_color="#FFF8DC", **border),
            "money_b": mk(num_format='$#,##0.00', bold=True, bg_color=p.soft, **border),
            "date": mk(num_format="yyyy-mm-dd", align="center", **border),
            "text": mk(**border),
            "text_b": mk(bold=True, bg_color=p.soft, **border),
            "group": mk(bold=True, bg_color=p.soft, font_color=p.accent, **border),
            "kpi": mk(font_size=20, bold=True, font_color=p.accent, num_format='$#,##0', align="center", bg_color=p.soft, border=1, border_color=p.soft),
            "kpi_pct": mk(font_size=20, bold=True, font_color=p.accent, num_format='0%', align="center", bg_color=p.soft, border=1, border_color=p.soft),
            "kpi_label": mk(font_size=9, bold=True, font_color=p.muted, align="center", bg_color=p.soft, border=1, border_color=p.soft),
            "red": wb.add_format({"font_color": "#B3261E", "bold": True}),
            "green": wb.add_format({"font_color": "#1B6B3A", "bold": True}),
        }


PROTECT_OPTIONS = {
    "objects": True, "scenarios": True, "format_cells": True, "format_columns": True, "format_rows": True,
    "insert_rows": True, "delete_rows": True, "sort": True, "autofilter": True, "select_locked_cells": True, "select_unlocked_cells": True,
}


def protect(ws, enabled: bool = True) -> None:
    """Lock formula cells (everything not explicitly unlocked). No password so buyers can unprotect with Review > Unprotect."""
    if enabled:
        ws.protect("", PROTECT_OPTIONS)
