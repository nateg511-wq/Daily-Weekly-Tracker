#!/usr/bin/env python3
"""
Level layer for the BTC TA stack: Support/Resistance + Trendlines.

Method:
  1. Swing detection - a bar that is the local high/low over +/- `order` bars.
  2. Support/Resistance - cluster recent swing points into horizontal levels,
     ranked by number of touches.
  3. Trendlines - least-squares fit through recent swing lows (support line)
     and swing highs (resistance line).

Input : data/btc_usd_daily_full.csv
Output: data/levels_{daily,weekly,monthly}.csv   (horizontal S/R)
        data/trendlines.csv                       (sloped lines, all timeframes)
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "data", "btc_usd_daily_full.csv")
OUT = os.path.join(HERE, "data")

# rule, swing order, lookback bars, cluster tolerance, trendline swing count
TF = {
    "weekly":    ("W-SUN", 4, 104, 0.030, 5),
    "monthly":   ("ME",    3, 36,  0.045, 4),
    "quarterly": ("QE",    2, 24,  0.060, 4),
}


def load_daily():
    df = pd.read_csv(SRC, parse_dates=["date"]).set_index("date").sort_index()
    for c in ["open", "high", "low", "close", "volume_btc"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def resample(df, rule):
    if rule is None:
        return df[["open", "high", "low", "close", "volume_btc"]].copy()
    agg = {"open": "first", "high": "max", "low": "min",
           "close": "last", "volume_btc": "sum"}
    return df.resample(rule).agg(agg).dropna(subset=["close"])


def swings(df, order):
    """Return per-bar arrays of confirmed swing-high / swing-low prices (NaN elsewhere)."""
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


def cluster(points, tol):
    """Greedy single-linkage clustering of (price, date) within `tol` fraction."""
    out = []
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


def trendline(pos, prices, last_pos):
    """Least-squares line through swing points -> (slope_per_bar, value_now)."""
    if len(pos) < 2:
        return None
    slope, intercept = np.polyfit(pos, prices, 1)
    return float(slope), float(slope * last_pos + intercept)


def build(name, df, order, lookback, tol, n_tl):
    price = df["close"].iloc[-1]
    sh, sl = swings(df, order)
    pos = np.arange(len(df))
    recent = pos >= max(0, len(df) - lookback)
    dates = df.index

    # ---- Horizontal S/R: cluster all recent swing points ----
    pts = [(sh[i], dates[i]) for i in pos[recent] if not np.isnan(sh[i])]
    pts += [(sl[i], dates[i]) for i in pos[recent] if not np.isnan(sl[i])]
    levels = cluster(pts, tol)
    rows = []
    for lv in levels:
        rows.append({
            "type": "resistance" if lv["level"] >= price else "support",
            "level": round(lv["level"], 2),
            "touches": lv["touches"],
            "first_touch": lv["first"].date(),
            "last_touch": lv["last"].date(),
            "dist_pct": round((lv["level"] - price) / price * 100, 2),
        })
    lv_df = pd.DataFrame(rows).sort_values("level")
    lv_df.to_csv(os.path.join(OUT, f"levels_{name}.csv"), index=False)

    # ---- Trendlines: fit through last N swing lows / highs ----
    tl = []
    for kind, arr in (("support", sl), ("resistance", sh)):
        idx = [i for i in pos[recent] if not np.isnan(arr[i])][-n_tl:]
        res = trendline(np.array(idx), np.array([arr[i] for i in idx]), len(df) - 1)
        if res:
            slope, now = res
            tl.append({"timeframe": name, "type": kind, "value_now": round(now, 2),
                       "slope_per_bar": round(slope, 2),
                       "direction": "rising" if slope > 0 else "falling",
                       "anchor_first": dates[idx[0]].date(),
                       "anchor_last": dates[idx[-1]].date(), "n_points": len(idx)})
    return price, lv_df, tl


def report(name, price, lv_df, tl):
    res = lv_df[lv_df["level"] > price].sort_values("level").head(3)
    sup = lv_df[lv_df["level"] <= price].sort_values("level", ascending=False).head(3)
    print(f"\n=== {name.upper()}  (price ${price:,.0f}) ===")
    print("  Resistance above:")
    for _, r in res.iterrows():
        print(f"    ${r['level']:>10,.0f}  ({r['touches']}x, last {r['last_touch']}, +{r['dist_pct']:.1f}%)")
    print("  Support below:")
    for _, r in sup.iterrows():
        print(f"    ${r['level']:>10,.0f}  ({r['touches']}x, last {r['last_touch']}, {r['dist_pct']:.1f}%)")
    for t in tl:
        print(f"  {t['type'].capitalize():10} trendline: ${t['value_now']:>10,.0f} now "
              f"({t['direction']}, {t['slope_per_bar']:+,.0f}/bar, from {t['anchor_first']})")


def main():
    daily = load_daily()
    all_tl = []
    for name, (rule, order, lookback, tol, n_tl) in TF.items():
        df = resample(daily, rule)
        price, lv_df, tl = build(name, df, order, lookback, tol, n_tl)
        all_tl.extend(tl)
        print(f"Wrote {len(lv_df):>3} {name:7} S/R levels -> data/levels_{name}.csv")
        report(name, price, lv_df, tl)
    pd.DataFrame(all_tl).to_csv(os.path.join(OUT, "trendlines.csv"), index=False)
    print(f"\nWrote {len(all_tl)} trendlines -> data/trendlines.csv")


if __name__ == "__main__":
    main()
