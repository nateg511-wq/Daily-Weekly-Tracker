"""Graded per-indicator scoring for the 7-indicator stack (weekly/monthly/quarterly).

Each indicator -> a CONVICTION SCORE in [-100, +100]:
    sign  = direction (positive bullish, negative bearish)
    |size| = conviction / intensity

Design (statistician's notes)
  * Bounded inputs (RSI, %B, range-position) map linearly to [-1, 1].
  * Unbounded / price-scaled inputs (MA distance, MACD, OBV drift) are
    normalized to scale-free quantities then squashed with tanh.
  * Composite = fixed weights from config (settings.json indicator_weights);
    'agreement' = indicators sharing the composite's sign at |score| >= 20.
  * MACD prose reports the histogram's SIGN as momentum polarity, not its
    derivative — "negative momentum" can be improving bar-over-bar.
  * Composites are also computed on COMPLETED bars only (dropping the live
    partial bar) so downstream reports can quantify partial-bar drift.

Reads : data/indicators_{tf}.csv, data/levels_{tf}.csv, data/trendlines.csv
Writes: data/signals.json
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .common import DATA, load_settings, log, save_json

CFG = {"weekly": dict(obv_lb=13, range_lb=104),
       "monthly": dict(obv_lb=6, range_lb=36),
       "quarterly": dict(obv_lb=4, range_lb=20)}


def clip(x: float, a: float = -1.0, b: float = 1.0) -> float:
    return max(a, min(b, x))


def money(x: float) -> str:
    return f"${x:,.0f}"


def band(score: float) -> str:
    a = abs(score)
    if a < 20:
        return "Neutral"
    if a < 45:
        return "Slight"
    if a < 70:
        return "Moderate"
    return "Strong"


def call(score: float) -> str:
    return "neutral" if abs(score) < 20 else ("bullish" if score > 0 else "bearish")


# ---------------- per-indicator scores: return (score in [-1,1], why) ----------------
def s_ma(ind: pd.DataFrame):
    r = ind.iloc[-1]
    p = r["close"]
    comps, parts = [], []
    for n in (20, 50, 200):
        v = r[f"sma{n}"]
        if pd.notna(v):
            pct = (p - v) / v
            comps.append(math.tanh(pct / 0.10))          # 10% gap ~ tanh(1) = 0.76
            parts.append((n, v, pct))
    base = sum(comps) / len(comps)
    cross = 0
    if pd.notna(r["sma50"]) and pd.notna(r["sma200"]):
        cross = 1 if r["sma50"] > r["sma200"] else -1
    s = clip(0.85 * base + 0.15 * cross)
    above = [f"SMA{n} ({money(v)}, {pct*100:+.0f}%)" for n, v, pct in parts if pct > 0]
    below = [f"SMA{n} ({money(v)}, {pct*100:+.0f}%)" for n, v, pct in parts if pct <= 0]
    cx = (" 50>200 (golden-cross structure)" if cross == 1
          else " 50<200 (death-cross structure)" if cross == -1 else "")
    why = (f"Price is {'above ' + ', '.join(above) if above else ''}"
           f"{'; ' if above and below else ''}"
           f"{'below ' + ', '.join(below) if below else ''}.{cx}")
    return s, why


def s_rsi(ind: pd.DataFrame):
    rsi = ind.iloc[-1]["rsi14"]
    s = clip((rsi - 50) / 30)
    dist = rsi - 50
    zone = (" — deep oversold, capitulation watch" if rsi < 30
            else " — overbought" if rsi > 70 else "")
    why = (f"RSI {rsi:.1f} sits {abs(dist):.0f} pts {'above' if dist >= 0 else 'below'} "
           f"the 50 midline{zone}. {'Weak' if dist < 0 else 'Firm'} momentum, "
           f"{'but not yet oversold (<30)' if 30 <= rsi < 45 else 'normal range' if 45 <= rsi <= 55 else 'stretched'}.")
    return s, why


def s_macd(ind: pd.DataFrame):
    r = ind.iloc[-1]
    m, h, p = r["macd"], r["macd_hist"], r["close"]
    regime = math.tanh((m / p) / 0.04)
    momo = math.tanh((h / p) / 0.02)
    s = clip(0.5 * regime + 0.5 * momo)
    why = (f"MACD line {'above' if m > 0 else 'below'} zero ({m:,.0f}) sets a "
           f"{'bullish' if m > 0 else 'bearish'} regime; histogram {h:+,.0f} shows "
           f"{'positive' if h > 0 else 'negative'} momentum (sign, not direction). "
           f"{'Regime and momentum aligned.' if (m > 0) == (h > 0) else 'Regime and momentum diverge (inflection).'}")
    return s, why


def s_obv(ind: pd.DataFrame, lb: int):
    obv = ind["obv"].iloc[-lb:]
    slope = np.polyfit(np.arange(len(obv)), obv.values, 1)[0]
    rng = obv.max() - obv.min()
    drift = slope * (len(obv) - 1)
    pos = (obv.iloc[-1] - obv.min()) / rng if rng > 0 else 0.5
    s = clip(drift / rng) if rng > 0 else 0.0
    word = "falling" if drift < 0 else "rising" if drift > 0 else "flat"
    flow = "distribution" if drift < 0 else "accumulation" if drift > 0 else "no net flow"
    why = (f"Over {lb} bars OBV has drifted {drift:+,.0f} "
           f"(~{drift/rng*100:+.0f}% of its range) and sits at {pos*100:.0f}% of range — "
           f"a {word} tape ({flow}). "
           f"{'Volume confirms the decline.' if s < -0.2 else 'Volume confirms the advance.' if s > 0.2 else 'No decisive net flow.'}")
    return s, why


def s_bb(ind: pd.DataFrame):
    r = ind.iloc[-1]
    b, w = r["bb_pctb"], r["bb_width"]
    s = clip((b - 0.5) / 0.5)
    loc = ("riding/under the lower band" if b < 0.1 else "in the lower half"
           if b < 0.5 else "riding/over the upper band" if b > 0.9 else "in the upper half")
    vol = "expanded/high-volatility" if w > 0.25 else "tight/compressed"
    why = (f"%B {b:.2f}: price is {loc}; band width {w*100:.0f}% of price "
           f"({vol}). {'Pinned to the downside.' if b < 0.2 else 'Pushing the upside.' if b > 0.8 else 'Mid-band, indecisive.'}")
    return s, why


def s_sr(ind: pd.DataFrame, lv: pd.DataFrame, lb: int):
    p = ind.iloc[-1]["close"]
    win = ind.iloc[-lb:]
    hi, lo = win["high"].max(), win["low"].min()
    pos = (p - lo) / (hi - lo) if hi > lo else 0.5
    s = clip((pos - 0.5) / 0.5)
    res = lv[lv["level"] > p].sort_values("level")
    sup = lv[lv["level"] <= p].sort_values("level", ascending=False)
    nr = res.iloc[0] if len(res) else None
    ns = sup.iloc[0] if len(sup) else None
    rtxt = (f"resistance {money(nr['level'])} (+{nr['dist_pct']:.1f}%, {int(nr['touches'])}x)"
            if nr is not None else "no resistance mapped")
    stxt = (f"support {money(ns['level'])} ({ns['dist_pct']:.1f}%, {int(ns['touches'])}x)"
            if ns is not None else "no support mapped")
    why = (f"Price is {pos*100:.0f}% up its {lb}-bar range ({money(lo)}-{money(hi)}) — "
           f"{'deep in the lower portion' if pos < 0.33 else 'mid-range' if pos < 0.66 else 'upper portion'}. "
           f"Nearest {rtxt}; nearest {stxt}.")
    return s, why


def s_trend(ind: pd.DataFrame, tl: pd.DataFrame):
    p = ind.iloc[-1]["close"]
    sup = tl[tl["type"] == "support"]
    res = tl[tl["type"] == "resistance"]
    if not len(sup):
        return 0.0, "No support trendline available."
    sline = sup.iloc[0]
    sv, sd = sline["value_now"], sline["direction"]
    gap = (p - sv) / p                                  # NOTE: % of price, per house convention
    sslope = 1 if sd == "rising" else -1
    s = clip(0.8 * math.tanh(gap / 0.06) + 0.2 * sslope)
    rtxt = ""
    if len(res):
        rr = res.iloc[0]
        rtxt = f" Overhead resistance line at {money(rr['value_now'])} ({rr['direction']})."
    state = "has broken BELOW" if p < sv else "is holding above"
    why = (f"Price {state} its {sd} support trendline ({money(sv)}, {gap*100:+.1f}% of price).{rtxt} "
           f"{'A break of support is bearish.' if p < sv else 'Trend support intact.'} "
           f"(Trendlines are least-squares fits — treat as lower-confidence.)")
    return s, why


INDICATORS = [
    ("Moving Averages", lambda i, lv, tl, c: s_ma(i)),
    ("RSI (14)",        lambda i, lv, tl, c: s_rsi(i)),
    ("MACD (12/26/9)",  lambda i, lv, tl, c: s_macd(i)),
    ("Volume / OBV",    lambda i, lv, tl, c: s_obv(i, c["obv_lb"])),
    ("Bollinger Bands", lambda i, lv, tl, c: s_bb(i)),
    ("Support/Resist",  lambda i, lv, tl, c: s_sr(i, lv, c["range_lb"])),
    ("Trendlines",      lambda i, lv, tl, c: s_trend(i, tl)),
]


def composite(ind: pd.DataFrame, lv: pd.DataFrame, tl: pd.DataFrame,
              cfg: dict, weights: dict) -> tuple[float, list[dict]]:
    rows, comp = [], 0.0
    for name, fn in INDICATORS:
        raw, why = fn(ind, lv, tl, cfg)
        score = round(raw * 100, 1)
        comp += weights[name] * score
        rows.append({"indicator": name, "score": score, "call": call(score),
                     "intensity": band(score), "why": why})
    return round(comp, 1), rows


def analyse(tf: str, weights: dict) -> dict:
    cfg = CFG[tf]
    ind = pd.read_csv(DATA / f"indicators_{tf}.csv", parse_dates=["date"]).set_index("date")
    lv = pd.read_csv(DATA / f"levels_{tf}.csv")
    tl = pd.read_csv(DATA / "trendlines.csv")
    tl = tl[tl["timeframe"] == tf]

    comp, rows = composite(ind, lv, tl, cfg, weights)
    # Completed-bars composite: drop the live partial bar AND re-evaluate the
    # trendline value one bar back (value_now is quoted at the live bar's x).
    tl_shift = tl.copy()
    if len(tl_shift):
        tl_shift["value_now"] = tl_shift["value_now"] - tl_shift["slope_per_bar"]
    comp_complete, _ = composite(ind.iloc[:-1], lv, tl_shift, cfg, weights)
    agree = sum(1 for r in rows if (r["score"] > 0) == (comp > 0) and abs(r["score"]) >= 20)
    return {"date": str(ind.index[-1].date()), "close": float(ind.iloc[-1]["close"]),
            "composite": comp, "composite_completed_bars": comp_complete,
            "overall": call(comp), "overall_intensity": band(comp),
            "agreement": agree, "indicators": rows}


def run() -> dict:
    weights = load_settings()["indicator_weights"]
    out = {tf: analyse(tf, weights) for tf in ("quarterly", "monthly", "weekly")}
    save_json(DATA / "signals.json", out)
    for tf in ("weekly", "monthly", "quarterly"):
        r = out[tf]
        log(f"score: {tf:9} {r['composite']:+6.1f}/100 ({r['overall_intensity']} {r['overall']}, "
            f"agreement {r['agreement']}/7; completed-bars {r['composite_completed_bars']:+.1f})")
    return out
