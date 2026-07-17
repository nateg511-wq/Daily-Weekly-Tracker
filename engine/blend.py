"""The master blender: EVERY PILLAR EQUAL-WEIGHTED -> master table + THE FINAL NUMBER.

    Signal(pillar, window) = ((P - 50) / 50) * Quality * Impact
    MASTER(window)         = simple MEAN over ALL pillars of Signal   (equal weight, 1/N each)
    FINAL NUMBER           = weighted mean of the window masters (equal + horizon variants)

Every pillar counts the same, regardless of how many there are: the qualitative
pillars in config/scores.json plus the computed Bitcoin-TA pillar. Add a pillar and
the weight auto-rebalances to 1/N. Impact is a single uniform value (settings.impact)
shared by all pillars, so pillars differ only by their P odds and their Quality.

Also reports a leave-one-out robustness check: the final number recomputed with each
single pillar removed (does any one pillar flip the conclusion?).
"""
from __future__ import annotations

from .common import DATA, GRID, LBL, call, load_json, load_scores, load_settings, log, save_json, signal

QUANT_PILLAR = "Bitcoin TA"


def qual_signals(scores: dict, score_set: str, impact: float) -> dict[int, dict[str, float]]:
    ss = scores["score_sets"][score_set]["P"]
    out: dict[int, dict[str, float]] = {}
    for h in GRID:
        out[h] = {name: signal(ss[name][str(h)], meta["quality"][str(h)], impact)
                  for name, meta in scores["pillars"].items()}
    return out


def run(score_set: str | None = None, quiet: bool = False) -> dict:
    settings = load_settings()
    scores = load_scores()
    impact = settings["impact"]
    score_set = score_set or scores["active_qual_set"]
    if score_set not in scores["score_sets"]:
        raise KeyError(f"score set '{score_set}' not in config/scores.json "
                       f"(have: {', '.join(scores['score_sets'])})")
    quant = load_json(DATA / "pillar_scores.json")

    pillars = list(scores["pillars"]) + [QUANT_PILLAR]
    n = len(pillars)

    # all pillar signals per window (qualitative + the computed quant pillar)
    sigs = qual_signals(scores, score_set, impact)
    for h in GRID:
        sigs[h][QUANT_PILLAR] = quant["windows"][LBL[h]]["signal"]

    # exact (unrounded) masters drive the calls and the finals; rounding is display-only
    exact = {h: sum(sigs[h][p] for p in pillars) / n for h in GRID}
    windows = {}
    for h in GRID:
        windows[LBL[h]] = {"pillars": {p: round(sigs[h][p], 2) for p in pillars},
                           "master": round(exact[h], 2), "call": call(exact[h])}

    finals_exact = {name: sum(w[str(h)] * exact[h] for h in GRID)
                    for name, w in settings["final_weights"].items()}
    finals = {name: round(v, 2) for name, v in finals_exact.items()}

    # leave-one-out: final number (equal window weighting) with each pillar removed
    ew = settings["final_weights"]["equal"]
    loo = {}
    for drop in pillars:
        wm = [sum(sigs[h][p] for p in pillars if p != drop) / (n - 1) for h in GRID]
        loo[drop] = round(sum(ew[str(h)] * m for h, m in zip(GRID, wm)), 2)

    out = dict(asof=quant["asof"], price=quant["price"], score_set=score_set,
               score_set_status=scores["score_sets"][score_set]["status"],
               model="equal-weight", n_pillars=n, weight_each=round(1 / n, 4), impact=impact,
               windows=windows,
               final_number={k: {"value": finals[k], "call": call(finals_exact[k])} for k in finals},
               leave_one_out_final_equal=loo)
    save_json(DATA / "master_blend.json", out)

    if not quiet:
        w = f"{100 / n:.0f}%"
        hdr = f"{'Window':>7} | " + " | ".join(f"{p[:11]:>11}" for p in pillars) + f" | {'MASTER':>7} | Call"
        print(hdr)
        print("-" * len(hdr))
        for h in GRID:
            r = windows[LBL[h]]
            print(f"{LBL[h]:>7} | " + " | ".join(f"{r['pillars'][p]:>+11.2f}" for p in pillars) +
                  f" | {r['master']:>+7.2f} | {r['call']}")
        fe, fh = finals["equal"], finals["horizon"]
        print(f"\nEqual weight: {n} pillars, {w} each (uniform impact {impact}).")
        print(f"THE FINAL NUMBER: equal-weight {fe:+.2f} ({call(finals_exact['equal'])})  ·  "
              f"horizon-weighted {fh:+.2f} ({call(finals_exact['horizon'])})")
        print("Leave-one-out final (equal): " +
              " · ".join(f"−{d.split()[0]} {v:+.2f}" for d, v in loo.items()))
        print(f"[score set: {score_set} ({out['score_set_status']}) · BTC ${quant['price']:,.0f} · {quant['asof']}]")
    return out
