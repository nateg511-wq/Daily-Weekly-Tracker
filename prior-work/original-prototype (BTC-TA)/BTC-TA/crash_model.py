#!/usr/bin/env python3
"""
CRASH-RISK GAUGE: P(a deep BTC drawdown occurs within the next 365 days | froth),
a logistic hazard model -- tested OUT-OF-SAMPLE via leave-one-cycle-out so the
model predicts crashes in cycles it never trained on. Plus conditional depth.

Honest by construction: froth uses only trailing data; the model that scores each
cycle is trained on the OTHER cycles; performance reported on held-out cycles only.
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
H, THRESH = 365, -0.35                    # horizon (days), "deep crash" = >=35% drawdown ahead


def zroll(s, w=730):
    return (s - s.rolling(w, min_periods=200).mean()) / s.rolling(w, min_periods=200).std()


altbtc = df["alt_mcap"] / df["btc_mcap"]
froth = pd.concat([zroll(df["alt_share"]), zroll(df["eth_btc"]),
                   zroll(altbtc.pct_change(90))], axis=1).mean(axis=1)

fwd = pd.Series(index=px.index, dtype=float)
v = px.values
for i in range(len(px) - H):
    fwd.iloc[i] = v[i:i + H].min() / v[i] - 1.0

# halving-cycle id (for leave-one-cycle-out)
halvings = [pd.Timestamp(d) for d in ["2016-07-09", "2020-05-11", "2024-04-19"]]
cyc = pd.Series(1, index=px.index)
for h in halvings:
    cyc[px.index >= h] += 1

D = pd.concat([froth.rename("froth"), fwd.rename("fwd"), cyc.rename("cyc")], axis=1).dropna()
D["y"] = (D["fwd"] <= THRESH).astype(int)


def fit_logistic(X, y, l2=2.0, iters=60):
    w = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(X @ w)))
        W = np.clip(p * (1 - p), 1e-6, None)
        g = X.T @ (p - y) + l2 * w
        Hess = X.T @ (X * W[:, None]) + l2 * np.eye(X.shape[1])
        w -= np.linalg.solve(Hess, g)
    return w


def design(fr, mu, sd):
    z = (fr - mu) / sd
    return np.column_stack([np.ones_like(z), z])


def auc(score, y):                         # rank-based AUC (no sklearn)
    r = pd.Series(score).rank().values
    n1, n0 = y.sum(), (1 - y).sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0) if n1 and n0 else np.nan


# ---- leave-one-cycle-out out-of-sample gauge ----
D["oos"] = np.nan
for c in sorted(D["cyc"].unique()):
    tr, te = D[D["cyc"] != c], D[D["cyc"] == c]
    if tr["y"].sum() < 3 or te["y"].sum() < 1:           # need events on both sides to learn/score
        continue
    mu, sd = tr["froth"].mean(), tr["froth"].std()
    w = fit_logistic(design(tr["froth"].values, mu, sd), tr["y"].values)
    D.loc[te.index, "oos"] = 1 / (1 + np.exp(-(design(te["froth"].values, mu, sd) @ w)))

scored = D.dropna(subset=["oos"])
oos_auc = auc(scored["oos"].values, scored["y"].values)

# ---- full-sample fit for the live reading + the P(crash|froth) curve ----
mu, sd = D["froth"].mean(), D["froth"].std()
w_full = fit_logistic(design(D["froth"].values, mu, sd), D["y"].values)
froth_now = froth.dropna().iloc[-1]
p_now = 1 / (1 + np.exp(-(design(np.array([froth_now]), mu, sd) @ w_full)[0]))

print("=" * 70)
print(f"CRASH-RISK GAUGE  —  P(>=35% drawdown within {H}d | froth)")
print("=" * 70)
print(f"Events in sample: {int(D['y'].sum())} of {len(D)} days flagged 'deep crash ahead'")
print(f"OUT-OF-SAMPLE AUC (leave-one-cycle-out): {oos_auc:.2f}   "
      f"(0.5 = coin flip, 1.0 = perfect; >0.7 = genuinely useful)")
print("\nP(crash) at different froth levels (full-sample fit):")
for fz in [-1.5, -1.0, 0.0, 1.0, 1.5, 2.0]:
    p = 1 / (1 + np.exp(-(design(np.array([fz]), mu, sd) @ w_full)[0]))
    print(f"  froth z = {fz:+.1f}  ->  P(deep crash ahead) = {p*100:4.0f}%")
print(f"\nTODAY  froth z = {froth_now:+.2f}  ->  crash-risk gauge = {p_now*100:.0f}%")

# ---- conditional depth by froth tercile ----
D["tier"] = pd.qcut(D["froth"], 3, labels=["low", "mid", "high"])
print("\nConditional drawdown depth by froth (next-year worst loss):")
for t, g in D.groupby("tier", observed=True):
    print(f"  {t:>4} froth: typical {g['fwd'].median()*100:+.0f}%   bad-case(10th pct) {g['fwd'].quantile(.10)*100:+.0f}%")

# ===================== chart =====================
fig, ax = plt.subplots(3, 1, figsize=(13, 9), sharex=True, height_ratios=[2, 1.3, 1])
ax[0].semilogy(px.index, px, color="#111", lw=1)
ax[0].set_ylabel("BTC (log)")
ax[0].set_title(f"Out-of-sample crash-risk gauge  (OOS AUC {oos_auc:.2f})  ·  shaded = a ≥35% drop was actually ahead")
# shade days where a deep crash was actually coming
deep = D[D["y"] == 1]
for ax_ in ax[:2]:
    for d in deep.index:
        ax_.axvspan(d, d + pd.Timedelta(days=1), color="#fca5a5", alpha=0.25, lw=0)
ax[1].plot(scored.index, scored["oos"] * 100, color="#b91c1c", lw=1.3)
ax[1].axhline(p_now * 100, color="#2563eb", ls=":", lw=1, label=f"today {p_now*100:.0f}%")
ax[1].scatter([froth.dropna().index[-1]], [p_now * 100], color="#2563eb", s=60, zorder=5)
ax[1].set_ylabel("crash-risk %\n(out-of-sample)")
ax[1].legend(loc="upper right", fontsize=8)
ax[1].grid(True, ls=":", alpha=0.4)
ax[2].fill_between(froth.index, froth.values, 0, where=(froth.values > 0), color="#dc2626", alpha=0.5)
ax[2].fill_between(froth.index, froth.values, 0, where=(froth.values <= 0), color="#16a34a", alpha=0.5)
ax[2].axhline(0, color="#888", lw=0.6)
ax[2].set_ylabel("froth z")
ax[2].grid(True, ls=":", alpha=0.4)
fig.tight_layout()
out = f"{HERE}/charts/crash_risk_gauge.png"
fig.savefig(out, dpi=150, bbox_inches="tight")
print(f"\nSaved chart -> {out}")
