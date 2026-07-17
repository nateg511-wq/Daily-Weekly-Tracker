#!/usr/bin/env python3
"""
*** SUPERSEDED (July 8, 2026) ***
This draft blender carries STALE pre-correction numbers (old CLARITY P's,
missing Fed & Macro, Tokenization at 20% with window gaps). The live engine
is:  ~/Desktop/Master Report 2026-07-08/master_blend.py
which blends all four corrected qualitative pillars + the quantitative
BTC-TA sleeve (~/Desktop/BTC-TA/pillar_mapping.py). Kept for the record.

CoinPicks pillar blender.
Paste each report's committed numbers below, run: python3 blend.py
Engine: Signal = ((P-50)/50) * Quality * Impact   (range -10..+10)
        Blend(window) = sum(Weight*Signal) / sum(Weight present)
Locked windows: 1mo, 3mo, 6mo, 1yr, 3yr  (horizons 1/3/6/12/36 months)
QUALITY MUST BE 0-1. P is 0-100 (50 = neutral). Impact is 0-10.
"""

GRID = [1, 3, 6, 12, 36]
LBL  = {1: "1mo", 3: "3mo", 6: "6mo", 12: "1yr", 36: "3yr"}

# weight (fraction), impact, rows = {horizon_months: (P, quality_0to1)}
# Only on-grid windows that the report actually committed are filled.
# None = the report has no committed value for that window yet (DATA GAP).
PILLARS = {
    "CLARITY Act":   dict(w=0.30, impact=9, rows={1:(50,0.85), 3:(50,0.85), 6:(55,0.85), 12:(70,0.90), 36:(80,0.90)}),
    "Iran War Risk": dict(w=0.25, impact=7, rows={1:(50,0.60), 3:(55,0.65), 6:(62,0.70), 12:(75,0.65), 36:None}),      # GAP: no 3yr (had off-grid 2yr)
    "Tokenization":  dict(w=0.20, impact=8, rows={1:None,      3:None,      6:(55,0.90), 12:(62,0.80), 36:(78,0.60)}),  # GAP: no 1mo/3mo; Quality RESCALED 9/8/7/6/5 -> 0.9..0.5
}

def signal(P, Q, I):
    return ((P - 50) / 50) * Q * I

def call(s):
    a = abs(s); d = "Bull" if s > 0 else "Bear"
    if a < 0.5:  return "Neutral"
    if a < 1.5:  return f"Mild {d}"
    if a < 3.0:  return d
    if a < 5.0:  return f"Strong {d}"
    return f"Very Strong {d}"

print(f"\n{'Window':>7} | {'Blend':>6} | {'Call':<12} | {'Cov':>4} | contributing pillars (signal)")
print("-" * 86)
for h in GRID:
    parts = []
    for name, d in PILLARS.items():
        cell = d["rows"].get(h)
        if cell is None:
            continue
        P, Q = cell
        parts.append((d["w"], signal(P, Q, d["impact"]), name))
    sw = sum(w for w, _, _ in parts)
    blend = sum(w * s for w, s, _ in parts) / sw if sw else 0.0
    det = ", ".join(f"{n} {s:+.2f}" for w, s, n in parts)
    print(f"{LBL[h]:>7} | {blend:+6.2f} | {call(blend):<12} | {int(sw*100):>3}% | {det}")
print("\nGaps to fill: Iran 3yr P/Q; Tokenization 1mo & 3mo P/Q; + 2 more pillars to reach 100% weight.")
