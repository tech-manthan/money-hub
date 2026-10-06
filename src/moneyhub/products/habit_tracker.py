"""Habit tracker: Excel/Google-Sheets workbook + printable monthly PDFs."""
from __future__ import annotations

import random

import xlsxwriter
from pydantic import BaseModel, Field

from ..niches import NicheProfile
from ..render.raster import pdf_page_count
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .registry import register
from .xlsx_common import XlsxTheme, protect


class HabitContent(BaseModel):
    title: str
    subtitle: str = "Monthly habit tracker"
    tagline: str = Field(description="One short, warm line (<= 70 chars)")
    habits: list[str] = Field(min_length=6, max_length=14, description="Habit names, <= 4 words each, specific to the niche")
    reminders: list[str] = Field(min_length=4, max_length=12, description="Short footer encouragements (<= 60 chars)")
    tips: list[str] = Field(min_length=3, max_length=6, description="Short how-to-use steps for the spreadsheet")


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


@register
class HabitTracker(ProductType[HabitContent]):
    key = "habit_tracker"
    label = "Habit tracker"
    description = "Interactive spreadsheet (checkboxes, auto % and chart) plus 12 printable monthly trackers."
    content_model = HabitContent
    default_sizes = ["letter", "a4"]
    price_range = (4.0, 10.0)
    typical_formats = "XLSX (Excel / Google Sheets) + PDF"

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> HabitContent:
        habits = list(dict.fromkeys(niche.habits))[:10]
        reminders = list(niche.affirmations) * 2
        return HabitContent(
            title=f"{niche.name} Habit Tracker",
            tagline=niche.tagline[:70],
            habits=habits,
            reminders=reminders[:10],
            tips=[
                "Choose the month and year at the top of the Tracker sheet.",
                "Tick a box each day you complete a habit. Percentages update automatically.",
                "Rename any habit by typing over it. Add up to 14 habits.",
                "Check the Insights sheet for your best habits and streaks.",
            ],
        )

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return (
            "Write the content for a MONTHLY HABIT TRACKER for this niche: 8-12 concrete, specific daily habits "
            "(not vague like 'be healthy'), short encouraging footer lines, and 4 how-to steps for the spreadsheet."
        )

    def build(self, ctx: BuildContext, content: HabitContent) -> BuildResult:
        slug = self.slug(content.title)
        xlsx_path = ctx.out_dir / f"{slug}.xlsx"
        _build_xlsx(xlsx_path, content, ctx)
        files = [ProductFile(xlsx_path, "xlsx", "Excel / Google Sheets workbook (checkboxes, auto % & chart)", True)]
        renderer, pages = "", 0
        jobs = [(ctx.page(s), ctx.out_dir / f"{slug}-printable-{s}.pdf", {"content": content}) for s in ctx.sizes]
        renderer = self.render_jobs(ctx, "habit_tracker_print.html.j2", jobs, extra_css=_HT_CSS, margin=2.6)
        for page, out, _ in jobs:
            _repeat_page(out, page_index=1, copies=11)  # one month page rendered once, cloned for 12 months
            pages = pdf_page_count(out)
            files.append(ProductFile(out, "pdf", f"{page.label} - printable", True, preview_pages=[0, 1, 2]))
        features = [
            "Interactive spreadsheet: tick boxes, progress % updates automatically",
            "Built-in progress chart and daily completion row",
            f"{len(content.habits)} pre-filled habits - or type your own",
            "12 printable monthly trackers (PDF)",
            f"Designed for {ctx.niche.audience}",
            "Works in Excel, Google Sheets and Numbers",
        ]
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer,
                           meta={"sheet_kind": "habit", "habits": content.habits})


def _repeat_page(pdf, page_index: int, copies: int) -> None:
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(pdf))
    writer = PdfWriter()
    for pg in reader.pages:
        writer.add_page(pg)
    for _ in range(copies):
        writer.add_page(reader.pages[page_index])
    with open(pdf, "wb") as fh:
        writer.write(fh)


_HT_CSS = """
.ht { flex:1; display:flex; flex-direction:column; border:1px solid var(--line); border-radius:var(--radius); overflow:hidden; min-height:0; }
.ht-row { flex:1; display:flex; border-bottom:1px solid var(--line); min-height:0; }
.ht-row:last-child { border-bottom:0; }
.ht-head { flex:none; height:1.9em; background:var(--soft); font-weight:700; color:var(--accent); }
.ht-name { flex:none; width:11em; padding:0 .5em; font-size:.8em; display:flex; align-items:center; border-right:1px solid var(--line); }
.ht-head .ht-name { font-family:var(--font-h); }
.ht-cell { flex:1; display:flex; align-items:center; justify-content:center; border-right:1px solid var(--line); font-size:.55em; min-width:0; }
.ht-cell .sq { width:.9em; height:.9em; }
"""


def _build_xlsx(path, content: HabitContent, ctx: BuildContext) -> None:
    pal = ctx.style.palette
    t = XlsxTheme.from_palette(pal, ctx.style.fonts.body)
    wb = xlsxwriter.Workbook(str(path))
    wb.set_properties({"title": content.title, "subject": content.subtitle, "comments": "Generated by MoneyHub"})
    f = t.formats(wb)

    # ---- Guide -------------------------------------------------------
    g = wb.add_worksheet("Start Here")
    g.hide_gridlines(2)
    g.set_column("A:A", 3); g.set_column("B:B", 90)
    g.set_row(1, 38)
    g.write("B2", content.title, f["title"])
    g.write("B3", content.tagline, f["tagline"])
    for i, tip in enumerate(content.tips):
        g.write(4 + i, 1, f"{i + 1}.  {tip}", f["body"])
        g.set_row(4 + i, 24)
    g.write(4 + len(content.tips) + 1, 1, "Tip: duplicate the Tracker sheet for a new month (right-click the tab > Move or Copy).", f["note"])

    # ---- Tracker ----------------------------------------------------
    ws = wb.add_worksheet("Tracker")
    ws.hide_gridlines(2)
    ws.freeze_panes(7, 2)
    ws.set_column("A:A", 2)
    ws.set_column("B:B", 26)
    ws.set_column("C:AG", 3.6)
    ws.set_column("AH:AH", 11)
    ws.set_row(1, 34)
    ws.merge_range("B2:AH2", content.title, f["title"])
    ws.write("B4", "Month", f["label"])
    ws.merge_range("C4:H4", "January", f["input_u"])
    ws.data_validation("C4", {"validate": "list", "source": MONTHS})
    ws.write("J4", "Year", f["label"])
    ws.merge_range("K4:N4", 2026, f["input_u"])
    ws.write("P4", "Days", f["label"])
    ws.write_formula("Q4", "=DAY(EOMONTH(DATE($K$4,MATCH($C$4,{\"January\",\"February\",\"March\",\"April\",\"May\",\"June\",\"July\",\"August\",\"September\",\"October\",\"November\",\"December\"},0),1),0))", f["calc"], 31)
    # header row
    ws.write("B7", "Habit", f["th"])
    for d in range(31):
        ws.write(6, 2 + d, d + 1, f["th_c"])
    ws.write(6, 33, "Done %", f["th_c"])
    n_rows = 14
    first = 7
    for r in range(n_rows):
        row = first + r
        ws.set_row(row, 21)
        name = content.habits[r] if r < len(content.habits) else ""
        ws.write(row, 1, name, f["habit_u"])
        for d in range(31):
            ws.insert_checkbox(row, 2 + d, False, f["cell_u"])
        rng = f"C{row + 1}:AG{row + 1}"
        ws.write_formula(row, 33, f'=IF(B{row + 1}="","",COUNTIF({rng},TRUE)/$Q$4)', f["pct"])
    last = first + n_rows - 1
    # grey out days past month end
    ws.conditional_format(first, 2, last, 32, {"type": "formula", "criteria": "=COLUMN()-2>$Q$4", "format": f["greyed"]})
    ws.conditional_format(first, 2, last, 32, {"type": "cell", "criteria": "==", "value": "TRUE", "format": f["done"]})
    ws.conditional_format(first, 33, last, 33, {"type": "data_bar", "bar_color": pal.accent, "bar_solid": True, "min_type": "num", "min_value": 0, "max_type": "num", "max_value": 1})
    # daily row
    drow = last + 2
    ws.write(drow, 1, "Habits done today", f["th"])
    for d in range(31):
        col = 2 + d
        letter = xlsxwriter.utility.xl_col_to_name(col)
        ws.write_formula(drow, col, f"=COUNTIF({letter}{first + 1}:{letter}{last + 1},TRUE)", f["th_c"])
    ws.write(drow + 2, 1, "Overall completion", f["label"])
    ws.merge_range(drow + 2, 2, drow + 2, 5, "", f["bigpct"])
    ws.write_formula(drow + 2, 2, f'=IFERROR(SUMPRODUCT((B{first + 1}:B{last + 1}<>"")*(C{first + 1}:AG{last + 1}=TRUE))/(COUNTIF(B{first + 1}:B{last + 1},"?*")*$Q$4),0)', f["bigpct"], 0)
    ws.write(drow + 4, 1, "Notes", f["label"])
    ws.merge_range(drow + 4, 2, drow + 8, 33, "", f["notebox_u"])

    # ---- Insights ---------------------------------------------------
    ins = wb.add_worksheet("Insights")
    ins.hide_gridlines(2)
    ins.set_column("A:A", 2); ins.set_column("B:B", 28); ins.set_column("C:D", 14)
    ins.write("B2", "Insights", f["title"])
    ins.write("B4", "Habit", f["th"]); ins.write("C4", "Days done", f["th_c"]); ins.write("D4", "Completion", f["th_c"])
    for r in range(n_rows):
        tr = first + r + 1
        ins.write_formula(4 + r, 1, f'=IF(Tracker!B{tr}="","",Tracker!B{tr})', f["habit"], "")
        ins.write_formula(4 + r, 2, f'=IF(Tracker!B{tr}="","",COUNTIF(Tracker!C{tr}:AG{tr},TRUE))', f["cell_c"], "")
        ins.write_formula(4 + r, 3, f'=IF(Tracker!B{tr}="","",Tracker!AH{tr})', f["pct"], "")
    chart = wb.add_chart({"type": "bar"})
    chart.add_series({
        "name": "Completion",
        "categories": f"=Insights!$B$5:$B${4 + len(content.habits)}",
        "values": f"=Insights!$D$5:$D${4 + len(content.habits)}",
        "fill": {"color": pal.accent},
        "data_labels": {"value": True, "num_format": "0%"},
    })
    chart.set_title({"name": "Habit completion this month", "name_font": {"size": 12, "color": pal.ink}})
    chart.set_legend({"none": True})
    chart.set_x_axis({"min": 0, "max": 1, "num_format": "0%", "major_gridlines": {"visible": True, "line": {"color": pal.line}}})
    chart.set_y_axis({"reverse": True})
    chart.set_size({"width": 620, "height": 380})
    ins.insert_chart("F4", chart)
    protect(ws, ctx.options.get("protect_sheets", True))
    protect(ins, ctx.options.get("protect_sheets", True))
    wb.close()
