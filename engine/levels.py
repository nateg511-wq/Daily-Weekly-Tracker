"""Support/Resistance and trendlines per timeframe.

Method:
  1. Swing detection — a bar that is the local high/low over ±`order` bars.
  2. Horizontal S/R — greedy single-linkage clustering of recent swing points
     within a fractional tolerance, ranked by touches.
  3. Trendlines — least-squares fit through the last N swing lows (support)
     and swing highs (resistance). Lower-confidence by nature; downstream
     scoring weights them at 0.10 and distances are quoted as % of price.

Input : data/btc_usd_daily_full.csv
Output: data/levels_{tf}.csv, data/trendlines.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .common import DATA, log
from .indicators import load_daily, resample

# rule, swing order, lookback bars, cluster tolerance, trendline swing count
TF = {
    "weekly":    ("W-SUN", 4, 104, 0.030, 5),
    "monthly":   ("ME",    3, 36,  0.045, 4),
    "quarterly": ("QE",    2, 24,  0.060, 4),
}


def swings(df: pd.DataFrame, order: int) -> tuple[np.ndarray, np.ndarray]:
    hi, lo = df["high"].values, df["low"].values
    n = len(df)
    sh, sl = np.full(n, np.nan), np.full(n, np.nan)
    for i in range(order, n - order):
        win_h, win_l = hi[i - order:i + order + 1], lo[i - order:i + order + 1]
        if hi[i] == win_h.max():
            sh[i] = hi[i]
        if lo[i] == win_l.min():
            sl[i] = lo[i]
    return sh, sl


def cluster(points: list, tol: float) -> list[dict]:
    out: list[dict] = []
    for price, date in sorted(points, key=lambda x: x[0]):
        if out and price <= out[-1]["ref"] * (1 + tol):
            cl = out[-1]
            cl["prices"].append(price)
            cl["dates"].append(date)
            cl["ref"] = float(np.mean(cl["prices"]))
        else:
            out.append({"prices": [price], "dates": [date], "ref": price})
    return [{"level": float(np.mean(c["prices"])), "touches": len(c["prices"]),
             "first": min(c["dates"]), "last": max(c["dates"])} for c in out]


def trendline(pos: np.ndarray, prices: np.ndarray, last_pos: int):
    if len(pos) < 2:
        return None
    slope, intercept = np.polyfit(pos, prices, 1)
    return float(slope), float(slope * last_pos + intercept)


def run() -> None:
    daily = load_daily()
    all_tl = []
    for name, (rule, order, lookback, tol, n_tl) in TF.items():
        df = resample(daily, rule)
        price = df["close"].iloc[-1]
        sh, sl = swings(df, order)
        pos = np.arange(len(df))
        recent = pos >= max(0, len(df) - lookback)
        dates = df.index

        pts = [(sh[i], dates[i]) for i in pos[recent] if not np.isnan(sh[i])]
        pts += [(sl[i], dates[i]) for i in pos[recent] if not np.isnan(sl[i])]
        rows = [{
            "type": "resistance" if lv["level"] >= price else "support",
            "level": round(lv["level"], 2),
            "touches": lv["touches"],
            "first_touch": lv["first"].date(),
            "last_touch": lv["last"].date(),
            "dist_pct": round((lv["level"] - price) / price * 100, 2),
        } for lv in cluster(pts, tol)]
        lv_df = pd.DataFrame(rows, columns=["type", "level", "touches", "first_touch", "last_touch", "dist_pct"])
        if len(lv_df):
            lv_df = lv_df.sort_values("level")
        lv_df.to_csv(DATA / f"levels_{name}.csv", index=False)

        for kind, arr in (("support", sl), ("resistance", sh)):
            idx = [i for i in pos[recent] if not np.isnan(arr[i])][-n_tl:]
            res = trendline(np.array(idx), np.array([arr[i] for i in idx]), len(df) - 1)
            if res:
                slope, now = res
                all_tl.append({"timeframe": name, "type": kind, "value_now": round(now, 2),
                               "slope_per_bar": round(slope, 2),
                               "direction": "rising" if slope > 0 else "falling",
                               "anchor_first": dates[idx[0]].date(),
                               "anchor_last": dates[idx[-1]].date(), "n_points": len(idx)})
        log(f"levels: {name} — {len(rows)} S/R levels (price ${price:,.0f})")
    pd.DataFrame(all_tl, columns=["timeframe", "type", "value_now", "slope_per_bar",
                                  "direction", "anchor_first", "anchor_last", "n_points"]
                 ).to_csv(DATA / "trendlines.csv", index=False)
    log(f"levels: {len(all_tl)} trendlines -> trendlines.csv")
