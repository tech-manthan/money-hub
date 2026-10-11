"""Budget tracker: Excel/Google-Sheets workbook (formulas, dashboard, charts) + printable budget pages."""
from __future__ import annotations

import datetime as dt
import random

import xlsxwriter
from pydantic import BaseModel, Field

from ..niches import NicheProfile
from ..render.raster import pdf_page_count
from .base import BuildContext, BuildResult, ProductFile, ProductType
from .habit_tracker import MONTHS
from .registry import register
from .xlsx_common import XlsxTheme, protect


class ExpenseGroup(BaseModel):
    name: str
    categories: list[str] = Field(min_length=2, max_length=8)


class BudgetContent(BaseModel):
    title: str
    subtitle: str = "Monthly budget planner"
    tagline: str
    income: list[str] = Field(min_length=2, max_length=6, description="Income sources")
    expense_groups: list[ExpenseGroup] = Field(min_length=3, max_length=6)
    savings_goals: list[str] = Field(min_length=3, max_length=6)
    bills: list[str] = Field(min_length=6, max_length=18)
    tips: list[str] = Field(min_length=3, max_length=6)


@register
class BudgetTracker(ProductType[BudgetContent]):
    key = "budget_tracker"
    decor_ok = True
    layouts = {"classic": "Classic: income and savings left, expenses right, plus bills, savings, debt and year pages",
               "stacked": "Stacked: income and savings across the top, expenses in columns below",
               "essentials": "Essentials: three monthly pages and a big bill tracker, nothing else",
               "savers": "Savers: one monthly page, savings progress bars, short bill list"}
    auto_layout = True
    layout_marker = "Pay period"
    label = "Budget tracker"
    description = "Spreadsheet with transactions, monthly budget vs actual, savings goals, debt payoff and dashboard + printable budget pages."
    content_model = BudgetContent
    price_range = (7.0, 18.0)
    typical_formats = "XLSX (Excel / Google Sheets) + PDF"

    def builtin_content(self, niche: NicheProfile, rng: random.Random, options: dict) -> BudgetContent:
        groups = [
            ExpenseGroup(name="Home", categories=["Rent / mortgage", "Utilities", "Internet & phone", "Home supplies"]),
            ExpenseGroup(name="Food", categories=["Groceries", "Dining out", "Coffee & snacks"]),
            ExpenseGroup(name="Transport", categories=["Fuel / transit", "Car payment", "Insurance", "Maintenance"]),
            ExpenseGroup(name="Life", categories=["Health", "Subscriptions", "Entertainment", "Personal care", "Gifts"]),
        ]
        extra = niche.budget_extra or ["Other"]
        groups.append(ExpenseGroup(name=niche.name if niche.budget_extra else "Other", categories=(extra + ["Miscellaneous"])[:5]))
        return BudgetContent(
            title=f"{niche.name} Budget Planner" if niche.key != "personal_finance" else "Monthly Budget Planner",
            tagline=niche.tagline[:70],
            income=["Paycheck", "Side income", "Other income"],
            expense_groups=groups,
            savings_goals=["Emergency fund", "Holiday fund", "Big purchase", "Retirement top-up"],
            bills=["Rent / mortgage", "Electricity", "Water", "Internet", "Phone", "Insurance", "Car payment", "Streaming", "Gym", "Credit card"],
            tips=[
                "Pick the month and year on the Settings sheet.",
                "Log every purchase on the Transactions sheet and pick a category from the drop-down.",
                "Open Budget to see planned vs actual - green means on track, red means over.",
                "Watch the Dashboard for your savings rate and where the money went.",
            ],
        )

    def llm_brief(self, niche: NicheProfile, options: dict) -> str:
        return (
            "Write the content for a MONTHLY BUDGET SPREADSHEET and printable budget pages for this niche. "
            "Expense groups and categories must reflect this audience's real spending (3-6 groups, 3-6 categories each). "
            "Include realistic bills and savings goals for them."
        )

    def build(self, ctx: BuildContext, content: BudgetContent) -> BuildResult:
        slug = self.slug(content.title)
        xlsx_path = ctx.out_dir / f"{slug}.xlsx"
        _build_xlsx(xlsx_path, content, ctx)
        files = [ProductFile(xlsx_path, "xlsx", "Excel / Google Sheets workbook (formulas, dashboard, charts)", True)]
        renderer, pages = "", 0
        jobs = [(ctx.page(s), ctx.out_dir / f"{slug}-printable-{s}.pdf", {"content": content}) for s in ctx.sizes]
        renderer, lmeta = self.render_layout(ctx, "budget_print.html.j2", [(s, j[1]) for s, j in zip(ctx.sizes, jobs)], {"content": content}, lambda spec, page: _BUDGET_CSS, margin=2.8)
        for page, out, _ in jobs:
            pages = pdf_page_count(out)
            files.append(ProductFile(out, "pdf", f"{page.label} - printable", True, preview_pages=[0, 1, 3, 5]))
        features = [
            "Transactions log with category drop-downs",
            "Planned vs actual budget with automatic colour coding",
            "Dashboard: income, spending, savings rate and charts",
            "Savings goal tracker with progress bars",
            "Debt payoff tracker",
            "Printable monthly budget, bill tracker and savings pages (PDF)",
            f"Categories tailored for {ctx.niche.audience}",
        ]
        return BuildResult(content.title, content.subtitle, files, features, pages, renderer,
                           meta={"sheet_kind": "budget", "groups": [(g.name, len(g.categories)) for g in content.expense_groups], **lmeta})


_BUDGET_CSS = """
.tbl { display:flex; flex-direction:column; border:1px solid var(--line); border-radius:var(--radius); overflow:hidden; }
.tr { display:flex; border-bottom:1px solid var(--line); min-height:1.9em; flex:1; }
.tr:last-child { border-bottom:0; }
.tr.th { flex:none; background:var(--accent); color:var(--accent-ink); font-weight:700; font-size:.72em; letter-spacing:.06em; text-transform:uppercase; min-height:1.9em; }
.td { flex:1; padding:.25em .5em; font-size:.8em; border-right:1px solid var(--line); display:flex; align-items:center; min-width:0; }
.td:last-child { border-right:0; }
.th .td { border-right-color:rgba(255,255,255,.25); }
"""


def _build_xlsx(path, c: BudgetContent, ctx: BuildContext) -> None:
    pal = ctx.style.palette
    t = XlsxTheme.from_palette(pal, ctx.style.fonts.body)
    wb = xlsxwriter.Workbook(str(path))
    wb.set_properties({"title": c.title, "subject": c.subtitle, "comments": "Generated by MoneyHub"})
    f = t.formats(wb)

    categories = [cat for g in c.expense_groups for cat in g.categories]
    sheets = {n: wb.add_worksheet(n) for n in ["Start Here", "Dashboard", "Settings", "Transactions", "Budget", "Savings", "Debt Payoff"]}

    # ---- Start Here --------------------------------------------------
    g = sheets["Start Here"]
    g.hide_gridlines(2); g.set_column("A:A", 3); g.set_column("B:B", 90)
    g.set_row(1, 38)
    g.write("B2", c.title, f["title"]); g.write("B3", c.tagline, f["tagline"])
    for i, tip in enumerate(c.tips):
        g.write(4 + i, 1, f"{i + 1}.  {tip}", f["body"]); g.set_row(4 + i, 24)
    g.write(4 + len(c.tips) + 1, 1, "Tip: yellow-shaded cells are inputs; everything else calculates for you.", f["note"])

    # ---- Settings ----------------------------------------------------
    st = sheets["Settings"]
    st.hide_gridlines(2); st.set_column("A:A", 2); st.set_column("B:B", 24); st.set_column("C:C", 18); st.set_column("E:G", 24)
    st.write("B2", "Settings", f["title"])
    st.write("B4", "Month", f["label"]); st.write("C4", "January", f["input_u"])
    st.data_validation("C4", {"validate": "list", "source": MONTHS})
    st.write("B5", "Year", f["label"]); st.write("C5", 2026, f["input_u"])
    st.write("B6", "Month number", f["label"])
    st.write_formula("C6", '=MATCH(C4,{"January","February","March","April","May","June","July","August","September","October","November","December"},0)', f["calc"], 1)
    st.write("B7", "Month start", f["label"]); st.write_formula("C7", "=DATE(C5,C6,1)", f["date"])
    st.write("B8", "Month end", f["label"]); st.write_formula("C8", "=EOMONTH(C7,0)", f["date"])
    st.write("E3", "Expense categories (edit freely)", f["label"])
    for i in range(30):
        st.write(3 + i, 4, categories[i] if i < len(categories) else "", f["input_u"])
    st.write("F3", "Group", f["label"])
    cat_group = {cat: g_.name for g_ in c.expense_groups for cat in g_.categories}
    for i in range(30):
        st.write(3 + i, 5, cat_group.get(categories[i], "") if i < len(categories) else "", f["input_u"])
    st.write("G3", "Income sources", f["label"])
    for i in range(10):
        st.write(3 + i, 6, c.income[i] if i < len(c.income) else "", f["input_u"])
    CAT_RANGE = "Settings!$E$4:$E$33"

    # ---- Transactions -------------------------------------------------
    tx = sheets["Transactions"]
    tx.hide_gridlines(2); tx.freeze_panes(4, 0)
    tx.set_column("A:A", 13); tx.set_column("B:B", 34); tx.set_column("C:C", 22); tx.set_column("D:D", 14); tx.set_column("E:E", 12)
    tx.write("A1", "Transactions", f["title"]); tx.set_row(0, 34)
    tx.write("A2", "Log every income and expense. Type = Expense or Income.", f["note"])
    for col, h in enumerate(["Date", "Description", "Category", "Amount", "Type"]):
        tx.write(3, col, h, f["th_c"] if col in (0, 3, 4) else f["th"])
    N = 1000
    for r in range(4, 4 + N):
        tx.write_blank(r, 0, None, f["date_u"]); tx.write_blank(r, 1, None, f["text_u"])
        tx.write_blank(r, 2, None, f["text_u"]); tx.write_blank(r, 3, None, f["money_u"]); tx.write_blank(r, 4, None, f["cell_u"])
    tx.data_validation(4, 2, 3 + N, 2, {"validate": "list", "source": f"={CAT_RANGE}"})
    tx.data_validation(4, 4, 3 + N, 4, {"validate": "list", "source": ["Expense", "Income"]})
    tx.data_validation(4, 0, 3 + N, 0, {"validate": "date", "criteria": ">", "value": dt.date(1900, 1, 1)})
    # sample rows so the first open shows the workbook working
    samples = [
        (dt.date(2026, 1, 1), "Paycheck", c.income[0], 2800, "Income"),
        (dt.date(2026, 1, 2), "Rent", categories[0], 1100, "Expense"),
        (dt.date(2026, 1, 4), "Groceries", categories[4] if len(categories) > 4 else categories[0], 86.40, "Expense"),
        (dt.date(2026, 1, 9), "Coffee", categories[6] if len(categories) > 6 else categories[0], 4.75, "Expense"),
    ]
    for i, (d, desc, cat, amt, typ) in enumerate(samples):
        r = 4 + i
        tx.write_datetime(r, 0, dt.datetime.combine(d, dt.time()), f["date_u"]); tx.write(r, 1, desc + " (sample - delete me)", f["text_u"])
        tx.write(r, 2, cat, f["text_u"]); tx.write(r, 3, amt, f["money_u"]); tx.write(r, 4, typ, f["cell_u"])
    TD, TC, TA, TT = f"Transactions!$A$5:$A${4 + N}", f"Transactions!$C$5:$C${4 + N}", f"Transactions!$D$5:$D${4 + N}", f"Transactions!$E$5:$E${4 + N}"

    # ---- Budget -------------------------------------------------------
    bu = sheets["Budget"]
    bu.hide_gridlines(2); bu.set_column("A:A", 2); bu.set_column("B:B", 30); bu.set_column("C:E", 15); bu.set_column("F:F", 24)
    bu.write("B2", "Budget", f["title"]); bu.set_row(1, 34)
    bu.write_formula("B3", '=Settings!C4&" "&Settings!C5', f["tagline"], "January 2026")
    for col, h in enumerate(["Category", "Planned", "Actual", "Difference"]):
        bu.write(4, 1 + col, h, f["th_c"] if col else f["th"])
    row = 5
    first_cat_row = row
    for grp in c.expense_groups:
        bu.merge_range(row, 1, row, 4, grp.name, f["group"]); row += 1
        for cat in grp.categories:
            bu.write(row, 1, cat, f["text"])
            bu.write(row, 2, None, f["money_in_u"])
            bu.write_formula(row, 3, f'=SUMIFS({TA},{TC},B{row + 1},{TT},"Expense",{TD},">="&Settings!$C$7,{TD},"<="&Settings!$C$8)', f["money"], 0)
            bu.write_formula(row, 4, f'=IF(C{row + 1}="","",C{row + 1}-D{row + 1})', f["money"], "")
            row += 1
    last_cat_row = row - 1
    bu.write(row, 1, "Total expenses", f["text_b"])
    bu.write_formula(row, 2, f"=SUM(C{first_cat_row + 1}:C{last_cat_row + 1})", f["money_b"], 0)
    bu.write_formula(row, 3, f"=SUM(D{first_cat_row + 1}:D{last_cat_row + 1})", f["money_b"], 0)
    bu.write_formula(row, 4, f"=C{row + 1}-D{row + 1}", f["money_b"], 0)
    total_row = row
    bu.conditional_format(first_cat_row, 4, total_row, 4, {"type": "cell", "criteria": "<", "value": 0, "format": f["red"]})
    bu.conditional_format(first_cat_row, 4, total_row, 4, {"type": "cell", "criteria": ">=", "value": 0, "format": f["green"]})
    bu.write(row + 2, 1, "Income this month", f["text_b"])
    bu.write_formula(row + 2, 3, f'=SUMIFS({TA},{TT},"Income",{TD},">="&Settings!$C$7,{TD},"<="&Settings!$C$8)', f["money_b"], 0)
    bu.write(row + 3, 1, "Left to save / spend", f["text_b"])
    bu.write_formula(row + 3, 3, f"=D{row + 3}-D{total_row + 1}", f["money_b"], 0)
    income_cell, spent_cell, left_cell = f"Budget!$D${row + 3}", f"Budget!$D${total_row + 1}", f"Budget!$D${row + 4}"

    # ---- Savings ------------------------------------------------------
    sv = sheets["Savings"]
    sv.hide_gridlines(2); sv.set_column("A:A", 2); sv.set_column("B:B", 28); sv.set_column("C:E", 15); sv.set_column("F:F", 18)
    sv.write("B2", "Savings goals", f["title"]); sv.set_row(1, 34)
    for col, h in enumerate(["Goal", "Target", "Saved so far", "Progress"]):
        sv.write(3, 1 + col, h, f["th_c"] if col else f["th"])
    for i in range(8):
        r = 4 + i
        sv.write(r, 1, c.savings_goals[i] if i < len(c.savings_goals) else "", f["text_u"])
        sv.write(r, 2, None, f["money_u"]); sv.write(r, 3, None, f["money_u"])
        sv.write_formula(r, 4, f'=IF(OR(C{r + 1}="",C{r + 1}=0),"",MIN(1,D{r + 1}/C{r + 1}))', f["pct"], "")
    sv.conditional_format(4, 4, 11, 4, {"type": "data_bar", "bar_color": pal.accent, "bar_solid": True, "min_type": "num", "min_value": 0, "max_type": "num", "max_value": 1})

    # ---- Debt payoff ---------------------------------------------------
    de = sheets["Debt Payoff"]
    de.hide_gridlines(2); de.set_column("A:A", 2); de.set_column("B:B", 26); de.set_column("C:G", 15)
    de.write("B2", "Debt payoff (snowball)", f["title"]); de.set_row(1, 34)
    de.write("B3", "List debts, smallest balance first. Pay minimums on all, put extra on the first.", f["note"])
    for col, h in enumerate(["Debt", "Balance", "APR %", "Min. payment", "Paid so far", "Remaining"]):
        de.write(4, 1 + col, h, f["th_c"] if col else f["th"])
    for i in range(10):
        r = 5 + i
        de.write(r, 1, None, f["text_u"]); de.write(r, 2, None, f["money_u"]); de.write(r, 3, None, f["text_u"])
        de.write(r, 4, None, f["money_u"]); de.write(r, 5, None, f["money_u"])
        de.write_formula(r, 6, f'=IF(C{r + 1}="","",MAX(0,C{r + 1}-F{r + 1}))', f["money"], "")
    de.write(16, 1, "Total remaining", f["text_b"])
    de.write_formula(16, 6, "=SUM(G6:G15)", f["money_b"], 0)

    # ---- Dashboard ------------------------------------------------------
    da = sheets["Dashboard"]
    da.hide_gridlines(2); da.set_column("A:A", 2); da.set_column("B:M", 13)
    da.write("B2", "Dashboard", f["title"]); da.set_row(1, 34)
    da.write_formula("B3", '=Settings!C4&" "&Settings!C5', f["tagline"], "January 2026")
    for i, (label, formula, fmt) in enumerate([
        ("INCOME", f"={income_cell}", "kpi"), ("SPENT", f"={spent_cell}", "kpi"), ("LEFT OVER", f"={left_cell}", "kpi"),
        ("SAVINGS RATE", f'=IF({income_cell}=0,0,MAX(0,{left_cell})/{income_cell})', "kpi_pct"),
    ]):
        col = 1 + i * 3
        da.merge_range(4, col, 4, col + 2, label, f["kpi_label"])
        da.merge_range(5, col, 6, col + 2, "", f[fmt])
        da.write_formula(5, col, formula, f[fmt], 0)
    # data for chart: spending by group
    da.write("O4", "Group", f["th"]); da.write("P4", "Spent", f["th_c"])
    for i, grp in enumerate(c.expense_groups):
        r_start = None
        da.write(4 + i, 14, grp.name, f["text"])
        crit = "+".join(
            f'SUMIFS({TA},{TC},"{cat}",{TT},"Expense",{TD},">="&Settings!$C$7,{TD},"<="&Settings!$C$8)'
            for cat in grp.categories
        )
        da.write_formula(4 + i, 15, "=" + crit, f["money"], 0)
    pie = wb.add_chart({"type": "doughnut"})
    pie.add_series({
        "name": "Spending by group",
        "categories": f"=Dashboard!$O$5:$O${4 + len(c.expense_groups)}",
        "values": f"=Dashboard!$P$5:$P${4 + len(c.expense_groups)}",
        "data_labels": {"percentage": True},
    })
    pie.set_title({"name": "Where the money went", "name_font": {"size": 12, "color": pal.ink}})
    pie.set_size({"width": 470, "height": 340})
    da.insert_chart("B9", pie)
    bar = wb.add_chart({"type": "column"})
    bar.add_series({"name": "Planned", "categories": "=Budget!$B$6:$B$%d" % (last_cat_row + 1), "values": "=Budget!$C$6:$C$%d" % (last_cat_row + 1), "fill": {"color": pal.line}})
    bar.add_series({"name": "Actual", "categories": "=Budget!$B$6:$B$%d" % (last_cat_row + 1), "values": "=Budget!$D$6:$D$%d" % (last_cat_row + 1), "fill": {"color": pal.accent}})
    bar.set_title({"name": "Planned vs actual", "name_font": {"size": 12, "color": pal.ink}})
    bar.set_size({"width": 560, "height": 340}); bar.set_legend({"position": "bottom"})
    da.insert_chart("H9", bar)

    on = ctx.options.get("protect_sheets", True)
    for name in ("Dashboard", "Settings", "Budget", "Savings", "Debt Payoff"):
        protect(sheets[name], on)
    sheets["Start Here"].activate()
    wb.close()
