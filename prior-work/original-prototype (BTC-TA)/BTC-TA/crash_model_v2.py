#!/usr/bin/env python3
"""
Multi-signal crash/depth model.  Two questions:
  (1) Does adding cycle-phase + valuation + position + momentum to froth beat the
      froth-only out-of-sample AUC of 0.58?  (logistic hazard, leave-one-cycle-out)
  (2) HOW FAR DOWN can this cycle go?  Conditional downside from today's state via
      leave-one-cycle-out k-nearest-neighbour analogs + a power-law valuation floor.
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

np.seterr(over="ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(f"{HERE}/data/altcoin_data.csv", parse_dates=["date"]).set_index("date").sort_index()
px = df["btc_price"].astype(float)
H, THRESH = 365, -0.35
GENESIS = pd.Timestamp("2009-01-03")


def zroll(s, w=730):
    return (s - s.rolling(w, min_periods=200).mean()) / s.rolling(w, min_periods=200).std()


# ---------- features (all trailing) ----------
altbtc = df["alt_mcap"] / df["btc_mcap"]
froth = pd.concat([zroll(df["alt_share"]), zroll(df["eth_btc"]), zroll(altbtc.pct_change(90))],
                  axis=1).mean(axis=1)
halvings = [pd.Timestamp(d) for d in ["2012-11-28", "2016-07-09", "2020-05-11", "2024-04-19"]]
phase = pd.Series([max((d - max(h for h in halvings if h <= d)).days / 30.44
                       if any(h <= d for h in halvings) else 0, 0) for d in px.index], index=px.index)
mayer = px / px.rolling(200).mean()
dd_ath = px / px.cummax() - 1.0
mom = px / px.shift(180) - 1.0
cyc = pd.Series(1, index=px.index)
for h in halvings[1:]:
    cyc[px.index >= h] += 1

# ---------- forward 365d drawdown (target) ----------
fwd = pd.Series(index=px.index, dtype=float)
v = px.values
for i in range(len(px) - H):
    fwd.iloc[i] = v[i:i + H].min() / v[i] - 1.0

FEAT = ["froth", "phase", "mayer", "dd_ath", "mom"]
D = pd.concat([froth.rename("froth"), phase.rename("phase"), mayer.rename("mayer"),
               dd_ath.rename("dd_ath"), mom.rename("mom"), fwd.rename("fwd"),
               cyc.rename("cyc"), px.rename("px")], axis=1)
Dq = D.dropna(subset=FEAT)                      # query rows (features present, fwd may be NaN)
Dt = Dq.dropna(subset=["fwd"]).copy()           # training rows (have outcome)
Dt["y"] = (Dt["fwd"] <= THRESH).astype(int)


def logit_fit(X, y, l2=2.0, it=60):
    w = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-np.clip(X @ w, -30, 30)))
        W = np.clip(p * (1 - p), 1e-6, None)
        w -= np.linalg.solve(X.T @ (X * W[:, None]) + l2 * np.eye(X.shape[1]), X.T @ (p - y) + l2 * w)
    return w


def auc(s, y):
    r = pd.Series(s).rank().values
    n1, n0 = y.sum(), (1 - y).sum()
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0) if n1 and n0 else np.nan


def std_cols(tr, cols):
    return tr[cols].mean(), tr[cols].std()


# ---------- (1) leave-one-cycle-out AUC: froth-only vs multi-signal ----------
def loco_auc(cols):
    Dt["oos"] = np.nan
    for c in sorted(Dt["cyc"].unique()):
        tr, te = Dt[Dt["cyc"] != c], Dt[Dt["cyc"] == c]
        if tr["y"].sum() < 3 or te["y"].sum() < 1:
            continue
        mu, sd = std_cols(tr, cols)
        Xtr = np.column_stack([np.ones(len(tr))] + [((tr[c2] - mu[c2]) / sd[c2]).values for c2 in cols])
        w = logit_fit(Xtr, tr["y"].values)
        Xte = np.column_stack([np.ones(len(te))] + [((te[c2] - mu[c2]) / sd[c2]).values for c2 in cols])
        Dt.loc[te.index, "oos"] = 1 / (1 + np.exp(-np.clip(Xte @ w, -30, 30)))
    s = Dt.dropna(subset=["oos"])
    return auc(s["oos"].values, s["y"].values)


auc_froth = loco_auc(["froth"])
auc_multi = loco_auc(FEAT)

# ---------- (2) how far down: leave-one-cycle-out KNN analogs for today's state ----------
cur = Dq.iloc[-1]
cur_px, cur_cyc = cur["px"], cur["cyc"]
ath = px.cummax().iloc[-1]
mu, sd = std_cols(Dt[Dt["cyc"] != cur_cyc], FEAT)        # standardize on OTHER cycles
def zvec(row):
    return np.array([(row[c] - mu[c]) / sd[c] for c in FEAT])
pool = Dt[Dt["cyc"] != cur_cyc].copy()                   # analogs from cycles we're NOT in
pool["dist"] = pool.apply(lambda r: np.sqrt(((zvec(r) - zvec(cur)) ** 2).sum()), axis=1)
K = 150
nn = pool.nsmallest(K, "dist")
q = {p: np.quantile(nn["fwd"], p) for p in [0.5, 0.25, 0.10, 0.05]}

# ---------- power-law valuation floor ----------
days = np.log10([(d - GENESIS).days for d in px.index])
lp = np.log10(px.values)
b, a = np.polyfit(days, lp, 1)
fit = a + b * days
resid_sd = (lp - fit).std()
fair_now = 10 ** fit[-1]
pl_lower1 = 10 ** (fit[-1] - resid_sd)                    # ~1 sd cheap band

print("=" * 70)
print("(1) OUT-OF-SAMPLE AUC (leave-one-cycle-out)")
print("=" * 70)
print(f"  froth only      : {auc_froth:.2f}")
print(f"  multi-signal    : {auc_multi:.2f}   ({'better' if auc_multi>auc_froth else 'no better'};  >0.70 = genuinely useful)")

print("\n" + "=" * 70)
print("(2) HOW FAR DOWN FROM HERE — analogs in OTHER cycles to today's state")
print("=" * 70)
print(f"  Today: BTC ${cur_px:,.0f}   ({dd_ath.iloc[-1]*100:.0f}% from ATH ${ath:,.0f})")
print(f"  froth z {cur['froth']:+.2f} | {cur['phase']:.0f}mo post-halving | Mayer {cur['mayer']:.2f} | mom180 {cur['mom']*100:+.0f}%")
print(f"  {K} closest historical analogs (other cycles): further 1-yr drawdown from here ->")
for p, lab in [(0.5, "median"), (0.25, "soft-bear (25th)"), (0.10, "bear (10th)"), (0.05, "tail (5th)")]:
    low = cur_px * (1 + q[p])
    print(f"    {lab:18}: {q[p]*100:+5.0f}%  ->  ~${low:,.0f}   (total {low/ath-1:+.0%} from ATH)")
print(f"\n  Power-law fair value now ~${fair_now:,.0f}; ~1sd cheap band ~${pl_lower1:,.0f}")
print(f"  (price is {(cur_px/fair_now-1)*100:.0f}% vs fair value)")
print("  Historical cycle troughs for reference: -77% to -85% from ATH "
      f"-> ${ath*0.23:,.0f} to ${ath*0.15:,.0f}")

# ---------- chart: how far down ----------
fig, ax = plt.subplots(figsize=(13, 7))
recent = px[px.index >= "2022-01-01"]
ax.semilogy(recent.index, recent, color="#111", lw=1.3)
levels = [(cur_px, "#2563eb", f"today ${cur_px:,.0f}"),
          (cur_px * (1 + q[0.5]), "#16a34a", f"median low ${cur_px*(1+q[0.5]):,.0f} ({q[0.5]*100:+.0f}%)"),
          (cur_px * (1 + q[0.10]), "#f59e0b", f"bear low ${cur_px*(1+q[0.10]):,.0f} ({q[0.10]*100:+.0f}%)"),
          (cur_px * (1 + q[0.05]), "#dc2626", f"tail low ${cur_px*(1+q[0.05]):,.0f} ({q[0.05]*100:+.0f}%)"),
          (pl_lower1, "#7c3aed", f"power-law cheap band ${pl_lower1:,.0f}")]
for lvl, c, lab in levels:
    ax.axhline(lvl, color=c, ls="--", lw=1.4, alpha=0.9)
    ax.text(recent.index[2], lvl, " " + lab, color=c, fontsize=8.5, va="bottom", fontweight="bold")
ax.set_ylabel("BTC price (log)")
ax.set_title(f"How far down can this cycle go?  (analogs from prior cycles + power-law floor)\n"
             f"multi-signal OOS AUC {auc_multi:.2f} vs froth-only {auc_froth:.2f}")
ax.grid(True, which="both", ls=":", alpha=0.4)
fig.tight_layout()
out = f"{HERE}/charts/downside_scenarios.png"
fig.savefig(out, dpi=150, bbox_inches="tight")
print(f"\nSaved chart -> {out}")
