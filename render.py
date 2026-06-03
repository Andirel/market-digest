"""Render the daily page from ratings + perspectives into static HTML."""
import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html"]),
)


def build_page(out_path: Path, ratings, perspectives):
    covered = [r for r in ratings if r["mean"] is not None]
    tmpl = env.get_template("index.html.j2")
    html = tmpl.render(
        date=datetime.date.today().isoformat(),
        ratings=ratings,
        perspectives=perspectives,
        stats={
            "total": len(ratings),
            "covered": len(covered),
            "strong_buy": sum(1 for r in covered if r["mean"] <= 1.5),
            "buy": sum(1 for r in covered if 1.5 < r["mean"] <= 2.5),
        },
    )
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path} ({len(ratings)} rows)")
