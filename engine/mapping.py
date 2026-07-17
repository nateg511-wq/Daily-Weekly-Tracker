"""TA -> Pillar mapping: convert the quant stack into the house pillar standard.

Window scores S in [-100, +100] from three evidence layers (weights in
settings.json quant.window_blend):
    tape composites (score.py)  — weekly ~1mo, monthly ~3mo, quarterly+monthly ~6mo
    cycle analogs (cycle.py)    — forward returns at today's cycle-month, n=3
    power-law value (cycle.py)  — V = 100*tanh(ln(fair/price))

Then the HONESTY CAP:  P = 50 + cap × (S / 100), cap = 25 by default —
pure TA never claims odds more than 25 points from a coin flip, because its
measured out-of-sample edge is modest (froth AUC ~0.58; a 5-feature crash
model failed LOCO testing at 0.44 and is permanently excluded).

Quality per window comes from settings.json (fixed rubric, documented basis).
Froth is reported but NOT a score input (its data lags ~6 weeks).

Reads : data/signals.json, data/cycle.json
Writes: data/pillar_scores.json   (the quant pillar the equal-weight blender consumes)
"""
from __future__ import annotations

import math

from .common import DATA, GRID, LBL, load_json, load_settings, log, save_json, signal


def run() -> dict:
    settings = load_settings()
    q = settings["quant"]
    impact = settings["impact"]
    sig = load_json(DATA / "signals.json")
    cyc = load_json(DATA / "cycle.json")

    tape = {"weekly": sig["weekly"]["composite"],
            "monthly": sig["monthly"]["composite"],
            "quarterly": sig["quarterly"]["composite"]}
    V = cyc["powerlaw"]["V"]

    windows = {}
    for h in GRID:
        wb = q["window_blend"][str(h)]
        S = 0.0
        for src, w in wb.items():
            if src == "analog":
                S += w * cyc["analogs"][str(h)]["score"]
            elif src == "powerlaw":
                S += w * V
            else:
                S += w * tape[src]
        # deterministic half-away-from-zero (built-in round() is half-to-even,
        # which would round a mildly-bullish x.5 boundary DOWN — asymmetric)
        x = 50 + q["honesty_cap"] * S / 100
        P = int(math.floor(x + 0.5)) if x >= 50 else int(math.ceil(x - 0.5))
        Q = q["quality"][str(h)]
        windows[LBL[h]] = dict(
            window_months=h, S=round(S, 1), P=P, quality=Q, impact=impact,
            signal=signal(P, Q, impact),      # FULL precision — display layers round
            analog=cyc["analogs"][str(h)], quality_basis=q["quality_basis"][str(h)],
        )

    out = dict(asof=cyc["asof"], price=cyc["price"], cycle_month=cyc["cycle_month"],
               tape=tape, powerlaw=cyc["powerlaw"], froth=cyc["froth"],
               impact=impact, honesty_cap=q["honesty_cap"], windows=windows)
    save_json(DATA / "pillar_scores.json", out)
    ps = " / ".join(str(windows[LBL[h]]["P"]) for h in GRID)
    log(f"mapping: quant draft P {ps}  (BTC ${cyc['price']:,.0f}, {cyc['asof']})")
    return out
