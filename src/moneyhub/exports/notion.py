"""Notion import pack: a zip of Markdown pages and CSV databases, which Notion imports as pages and databases.
CSV import creates plain columns (text/number). Notion cannot import formulas, relations or views, so the guide tells the
buyer which columns to switch to Checkbox/Date/Select after importing."""
from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path

from . import Loaded, out_dir

SUPPORTED = ("weekly_planner", "daily_planner", "habit_tracker", "guided_journal", "checklist_pack", "worksheet_pack",
             "ebook_guide", "card_deck", "budget_tracker")


def _csv(header: list[str], rows: list[list[str]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def _safe(name: str) -> str:
    return re.sub(r"[^\w\- ]+", "", name).strip()[:60] or "Page"


def _todo(items: list[str]) -> str:
    return "\n".join(f"- [ ] {i}" for i in items)


def _start(c: dict, extra: str = "") -> str:
    how = "\n".join(f"{n}. {s}" for n, s in enumerate(c.get("how_to", []), 1))
    return (f"# {c['title']}\n\n*{c.get('tagline', '')}*\n\n" + (c.get("welcome", "") + "\n\n" if c.get("welcome") else "")
            + ("## How to use this\n\n" + how + "\n\n" if how else "") + extra)


def build_pages(ptype: str, c: dict) -> dict[str, str]:
    """File name -> text for the zip (Markdown pages and CSV databases)."""
    f: dict[str, str] = {}
    if ptype == "weekly_planner":
        f["Start Here.md"] = _start(c, "## What is inside\n\n- **Big Picture** page for the year\n- **Months** database\n- **Weeks** database, one row per week\n")
        f["Big Picture.md"] = "# Big picture\n\n" + "\n\n".join(f"## {p}\n\n- \n- \n- " for p in c["yearly_prompts"])
        boxes = c["weekly_boxes"]
        f["Weeks.csv"] = _csv(["Week", "Week of", "Focus", *boxes, "Done (Yes/No)"], [[f"Week {w}", "", "", *[""] * len(boxes), ""] for w in range(1, c.get("weeks", 52) + 1)])
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        f["Months.csv"] = _csv(["Month", *c["monthly_prompts"]], [[m, *[""] * len(c["monthly_prompts"])] for m in months])
    elif ptype == "daily_planner":
        labels = c["daily_labels"]
        f["Start Here.md"] = _start(c, "Each row of **Days** is one day. Add a Date column of type Date if you like.\n")
        f["Days.csv"] = _csv(["Day", "Date", c["priorities_label"], c["todo_label"], *c["boxes"], *labels],
                             [[f"Day {d}", "", "", "", *[""] * len(c["boxes"]), *["No"] * len(labels)] for d in range(1, c.get("days", 60) + 1)])
    elif ptype == "habit_tracker":
        habits = c["habits"]
        f["Start Here.md"] = _start({**c, "how_to": c.get("tips", [])}, "After importing, change the habit columns of **Daily Check-in** to type **Checkbox**.\n")
        f["Daily Check-in.csv"] = _csv(["Date", *habits], [[f"Day {d}", *["No"] * len(habits)] for d in range(1, 32)])
        f["Habits.csv"] = _csv(["Habit", "Why it matters", "Best streak"], [[h, "", ""] for h in habits])
    elif ptype == "guided_journal":
        f["Start Here.md"] = _start(c, "Open **Journal Index** to see all days. Each day has its own page in the **Days** folder.\n")
        f["Journal Index.csv"] = _csv(["Day", "Theme", "Prompt", "Done"], [[f"Day {i}", d["theme"], d["prompt"], "No"] for i, d in enumerate(c["days"], 1)])
        for i, d in enumerate(c["days"], 1):
            f[f"Days/Day {i:02d} - {_safe(d['theme'])}.md"] = (f"# Day {i}: {d['theme']}\n\n**{d['prompt']}**\n\n" + (f"*{d['nudge']}*\n\n" if d.get("nudge") else "")
                                                               + "## My thoughts\n\n\n\n## Today I am grateful for\n\n- \n- \n- \n\n## One small step for tomorrow\n\n- [ ] \n")
        f["Affirmations.md"] = "# Affirmations\n\n" + "\n".join(f"- {a}" for a in c["affirmations"])
    elif ptype == "checklist_pack":
        f["Start Here.md"] = _start({**c, "how_to": []}, "## Checklists\n\n" + "\n".join(f"- {cl['title']}" for cl in c["checklists"]) + "\n")
        for cl in c["checklists"]:
            body = "\n\n".join(f"## {g['name']}\n\n{_todo(g['items'])}" for g in cl["groups"])
            f[f"Checklists/{_safe(cl['title'])}.md"] = f"# {cl['title']}\n\n{cl.get('intro', '')}\n\n{body}\n"
    elif ptype == "worksheet_pack":
        f["Start Here.md"] = _start({**c, "how_to": []}, f"Topic: {c['topic']}. Level: {c['level']}.\n")
        for n, sh in enumerate(c["sheets"], 1):
            qs = []
            for i, it in enumerate(sh["items"], 1):
                qs.append(f"{i}. {it['question']}" + ("".join(f"\n    - {ch}" for ch in it["choices"]) if it["choices"] else ""))
            f[f"Worksheets/{n:02d} {_safe(sh['title'])}.md"] = f"# {sh['title']}\n\n*{sh['instructions']}*\n\n" + "\n\n".join(qs) + "\n"
        f["Answer Key.md"] = "# Answer key\n\n" + "\n\n".join(f"## {sh['title']}\n\n" + "\n".join(f"{i}. {it['answer']}" for i, it in enumerate(sh["items"], 1)) for sh in c["sheets"])
    elif ptype == "ebook_guide":
        f["Start Here.md"] = _start({**c, "how_to": []}, (f"> {c['disclaimer']}\n\n" if c.get("disclaimer") else "") + c.get("intro", "") + "\n")
        for n, ch in enumerate(c["chapters"], 1):
            f[f"Chapters/{n:02d} {_safe(ch['title'])}.md"] = (f"# {ch['title']}\n\n{ch['intro']}\n\n" + "\n".join(f"- {t}" for t in ch["tips"])
                                                            + (f"\n\n> {ch['callout']}\n" if ch.get("callout") else "") + "\n\n## Action steps\n\n" + _todo(ch["action_steps"]) + "\n")
    elif ptype == "card_deck":
        f["Start Here.md"] = _start({**c, "how_to": []}, "Open **Cards** as a Gallery view for a card-deck feel.\n")
        f["Cards.csv"] = _csv(["Card", "Hint", "Category"], [[x["text"], x.get("hint", ""), x.get("category", "")] for x in c["cards"]])
    elif ptype == "budget_tracker":
        f["Start Here.md"] = _start({**c, "how_to": c.get("tips", [])}, "Notion cannot import spreadsheet formulas. Add a **Formula** column such as `prop(\"Budget\") - prop(\"Actual\")` to the Expenses database after importing.\n")
        f["Income.csv"] = _csv(["Source", "Expected", "Actual"], [[s, "", ""] for s in c["income"]])
        f["Expenses.csv"] = _csv(["Category", "Group", "Budget", "Actual"], [[cat, g["name"], "", ""] for g in c["expense_groups"] for cat in g["categories"]])
        f["Bills.csv"] = _csv(["Bill", "Due day", "Amount", "Paid"], [[b, "", "", "No"] for b in c["bills"]])
        f["Savings Goals.csv"] = _csv(["Goal", "Target", "Saved so far", "Target date"], [[g, "", "", ""] for g in c["savings_goals"]])
    else:
        raise ValueError(f"{ptype} has no Notion version. Supported: {', '.join(SUPPORTED)}")
    return f


GUIDE = """# Import this into Notion

1. In Notion, open the sidebar and choose **Import** (or Settings > Import).
2. Pick **Text & Markdown**, then choose the zip file ({zip}). Notion creates the pages and databases.
3. Open **Start Here** first.
4. Tidy up the databases: change columns to the type you want (Checkbox, Date, Select). Notion imports CSV columns as text or numbers.
5. Duplicate or move the finished workspace wherever you like.

## Selling a Notion product

Buyers usually receive a link to a duplicable Notion page, not a zip. Once your workspace looks right, use **Share > Publish** (allow
**Duplicate as template**) and put that link in a short PDF for your customers. Check Notion's current rules for selling templates.
"""


def export_notion(l: Loaded) -> Path:
    files = build_pages(l.ptype, l.content)
    d = out_dir(l, "exports")
    base = re.sub(r"[^a-z0-9]+", "-", l.title.lower()).strip("-")
    z = d / f"{base}-notion-import.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, text in files.items():
            zf.writestr(f"{_safe(l.title)}/{name}", text)
    guide = d / f"{base}-notion-guide.md"
    guide.write_text(GUIDE.format(zip=z.name), encoding="utf-8")
    with zipfile.ZipFile(d / f"{base}-notion-pack.zip", "w", zipfile.ZIP_DEFLATED) as zf:   # one download: the import zip plus the guide
        zf.write(z, z.name)
        zf.write(guide, guide.name)
    return z
