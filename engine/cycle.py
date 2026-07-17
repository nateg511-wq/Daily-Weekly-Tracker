"""Halving-cycle analysis + cycle-analog forward returns + power-law valuation.

Three slow clocks feeding the long-window quant scores:
  * Cycle table: top/bottom/momentum-turn timing per completed cycle, with
    projections for the current cycle from the C1–C3 averages.
  * Analogs: standing at today's cycle-month in each completed cycle, the
    forward 1/3/6/12/36-month returns. n=3 — single windows CAN flip when
    alignment shifts a few days; direction is the signal, levels are soft.
    36-month windows cross into the NEXT cycle's rally by construction.
  * Power law: log10(price) ~ log10(days since genesis) over the full series.
    Fit-window honesty: fair value moves materially with the start year; the
    sensitivity range is computed and reported, not hidden. R² is inflated by
    construction for integrated series — treat the −1σ/−2σ bands as scenario
    bounds, not forecasts.

Writes data/cycle.json; the overlay chart lives in charts.py.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .common import DATA, load_settings, log, save_json


def load_close() -> pd.Series:
    s = (pd.read_csv(DATA / "btc_usd_daily_full.csv", parse_dates=["date"])
         .set_index("date")["close"])
    return pd.to_numeric(s, errors="coerce").dropna().sort_index()


def months(a: pd.Timestamp, b: pd.Timestamp) -> float:
    return (b - a).days / 30.44


def cycle_table(close: pd.Series, halvings: list[pd.Timestamp]) -> list[dict]:
    today = close.index[-1]
    mom = close / close.shift(365) - 1.0
    rows = []
    for i, h in enumerate(halvings):
        end = halvings[i + 1] if i + 1 < len(halvings) else today
        seg = close[(close.index >= h) & (close.index < end)]
        hp = close.asof(h)
        top_window = seg[seg.index <= h + pd.Timedelta(days=int(30 * 30.44))]
        top_date, top_p = top_window.idxmax(), top_window.max()
        after = seg[seg.index >= top_date]
        bot_date, bot_p = after.idxmin(), after.min()
        ms = mom[(mom.index >= h) & (mom.index < end)].dropna()
        trough = ms.idxmin() if len(ms) else None
        turn = None
        if trough is not None:
            pos = ms[(ms.index >= trough) & (ms > 0)]
            turn = pos.index[0] if len(pos) else None
        rows.append(dict(
            halving=str(h.date()), price_at_halving=float(hp),
            top_date=str(top_date.date()), top=float(top_p), m_top=round(months(h, top_date), 1),
            bottom_date=str(bot_date.date()), bottom=float(bot_p), m_bottom=round(months(h, bot_date), 1),
            drawdown=round(bot_p / top_p - 1, 3),
            turn_date=str(turn.date()) if turn is not None else None,
            m_turn=round(months(h, turn), 1) if turn is not None else None,
        ))
    return rows


def analogs(close: pd.Series, halvings: list[pd.Timestamp], grid: list[int]) -> tuple[float, dict]:
    today = close.index[-1]
    cm = months(halvings[-1], today)
    out = {}
    for h in grid:
        rets = []
        for hv in halvings[:3]:
            t0 = hv + pd.Timedelta(days=int(cm * 30.44))
            t1 = t0 + pd.Timedelta(days=int(h * 30.44))
            p0, p1 = close.asof(t0), close.asof(t1)
            if pd.notna(p0) and pd.notna(p1) and t1 <= close.index[-1]:
                rets.append(float(p1 / p0 - 1))
        hit = sum(1 for r in rets if r > 0) / len(rets)
        med = float(np.median(rets))
        scale = 0.5 * math.sqrt(h / 12)
        score = 100 * (0.5 * (2 * hit - 1) + 0.5 * math.tanh(math.log(1 + med) / scale))
        out[str(h)] = dict(score=round(score, 1), hit=f"{sum(1 for r in rets if r > 0)}/{len(rets)}",
                           median_ret=round(med, 3), rets=[round(r, 3) for r in rets])
    return round(cm, 2), out


def powerlaw(close: pd.Series, genesis: pd.Timestamp) -> dict:
    def fit(series: pd.Series) -> tuple[float, float, float]:
        days = np.log10([(d - genesis).days for d in series.index])
        lp = np.log10(series.values)
        b, a = np.polyfit(days, lp, 1)
        fitv = a + b * days
        r2 = 1 - ((lp - fitv) ** 2).sum() / ((lp - lp.mean()) ** 2).sum()
        sd = (lp - fitv).std()
        return 10 ** fitv[-1], r2, sd

    fair, r2, sd = fit(close)
    lf = math.log10(fair)
    sens = {}
    for start in ("2011", "2012", "2013", "2015"):
        f, _, _ = fit(close[close.index >= start])
        sens[start] = round(f)
    gap = math.log(fair / close.iloc[-1])
    return dict(fair=round(fair), r2=round(r2, 3),
                minus1sd=round(10 ** (lf - sd)), minus2sd=round(10 ** (lf - 2 * sd)),
                pct_vs_fair=round(close.iloc[-1] / fair - 1, 3),
                V=round(100 * math.tanh(gap), 1),
                fit_start_sensitivity=sens)


def froth(alt_csv) -> dict:
    df = pd.read_csv(alt_csv, parse_dates=["date"]).set_index("date").sort_index()

    def zroll(s, w=730):
        return (s - s.rolling(w, min_periods=200).mean()) / s.rolling(w, min_periods=200).std()

    altbtc = df["alt_mcap"] / df["btc_mcap"]
    z = pd.concat([zroll(df["alt_share"]), zroll(df["eth_btc"]),
                   zroll(altbtc.pct_change(90))], axis=1).mean(axis=1)
    return dict(z=round(float(z.iloc[-1]), 2), asof=str(df.index[-1].date()),
                note="robustness tilt only — Coin Metrics community data lags ~6 weeks")


def run() -> dict:
    s = load_settings()
    halvings = [pd.Timestamp(d) for d in s["data"]["halvings"]]
    genesis = pd.Timestamp(s["data"]["genesis"])
    close = load_close()

    table = cycle_table(close, halvings)
    cm, an = analogs(close, halvings, [1, 3, 6, 12, 36])
    pl = powerlaw(close, genesis)
    fr = froth(DATA / "altcoin_data.csv")

    done = table[:3]
    proj = {k: round(sum(r[k] for r in done) / 3, 1) for k in ("m_top", "m_bottom", "m_turn")}
    out = dict(asof=str(close.index[-1].date()), price=float(close.iloc[-1]),
               cycle_month=cm, cycles=table, projections_from_C1_C3=proj,
               analogs=an, powerlaw=pl, froth=fr)
    save_json(DATA / "cycle.json", out)
    log(f"cycle: month {cm} | analogs 12mo {an['12']['hit']} median {an['12']['median_ret']:+.1%} | "
        f"power-law fair ${pl['fair']:,} ({pl['pct_vs_fair']:+.0%} vs fair) | froth z {fr['z']:+.2f} ({fr['asof']})")
    return out
