"""Final-number history: scan reports/archive/<date>/master_blend.json
snapshots into a time series, so the daily cadence can be tracked over time.

Each `run.py archive` call snapshots that day's master_blend.json — this
module just walks those snapshots (one row per date; if a date has an
archive-2, -3, ... suffix, the latest one for that date wins) and writes:

Output: data/final_number_history.csv, charts/final_number_history.png
"""
from __future__ import annotations

import csv
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from .common import CHARTS, DATA, GRID, LBL, REPORTS, load_json, log  # noqa: E402

ARCHIVE = REPORTS / "archive"
CSV_OUT = DATA / "final_number_history.csv"
CHART_OUT = CHARTS / "final_number_history.png"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def collect() -> list[dict]:
    rows: dict[str, dict] = {}  # date -> row; later archive dirs for the same date win
    for d in sorted(ARCHIVE.iterdir()):
        if not d.is_dir() or not DATE_RE.match(d.name):
            continue
        mb_path = d / "master_blend.json"
        if not mb_path.exists():
            continue
        mb = load_json(mb_path)
        date = mb.get("asof", d.name[:10])
        row = {
            "date": date,
            "price": mb.get("price"),
            "score_set": mb.get("score_set"),
            "final_equal": mb["final_number"]["equal"]["value"],
            "final_equal_call": mb["final_number"]["equal"]["call"],
            "final_horizon": mb["final_number"]["horizon"]["value"],
            "final_horizon_call": mb["final_number"]["horizon"]["call"],
        }
        for h in GRID:
            row[f"master_{LBL[h]}"] = mb["windows"][LBL[h]]["master"]
        rows[date] = row  # overwritten by later-sorted dirs (archive-2 etc.) for the same date
    return [rows[d] for d in sorted(rows)]


def write_csv(rows: list[dict]) -> None:
    if not rows:
        log("history: no archived snapshots found — nothing to write")
        return
    cols = list(rows[0].keys())
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    log(f"history: {len(rows)} snapshots -> {CSV_OUT.name}")


def chart(rows: list[dict]) -> None:
    if len(rows) < 1:
        return
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axhline(0, color="#94a3b8", lw=1, ls="-", zorder=1)
    for lvl, c in ((0.5, "#e2e8f0"), (1.5, "#e2e8f0"), (3.0, "#e2e8f0")):
        ax.axhline(lvl, color=c, lw=0.8, ls=":", zorder=0)
        ax.axhline(-lvl, color=c, lw=0.8, ls=":", zorder=0)

    marker = "o" if len(df) < 30 else None
    ax.plot(df["date"], df["final_equal"], color="#2563eb", lw=2, marker=marker,
             label="Final Number (equal-weight)")
    ax.plot(df["date"], df["final_horizon"], color="#16a34a", lw=1.6, marker=marker,
             ls="--", alpha=0.85, label="Final Number (horizon-weighted)")

    for _, r in df.iterrows():
        ax.annotate(f"{r['final_equal']:+.2f}", (r["date"], r["final_equal"]),
                     textcoords="offset points", xytext=(0, 8), fontsize=7.5,
                     ha="center", color="#1e40af")

    ax.set_ylabel("Final Number (−10 max bear … +10 max bull)")
    ax.set_title("CoinPicks Market Direction — Final Number Over Time")
    ax.grid(True, axis="x", ls=":", alpha=0.35)
    ax.legend(loc="best", fontsize=9)
    fig.autofmt_xdate()
    fig.tight_layout()
    CHARTS.mkdir(exist_ok=True)
    fig.savefig(CHART_OUT, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log(f"history: chart -> {CHART_OUT.name}")


def run() -> list[dict]:
    rows = collect()
    write_csv(rows)
    chart(rows)
    return rows


if __name__ == "__main__":
    for r in run():
        print(r)
