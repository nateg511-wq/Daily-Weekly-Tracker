#!/usr/bin/env python3
"""
HOW FAR DOWN — honest downside map for the current cycle, on REAL current price
(master/bitstamp to 2026-06-19). Two robust anchors instead of the overfit
multi-signal model: (a) power-law valuation bands (R^2~0.96), (b) historical
cycle troughs. Froth thesis tilts toward the shallow end.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
m = pd.read_csv(f"{HERE}/data/btc_usd_daily_full.csv", parse_dates=["date"]).set_index("date")["close"].astype(float)
cur, ath = m.iloc[-1], m.cummax().iloc[-1]
low_so_far = m[m.index >= "2025-10-06"].min()

# power-law fair value + bands (log10 price vs log10 days-since-genesis)
g = pd.Timestamp("2009-01-03")
days = np.log10([(d - g).days for d in m.index])
lp = np.log10(m.values)
b, a0 = np.polyfit(days, lp, 1)
fit = a0 + b * days
sd = (lp - fit).std()
r2 = 1 - ((lp - fit) ** 2).sum() / ((lp - lp.mean()) ** 2).sum()
fair = 10 ** fit[-1]
pl_1, pl_2 = 10 ** (fit[-1] - sd), 10 ** (fit[-1] - 2 * sd)

scen = {
    "Shallow — froth thesis holds": (low_so_far * 0.92, "we're near it; no alt bubble + already cheap"),
    "Deep value — power-law -2sd":  (pl_2, "classic-bear valuation floor"),
    "Historic bear -77%":           (ath * 0.23, "matches power-law deep band"),
    "Extreme -85% (worst ever)":    (ath * 0.15, "every prior trough was -77/-85%"),
}

print("=" * 66)
print("HOW FAR DOWN CAN THIS CYCLE GO?")
print("=" * 66)
print(f"Now: ${cur:,.0f}  ({cur/ath-1:+.0%} from ATH ${ath:,.0f})  | cycle low so far ${low_so_far:,.0f}")
print(f"Power-law (R^2={r2:.2f}): fair ${fair:,.0f} | -1sd ${pl_1:,.0f} | -2sd ${pl_2:,.0f} "
      f"(price is {cur/fair-1:+.0%} vs fair, already below -1sd)\n")
for name, (lvl, note) in scen.items():
    print(f"  {name:30} ~${lvl:>8,.0f}  ({lvl/ath-1:+.0%} from ATH)   {note}")

# chart
fig, ax = plt.subplots(figsize=(13, 7))
r = m[m.index >= "2023-01-01"]
ax.semilogy(r.index, r, color="#111", lw=1.4)
ax.axhline(cur, color="#2563eb", ls="-", lw=1.6)
ax.text(r.index[2], cur, f" now ${cur:,.0f}", color="#2563eb", va="bottom", fontweight="bold", fontsize=9)
palette = ["#16a34a", "#7c3aed", "#f59e0b", "#dc2626"]
for (name, (lvl, note)), c in zip(scen.items(), palette):
    ax.axhline(lvl, color=c, ls="--", lw=1.4, alpha=0.9)
    ax.text(r.index[2], lvl, f" {name}: ${lvl:,.0f} ({lvl/ath-1:+.0%})", color=c, va="bottom", fontsize=8.3, fontweight="bold")
ax.axhspan(scen["Deep value — power-law -2sd"][0], scen["Shallow — froth thesis holds"][0],
           color="#fde68a", alpha=0.18)
ax.set_ylabel("BTC price (log)")
ax.set_title("How far down can this cycle go?  Valuation floor + cycle history\n"
             "(shaded = plausible-bottom zone; froth thesis leans toward the top of it)")
ax.grid(True, which="both", ls=":", alpha=0.4)
fig.tight_layout()
out = f"{HERE}/charts/downside_scenarios.png"
fig.savefig(out, dpi=150, bbox_inches="tight")
print(f"\nSaved chart -> {out}")
