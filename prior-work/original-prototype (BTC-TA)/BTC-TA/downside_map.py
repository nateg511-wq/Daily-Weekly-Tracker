#!/usr/bin/env python3
"""
Consolidated BTC downside map (6-method panel synthesis) on real price data.
Most-likely bottom zone, base/bear/tail cases, key levels, the 200-week MA floor.
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
ma200w = m.rolling(1400).mean()

# synthesized levels (from the 6-method panel; updated Jul 8 2026 after the
# June 30 / July 1 flush: old $60,859 trigger broke, intraday low $57,735
# tagged the golden pocket, close low $58,526, then a bounce to ~$62k)
ZONE = (54000, 60900)
NOW, TRIGGER, BASE, BEAR, TAIL = cur, 58526, 57000, 50000, 38000

fig, ax = plt.subplots(figsize=(13, 7.5))
r = m[m.index >= "2024-06-01"]
ax.plot(r.index, r, color="#111", lw=1.5, label="BTC")
ax.plot(ma200w[ma200w.index >= "2024-06-01"].index, ma200w[ma200w.index >= "2024-06-01"],
        color="#7c3aed", lw=1.5, ls="-", alpha=0.8, label="200-week MA (rising floor)")
ax.axhspan(*ZONE, color="#86efac", alpha=0.30, label="most-likely bottom zone \\$54k–\\$61k")

lines = [(NOW, "#2563eb", "-", f"now  ${NOW:,.0f}  ({NOW/ath-1:+.0%})", "bottom"),
         (TRIGGER, "#0891b2", ":", "Jun 30 cycle-low close \\$58,526 — THE trigger level (intraday \\$57,735)", "top"),
         (BASE, "#16a34a", "-", f"BASE  ${BASE:,.0f}  (−54%)  ·  5-method cluster + Fib golden pocket", "top"),
         (BEAR, "#f59e0b", "--", f"BEAR  ${BEAR:,.0f}  (−60%)  ·  needs a macro shock", "bottom"),
         (TAIL, "#dc2626", "--", f"TAIL  ${TAIL:,.0f}  (−70%)  ·  only on an exogenous catastrophe", "bottom")]
for lvl, c, ls, lab, va in lines:
    ax.axhline(lvl, color=c, ls=ls, lw=1.8 if ls == "-" else 1.4, alpha=0.95)
    ax.text(r.index[1], lvl, "  " + lab, color=c, va=va, fontsize=8.6, fontweight="bold")

ax.set_ylim(30000, 132000)
ax.set_ylabel("BTC price (USD)")
ax.set_title(f"BTC downside map — how far can this cycle go?   (ATH \\${ath:,.0f} → now \\${cur:,.0f})\n"
             "6 independent methods; 5 converge on \\$54k–\\$57k.  Jun 30 flush hit the zone (\\$58,526 close / \\$57,735 intraday) and bounced.  Watch \\$58,526.")
ax.grid(True, ls=":", alpha=0.4)
ax.legend(loc="upper right", fontsize=8.5)
box = ("Odds of where the bottom forms (updated Jul 8 after the Jun 30 flush):\n"
       "~40%  Jun 30/Jul 1 was it — $57.7–58.5k holds on any retest\n"
       "~35%  one more flush into the $54–58k base\n"
       "~17%  deeper bear $47–53k (macro shock)\n"
       " ~8%  tail $33–42k (needs a catastrophe)\n"
       "skeptic: weight sub-$45k at 15–20%")
ax.text(0.012, 0.035, box, transform=ax.transAxes, fontsize=8, va="bottom", family="monospace",
        bbox=dict(boxstyle="round,pad=0.4", fc="#f8fafc", ec="#94a3b8", alpha=0.95))
fig.tight_layout()
out = f"{HERE}/charts/downside_map.png"
fig.savefig(out, dpi=150, bbox_inches="tight")
print(f"now ${cur:,.0f} | 200wMA ${ma200w.iloc[-1]:,.0f} | zone ${ZONE[0]:,}-${ZONE[1]:,} | base ${BASE:,} | bear ${BEAR:,} | tail ${TAIL:,}")
print(f"Saved -> {out}")
