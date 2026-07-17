#!/usr/bin/env python3
"""
TEST: does altcoin froth tend to show up right BEFORE deeper BTC crashes?

Froth index F_t = mean of trailing-2yr z-scores of {alt market-cap share,
ETH/BTC ratio, 90d altcoin/BTC momentum}. All trailing -> no look-ahead.

Two tests:
  A) Episode level: detect swing-peak tops, measure the forward 365d drawdown
     from each, and rank-correlate pre-peak froth with crash depth.
  B) Higher power: for every day, forward 365d max drawdown vs froth quartile,
     with a block-bootstrap on the high-vs-low froth gap (handles overlap).
Caveats printed inline (maturation confound, exogenous shocks, dependence).
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(f"{HERE}/data/altcoin_data.csv", parse_dates=["date"]).set_index("date").sort_index()
px = df["btc_price"].astype(float)


def zroll(s, w=730):
    m = s.rolling(w, min_periods=200).mean()
    sd = s.rolling(w, min_periods=200).std()
    return (s - m) / sd


# ---- froth index (trailing, scale-free) ----
altbtc = df["alt_mcap"] / df["btc_mcap"]
froth = pd.concat([zroll(df["alt_share"]), zroll(df["eth_btc"]),
                   zroll(altbtc.pct_change(90))], axis=1).mean(axis=1)
froth = froth.reindex(px.index).interpolate(limit=5)
F = froth.dropna()

# ---- forward 365d max drawdown for every day ----
H = 365
fwd_dd = pd.Series(index=px.index, dtype=float)
vals = px.values
for i in range(len(px)):
    w = vals[i:i + H]
    fwd_dd.iloc[i] = w.min() / vals[i] - 1.0          # worst loss over next year
fwd_dd = fwd_dd.iloc[:-H]                              # drop right-censored tail

# =========================== TEST A: episode level ===========================
# swing-peak tops: local max over +/-60d, then de-dup peaks within 120d (keep higher)
W = 60
hi = px.values
peaks = [i for i in range(W, len(px) - W) if hi[i] == hi[i - W:i + W + 1].max()]
ded = []
for i in peaks:
    if ded and (px.index[i] - px.index[ded[-1]]).days < 120:
        if hi[i] > hi[ded[-1]]:
            ded[-1] = i
    else:
        ded.append(i)

rows = []
for i in ded:
    d = px.index[i]
    if d not in fwd_dd.index or pd.isna(fwd_dd.loc[d]) or pd.isna(F.reindex([d]).iloc[0]):
        continue
    rows.append(dict(peak=d.date(), price=px.iloc[i], depth=fwd_dd.loc[d],
                     froth=F.reindex([d]).iloc[0]))
ep = pd.DataFrame(rows)
ep = ep[ep["depth"] <= -0.15].reset_index(drop=True)   # real declines only

def spearman(a, b):                                     # rank then Pearson (no scipy)
    ra = pd.Series(np.asarray(a, float)).rank().values
    rb = pd.Series(np.asarray(b, float)).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])

rng = np.random.default_rng(7)
dep = ep["depth"].values
rho = spearman(ep["froth"].values, dep)                 # froth high & depth very negative -> rho<0
# permutation p (one-sided: froth predicts deeper i.e. more-negative depth)
perm = [spearman(rng.permutation(ep["froth"].values), dep) for _ in range(20000)]
p_perm = float(np.mean([r <= rho for r in perm]))

print("=" * 72)
print("TEST A — peak episodes: pre-peak froth vs forward 365d crash depth")
print("=" * 72)
print(f"{'peak':>12} {'price':>10} {'depth':>8} {'froth z':>8}")
for _, r in ep.sort_values("peak").iterrows():
    print(f"{str(r['peak']):>12} {r['price']:>10,.0f} {r['depth']*100:>7.0f}% {r['froth']:>8.2f}")
print(f"\nSpearman(froth, depth) = {rho:+.2f}   (negative = more froth -> deeper crash)")
print(f"one-sided permutation p = {p_perm:.3f}   (n = {len(ep)} episodes)")

# =========================== TEST B: all-day quartiles =======================
both = pd.concat([F.rename("froth"), fwd_dd.rename("dd")], axis=1).dropna()
both["q"] = pd.qcut(both["froth"], 4, labels=["Q1 low", "Q2", "Q3", "Q4 high"])
print("\n" + "=" * 72)
print("TEST B — forward 365d drawdown by froth quartile (every day)")
print("=" * 72)
print(f"{'froth quartile':>14} {'avg dd':>9} {'median':>9} {'worst':>9} {'n':>6}")
for q, g in both.groupby("q", observed=True):
    print(f"{str(q):>14} {g['dd'].mean()*100:>8.0f}% {g['dd'].median()*100:>8.0f}% {g['dd'].min()*100:>8.0f}% {len(g):>6}")

hi_q = both[both["q"] == "Q4 high"]["dd"]
lo_q = both[both["q"] == "Q1 low"]["dd"]
gap = hi_q.mean() - lo_q.mean()
# block bootstrap (90d blocks) on the high-minus-low gap -> honest about overlap
arr = both[["froth", "dd"]].values
n, bl = len(arr), 90
boots = []
for _ in range(2000):
    idx = np.concatenate([np.arange(s, min(s + bl, n))
                          for s in rng.integers(0, n - bl, n // bl)])
    b = pd.DataFrame(arr[idx], columns=["froth", "dd"])
    b["q"] = pd.qcut(b["froth"].rank(method="first"), 4, labels=False)
    boots.append(b[b["q"] == 3]["dd"].mean() - b[b["q"] == 0]["dd"].mean())
lo_ci, hi_ci = np.percentile(boots, [2.5, 97.5])
print(f"\nHigh-froth minus low-froth avg drawdown gap = {gap*100:+.0f} pts")
print(f"  block-bootstrap 95% CI: [{lo_ci*100:+.0f}, {hi_ci*100:+.0f}] pts  "
      f"({'EXCLUDES 0 (significant)' if hi_ci < 0 else 'includes 0 (not significant)'})")

# =============================== chart ===============================
fig, ax = plt.subplots(2, 1, figsize=(13, 8), sharex=True, height_ratios=[2.3, 1])
ax[0].semilogy(px.index, px, color="#111", lw=1)
sc = ax[0].scatter(ep["peak"].apply(pd.Timestamp), ep["price"], c=ep["froth"],
                   cmap="RdYlGn_r", s=90, zorder=5, edgecolor="black", linewidth=0.6,
                   vmin=-1.5, vmax=1.5)
for _, r in ep.iterrows():
    ax[0].annotate(f"{r['depth']*100:.0f}%", (pd.Timestamp(r["peak"]), r["price"]),
                   fontsize=7, ha="center", va="bottom")
ax[0].set_ylabel("BTC price (log)")
ax[0].set_title("Peaks colored by pre-crash froth (red = high alt froth)  ·  label = next-year drawdown")
plt.colorbar(sc, ax=ax[0], label="froth z", pad=0.01)
ax[1].fill_between(F.index, F.values, 0, where=(F.values > 0), color="#dc2626", alpha=0.5)
ax[1].fill_between(F.index, F.values, 0, where=(F.values <= 0), color="#16a34a", alpha=0.5)
ax[1].axhline(0, color="#888", lw=0.6)
ax[1].set_ylabel("alt-froth index (z)")
ax[1].set_title("Altcoin froth index over time")
ax[1].grid(True, ls=":", alpha=0.4)
fig.tight_layout()
out = f"{HERE}/charts/altcoin_froth_test.png"
fig.savefig(out, dpi=150, bbox_inches="tight")
print(f"\nSaved chart -> {out}")
