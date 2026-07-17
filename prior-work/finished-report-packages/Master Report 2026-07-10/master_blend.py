#!/usr/bin/env python3
"""
CoinPicks MASTER blender — qualitative pillars + the quantitative BTC-TA sleeve.

Two qualitative score sets are carried:
  * JUNE COMMITTED — Alex's stamped scores from the June 12–19 reports.
  * JULY 8 DRAFT   — re-rated after the July 8 re-research (fired triggers:
    CLARITY July-1 down-trigger; Iran ceasefire break + Hormuz shock;
    Tokenization Q2 print / GENIUS partial-slip; Fed hike-odds >75%).
    Drafts are AWAITING ALEX'S STAMP — the July 8 reports show both sets.

Default blend uses SCORESET = "july8_draft" (what the current evidence says).
Flip SCORESET to "june_committed" to reproduce the stamped-only master.

Engine (house standard):
    Signal(pillar, window) = ((P - 50) / 50) * Quality * Impact      [-10 .. +10]
    Qual blend(window)     = sum(w_i * Signal_i) / sum(w_i)          (weights sum 1.05 -> normalized)
    MASTER(window)         = mix * QualBlend + (1 - mix) * QuantSignal
Call bands on |signal|: <0.5 Neutral | <1.5 Mild | <3.0 Bull/Bear | <5.0 Strong | else Very Strong
"""
import json
import os

GRID = [1, 3, 6, 12, 36]
LBL = {1: "1mo", 3: "3mo", 6: "6mo", 12: "1yr", 36: "3yr"}
SCORESET = "july10_draft"         # or "july8_draft" / "june_committed"

# quality per window (unchanged June -> July)
QUALITY = {
    "CLARITY Act":   {1: 0.85, 3: 0.85, 6: 0.85, 12: 0.90, 36: 0.95},
    "Iran War Risk": {1: 0.60, 3: 0.65, 6: 0.70, 12: 0.65, 36: 0.55},
    "Tokenization":  {1: 0.90, 3: 0.88, 6: 0.85, 12: 0.78, 36: 0.70},
    "Fed & Macro":   {1: 0.85, 3: 0.85, 6: 0.80, 12: 0.75, 36: 0.65},
}
META = {  # weight, impact
    "CLARITY Act":   (0.25, 9),
    "Iran War Risk": (0.25, 7),
    "Tokenization":  (0.30, 8),
    "Fed & Macro":   (0.25, 9),
}
P = {
    "june_committed": {   # stamped June 12-19, 2026
        "CLARITY Act":   {1: 55, 3: 60, 6: 65, 12: 85, 36: 92},
        "Iran War Risk": {1: 50, 3: 55, 6: 62, 12: 75, 36: 85},
        "Tokenization":  {1: 53, 3: 57, 6: 62, 12: 72, 36: 85},
        "Fed & Macro":   {1: 38, 3: 40, 6: 46, 12: 54, 36: 61},
    },
    "july8_draft": {      # re-rated July 8, 2026 — superseded by july10_draft
        "CLARITY Act":   {1: 52, 3: 56, 6: 61, 12: 83, 36: 92},
        "Iran War Risk": {1: 40, 3: 47, 6: 55, 12: 70, 36: 83},
        "Tokenization":  {1: 52, 3: 56, 6: 62, 12: 73, 36: 85},
        "Fed & Macro":   {1: 35, 3: 36, 6: 42, 12: 52, 36: 61},
    },
    "july10_draft": {     # re-rated July 10, 2026 — awaiting stamp
        "CLARITY Act":   {1: 50, 3: 54, 6: 60, 12: 82, 36: 92},
        "Iran War Risk": {1: 42, 3: 49, 6: 56, 12: 70, 36: 83},
        "Tokenization":  {1: 53, 3: 58, 6: 64, 12: 74, 36: 85},
        "Fed & Macro":   {1: 34, 3: 36, 6: 44, 12: 53, 36: 61},
    },
}

# THE ONE FINAL NUMBER: cross-window synthesis of the five master signals.
# Headline = equal-weight mean of the 1mo/3mo/6mo/1yr/3yr master signals.
# Variant  = horizon-weighted (10/15/20/30/25%) for a longer-money posture.
FINAL_WEIGHTS = {"equal": [0.2]*5, "horizon": [0.10, 0.15, 0.20, 0.30, 0.25]}

QUANT_JSON = os.path.expanduser("~/Desktop/BTC-TA/data/pillar_scores.json")
MIXES = [0.5, 0.6, 0.4]           # qual share of the master; 0.5 is the headline


def signal(p, q, i):
    return ((p - 50) / 50) * q * i


def call(s):
    a = abs(s); d = "Bull" if s > 0 else "Bear"
    if a < 0.5: return "Neutral"
    if a < 1.5: return f"Mild {d}"
    if a < 3.0: return d
    if a < 5.0: return f"Strong {d}"
    return f"Very Strong {d}"


def blend(scoreset):
    q = json.load(open(QUANT_JSON))
    quant = {h: q["windows"][LBL[h]]["signal"] for h in GRID}
    wsum = sum(w for w, _ in META.values())
    out = {}
    for h in GRID:
        sigs = {n: signal(P[scoreset][n][h], QUALITY[n][h], META[n][1]) for n in META}
        qual = sum(META[n][0] * sigs[n] for n in META) / wsum
        row = {"pillars": {n: round(s, 2) for n, s in sigs.items()},
               "qual_blend": round(qual, 2), "quant": quant[h]}
        for mix in MIXES:
            row[f"master_{int(mix*100)}q"] = round(mix * qual + (1 - mix) * quant[h], 2)
        row["call"] = call(row["master_50q"])
        out[LBL[h]] = row
    return q, out


def main():
    q, out = blend(SCORESET)
    _, june = blend("june_committed")
    print(f"Scoreset: {SCORESET} | quant: BTC-TA pillar_scores.json as of {q['asof']} (BTC ${q['price']:,.0f})\n")
    hdr = f"{'Window':>7} | " + " | ".join(f"{n[:12]:>12}" for n in META) + \
          f" | {'QUAL blend':>10} | {'QUANT (TA)':>10} | {'MASTER 50/50':>12} | {'(June cmte)':>11} | Call"
    print(hdr); print("-" * len(hdr))
    for h in GRID:
        r, j = out[LBL[h]], june[LBL[h]]
        print(f"{LBL[h]:>7} | " + " | ".join(f"{r['pillars'][n]:>+12.2f}" for n in META) +
              f" | {r['qual_blend']:>+10.2f} | {r['quant']:>+10.2f} | {r['master_50q']:>+12.2f} | {j['master_50q']:>+11.2f} | {r['call']}")
    print("\nSensitivity (master at other qual/quant mixes):")
    for h in GRID:
        r = out[LBL[h]]
        print(f"  {LBL[h]:>4}: 60/40 {r['master_60q']:+.2f} ({call(r['master_60q'])})   40/60 {r['master_40q']:+.2f} ({call(r['master_40q'])})")
    masters = [out[LBL[h]]["master_50q"] for h in GRID]
    finals = {k: round(sum(w*m for w, m in zip(ws, masters)), 2) for k, ws in FINAL_WEIGHTS.items()}
    print(f"\nTHE FINAL NUMBER (cross-window): equal-weight {finals['equal']:+.2f} ({call(finals['equal'])})"
          f"  ·  horizon-weighted {finals['horizon']:+.2f} ({call(finals['horizon'])})")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "master_blend.json")
    with open(path, "w") as f:
        json.dump({"asof": "2026-07-10", "scoreset": SCORESET, "final_number": finals, "quant_source": QUANT_JSON,
                   "qual_weights_sum": round(sum(w for w, _ in META.values()), 2),
                   "windows": out, "june_committed_master": {k: v["master_50q"] for k, v in june.items()}},
                  f, indent=2)
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
