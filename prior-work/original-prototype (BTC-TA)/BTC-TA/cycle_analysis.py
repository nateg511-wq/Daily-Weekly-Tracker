#!/usr/bin/env python3
"""
Halving-cycle analysis: for each of BTC's 4 halvings, find the cycle top, the
cycle bottom, and when 1-year momentum troughed and turned back positive --
then project those cycle-months onto the current (2024) cycle to date the
likely momentum turn. Also renders a cycle-overlay chart.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
close = (pd.read_csv(f"{HERE}/data/btc_usd_daily_full.csv", parse_dates=["date"])
         .set_index("date")["close"].astype(float))
today = close.index[-1]

HALVINGS = [pd.Timestamp(d) for d in ["2012-11-28", "2016-07-09", "2020-05-11", "2024-04-19"]]
LABELS = ["C1 (2012)", "C2 (2016)", "C3 (2020)", "C4 (2024)"]
mom = close / close.shift(365) - 1.0          # trailing 1-year momentum (YoY)


def months(a, b):
    return (b - a).days / 30.44


rows = []
for i, h in enumerate(HALVINGS):
    end = HALVINGS[i + 1] if i + 1 < len(HALVINGS) else today
    seg = close[(close.index >= h) & (close.index < end)]
    hp = close.asof(h)
    # tops historically come 12-18 mo post-halving; cap the search at 30 mo so we
    # don't accidentally grab the NEXT cycle's pre-halving rally.
    top_window = seg[seg.index <= h + pd.Timedelta(days=int(30 * 30.44))]
    top_date, top_p = top_window.idxmax(), top_window.max()
    after = seg[seg.index >= top_date]
    bot_date, bot_p = after.idxmin(), after.min()
    ms = mom[(mom.index >= h) & (mom.index < end)].dropna()
    trough_date = ms.idxmin() if len(ms) else None
    turn = None
    if trough_date is not None:
        pos = ms[(ms.index >= trough_date) & (ms > 0)]
        turn = pos.index[0] if len(pos) else None
    rows.append(dict(label=LABELS[i], h=h, hp=hp, top_date=top_date, top_p=top_p,
                     m_top=months(h, top_date), bot_date=bot_date, bot_p=bot_p,
                     m_bot=months(h, bot_date), dd=bot_p / top_p - 1,
                     turn=turn, m_turn=months(h, turn) if turn is not None else None))

print(f"Today: {today.date()}   BTC ${close.iloc[-1]:,.0f}\n")
print(f"{'cycle':10} {'halving':>11} {'top':>11} {'mo→top':>7} {'bottom':>11} {'mo→bot':>7} {'drawdwn':>8} {'mom turn+':>11} {'mo→turn':>7}")
for r in rows:
    turn = r["turn"].date() if r["turn"] is not None else "—"
    mt = f"{r['m_turn']:.0f}" if r["m_turn"] is not None else "—"
    note = "  <-- current, still unfolding" if r["label"].startswith("C4") else ""
    print(f"{r['label']:10} {str(r['h'].date()):>11} {str(r['top_date'].date()):>11} "
          f"{r['m_top']:>7.0f} {str(r['bot_date'].date()):>11} {r['m_bot']:>7.0f} "
          f"{r['dd']*100:>7.0f}% {str(turn):>11} {mt:>7}{note}")

# Projection from the 3 completed cycles
done = rows[:3]
avg_top = sum(r["m_top"] for r in done) / 3
avg_bot = sum(r["m_bot"] for r in done) / 3
avg_turn = sum(r["m_turn"] for r in done) / 3
h4 = HALVINGS[3]
proj = lambda m: (h4 + pd.Timedelta(days=m * 30.44)).date()
cur = rows[3]
print(f"\nCurrent cycle: {months(h4, today):.0f} months past the 2024-04-19 halving.")
print(f"  Top so far : {cur['top_date'].date()} ${cur['top_p']:,.0f}  ({cur['m_top']:.0f} mo in)")
print(f"  Low so far : {cur['bot_date'].date()} ${cur['bot_p']:,.0f}  (drawdown {cur['dd']*100:.0f}% from top)")
print(f"\nProjection onto 2024 cycle (avg of C1-C3):")
print(f"  avg months→top  {avg_top:.0f}  -> {proj(avg_top)}")
print(f"  avg months→bottom {avg_bot:.0f} -> {proj(avg_bot)}")
print(f"  avg months→momentum-turn {avg_turn:.0f} -> {proj(avg_turn)}")
print(f"  (per-cycle momentum-turn months: {[round(r['m_turn']) for r in done]})")

# ---- overlay chart: price ÷ halving-price, log y, x = months since halving ----
fig, ax = plt.subplots(figsize=(13, 7))
colors = ["#9ca3af", "#60a5fa", "#f59e0b", "#dc2626"]
for i, (r, c) in enumerate(zip(rows, colors)):
    end = HALVINGS[i + 1] if i + 1 < len(HALVINGS) else today
    seg = close[(close.index >= r["h"]) & (close.index < end)]
    x = [(d - r["h"]).days / 30.44 for d in seg.index]
    y = seg.values / r["hp"]
    lw = 2.6 if i == 3 else 1.4
    ax.plot(x, y, color=c, lw=lw, label=r["label"], alpha=0.95 if i == 3 else 0.8)
    if r["m_turn"] is not None:
        ax.scatter([r["m_turn"]], [close.asof(r["turn"]) / r["hp"]], color=c, s=45, zorder=5,
                   marker="^", edgecolor="white", linewidth=0.6)
# --- vertical lines: where we are now + projected momentum turn (Bayesian, n=3) ---
cm = months(h4, today)
TURN_M, TURN_LO, TURN_HI = 35.88, 33.3, 39.0          # months post-halving; 80% interval
turn_date = pd.Timestamp("2027-04-16")
days_to = (turn_date - today).days
xtrans = ax.get_xaxis_transform()                      # x in data, y in axes-fraction
ax.axvspan(TURN_LO, TURN_HI, color="#16a34a", alpha=0.10, zorder=0)   # 80% window
ax.axvline(TURN_M, color="#16a34a", ls="--", lw=2.2, zorder=4,
           label=f"projected momentum turn · {turn_date.date()}")
ax.axvline(cm, color="#dc2626", ls=":", lw=1.7, alpha=0.85, zorder=4)
ax.scatter([cm], [close.iloc[-1] / rows[3]["hp"]], color="#dc2626", s=150, zorder=6,
           marker="o", edgecolor="black", linewidth=1.1, label=f"we are here · {today.date()}")
ax.text(cm, 0.02, " today", transform=xtrans, color="#dc2626", fontsize=8, ha="left", va="bottom")
ax.text(TURN_M, 0.02, " turn", transform=xtrans, color="#15803d", fontsize=8, ha="left", va="bottom")
ax.text(0.5, 0.97,
        f"≈ {days_to} days to projected momentum turn   "
        f"(point {turn_date.date()};  80% window Jan–Jul 2027)",
        transform=ax.transAxes, ha="center", va="top", fontsize=10.5, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.35", fc="#ecfdf5", ec="#16a34a", alpha=0.95))
ax.set_yscale("log")
ax.set_xlabel("months since halving")
ax.set_ylabel("price ÷ price at halving (log)")
ax.set_title("BTC halving cycles, aligned  (▲ = 1-yr momentum turned positive)")
ax.legend(loc="lower right", fontsize=8.5, framealpha=0.92)
ax.grid(True, which="both", ls=":", alpha=0.4)
ax.set_xlim(0, 50)
fig.tight_layout()
out = f"{HERE}/charts/halving_cycle.png"
fig.savefig(out, dpi=150, bbox_inches="tight")
print(f"\nSaved overlay chart -> {out}")
