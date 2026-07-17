#!/usr/bin/env python3
"""
TA -> Pillar mapping: convert the quantitative BTC-TA stack into the CoinPicks
pillar standard (P 0-100, Quality 0-1, Impact 0-10, Signal = ((P-50)/50)*Q*I)
on the locked windows 1mo / 3mo / 6mo / 1yr / 3yr.

Method (statistician's notes)
  1. WINDOW SCORES S in [-100, +100], from three evidence layers:
       * Tape composites (score.py): weekly / monthly / quarterly 7-indicator
         conviction scores. Weekly bars speak to ~1mo, monthly to ~3mo,
         quarterly (+monthly) to ~6mo.
       * Cycle analogs: at today's cycle-month (months since the 2024 halving),
         the forward 1/3/6/12/36-mo returns at the SAME cycle-month in the three
         completed halving cycles. Score = 0.5*(2*hitrate-1)
         + 0.5*tanh(median_logret / (0.5*sqrt(h/12))) -- hit-rate and
         vol-scaled magnitude, equally weighted.
       * Power-law value: V = 100*tanh(ln(fair/price)), fair value from the
         log-log power-law fit over the full 2010+ series (R^2 ~ 0.96).
     Window blends (weights fixed by design, trend->short / structure->long):
       S(1mo)  = 0.7*C_weekly    + 0.3*A_1
       S(3mo)  = 0.6*C_monthly   + 0.4*A_3
       S(6mo)  = 0.35*C_quarterly + 0.35*C_monthly + 0.30*A_6
       S(1yr)  = 0.5*A_12 + 0.5*V
       S(3yr)  = 0.5*A_36 + 0.5*V
  2. P = 50 + 25*(S/100)  -- the HONESTY CAP: pure TA never claims odds more
     than 25 pts from a coin flip, because its demonstrated out-of-sample edge
     is modest (froth-signal AUC 0.58; the multi-signal crash model FAILED
     out-of-sample at 0.44 and was rejected).
  3. Quality: fixed rubric per window (data depth, indicator agreement,
     sample size of analogs, regime risk) -- printed with justification.
  4. Impact: 8/10 (AI draft). The tape aggregates all drivers but adds no
     external causal force of its own.
Froth (alt-season index) is NOT a score input -- its Coin Metrics data lags
~6 weeks -- it is reported as a robustness tilt only.

Reads : data/signals.json, data/btc_usd_daily_full.csv, data/altcoin_data.csv
Writes: data/pillar_scores.json
"""
import json
import math
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

HALVINGS = [pd.Timestamp(d) for d in ["2012-11-28", "2016-07-09", "2020-05-11", "2024-04-19"]]
WINDOWS = [1, 3, 6, 12, 36]
LBL = {1: "1mo", 3: "3mo", 6: "6mo", 12: "1yr", 36: "3yr"}
IMPACT = 8

QUALITY = {
    1:  (0.75, "835 weekly bars, 7/7 indicator agreement; edge modest by design"),
    3:  (0.70, "193 monthly bars, 6/7 agreement; analog sample thin (n=3) but unanimous"),
    6:  (0.55, "quarterly layer weakest (65 bars, 1/7 agreement); inputs disagree in sign"),
    12: (0.60, "analogs 3/3 positive + power-law R^2 0.96 converge; n=3 is thin"),
    36: (0.50, "n=3 and both long analogs carry regime-unique tailwinds; halving effect may be attenuating"),
}


def analog_scores(close):
    today = close.index[-1]
    cm = (today - HALVINGS[3]).days / 30.44
    out = {}
    for h in WINDOWS:
        rets = []
        for hv in HALVINGS[:3]:
            t0 = hv + pd.Timedelta(days=int(cm * 30.44))
            t1 = t0 + pd.Timedelta(days=int(h * 30.44))
            p0, p1 = close.asof(t0), close.asof(t1)
            if pd.notna(p0) and pd.notna(p1) and t1 <= close.index[-1]:
                rets.append(p1 / p0 - 1)
        hit = sum(1 for r in rets if r > 0) / len(rets)
        med = float(np.median(rets))
        scale = 0.5 * math.sqrt(h / 12)
        score = 100 * (0.5 * (2 * hit - 1) + 0.5 * math.tanh(math.log(1 + med) / scale))
        out[h] = dict(score=round(score, 1), hit=f"{sum(1 for r in rets if r > 0)}/{len(rets)}",
                      median_ret=round(med, 3), rets=[round(r, 3) for r in rets])
    return cm, out


def powerlaw_value(close):
    g = pd.Timestamp("2009-01-03")
    days = np.log10([(d - g).days for d in close.index])
    lp = np.log10(close.values)
    b, a = np.polyfit(days, lp, 1)
    fit = a + b * days
    r2 = 1 - ((lp - fit) ** 2).sum() / ((lp - lp.mean()) ** 2).sum()
    fair = 10 ** fit[-1]
    gap = math.log(fair / close.iloc[-1])
    return fair, r2, 100 * math.tanh(gap)


def froth_tilt():
    df = pd.read_csv(f"{DATA}/altcoin_data.csv", parse_dates=["date"]).set_index("date").sort_index()
    def zroll(s, w=730):
        return (s - s.rolling(w, min_periods=200).mean()) / s.rolling(w, min_periods=200).std()
    altbtc = df["alt_mcap"] / df["btc_mcap"]
    froth = pd.concat([zroll(df["alt_share"]), zroll(df["eth_btc"]),
                       zroll(altbtc.pct_change(90))], axis=1).mean(axis=1)
    return float(froth.iloc[-1]), str(df.index[-1].date())


def main():
    sig = json.load(open(f"{DATA}/signals.json"))
    close = (pd.read_csv(f"{DATA}/btc_usd_daily_full.csv", parse_dates=["date"])
             .set_index("date")["close"].astype(float))
    cw, cmn, cq = (sig["weekly"]["composite"], sig["monthly"]["composite"],
                   sig["quarterly"]["composite"])
    cyc_month, A = analog_scores(close)
    fair, r2, V = powerlaw_value(close)
    fz, fdate = froth_tilt()

    S = {
        1:  0.7 * cw + 0.3 * A[1]["score"],
        3:  0.6 * cmn + 0.4 * A[3]["score"],
        6:  0.35 * cq + 0.35 * cmn + 0.30 * A[6]["score"],
        12: 0.5 * A[12]["score"] + 0.5 * V,
        36: 0.5 * A[36]["score"] + 0.5 * V,
    }

    rows = {}
    print(f"BTC ${close.iloc[-1]:,.0f} on {close.index[-1].date()} | cycle-month {cyc_month:.1f} "
          f"| power-law fair ${fair:,.0f} (R^2 {r2:.2f}) | froth z {fz:+.2f} (as of {fdate}, lagged)")
    print(f"Tape composites: weekly {cw:+.1f} / monthly {cmn:+.1f} / quarterly {cq:+.1f}\n")
    print(f"{'win':>4} | {'S':>6} | {'P':>3} | {'Q':>4} | {'I':>2} | {'Signal':>6} | quality basis")
    print("-" * 100)
    for h in WINDOWS:
        P = round(50 + 25 * S[h] / 100)
        Q, why = QUALITY[h]
        signal = (P - 50) / 50 * Q * IMPACT
        rows[LBL[h]] = dict(window_months=h, S=round(S[h], 1), P=P, quality=Q,
                            impact=IMPACT, signal=round(signal, 2),
                            analog=A[h], quality_basis=why)
        print(f"{LBL[h]:>4} | {S[h]:+6.1f} | {P:>3} | {Q:.2f} | {IMPACT:>2} | {signal:+6.2f} | {why}")

    out = dict(asof=str(close.index[-1].date()), price=float(close.iloc[-1]),
               cycle_month=round(cyc_month, 1),
               tape=dict(weekly=cw, monthly=cmn, quarterly=cq),
               powerlaw=dict(fair=round(fair), r2=round(r2, 3), V=round(V, 1)),
               froth=dict(z=round(fz, 2), asof=fdate, note="robustness tilt only (lagged data)"),
               impact=IMPACT, windows=rows)
    with open(f"{DATA}/pillar_scores.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote data/pillar_scores.json")


if __name__ == "__main__":
    main()
