"""Human/AI-readable digests of the current state.

`numbers` — every figure a report writer needs, in one paste-able block.
`status`  — the latest master table + final number, no recompute.
"""
from __future__ import annotations

import pandas as pd

from .common import DATA, GRID, LBL, call, load_json, load_scores


def print_status() -> None:
    mb = load_json(DATA / "master_blend.json")
    print(f"As of {mb['asof']} · BTC ${mb['price']:,.0f} · score set: {mb['score_set']} ({mb['score_set_status']})")
    print(f"Model: equal weight — {mb['n_pillars']} pillars, {mb['weight_each']*100:.0f}% each, uniform impact {mb['impact']}\n")
    pillars = list(next(iter(mb["windows"].values()))["pillars"])
    hdr = f"{'Window':>7} | " + " | ".join(f"{p[:11]:>11}" for p in pillars) + f" | {'MASTER':>7} | Call"
    print(hdr)
    print("-" * len(hdr))
    for h in GRID:
        r = mb["windows"][LBL[h]]
        print(f"{LBL[h]:>7} | " + " | ".join(f"{r['pillars'][p]:>+11.2f}" for p in pillars) +
              f" | {r['master']:>+7.2f} | {r['call']}")
    fn = mb["final_number"]
    print(f"\nTHE FINAL NUMBER: {fn['equal']['value']:+.2f} ({fn['equal']['call']}) equal-weight · "
          f"{fn['horizon']['value']:+.2f} ({fn['horizon']['call']}) horizon-weighted")
    loo = mb.get("leave_one_out_final_equal", {})
    if loo:
        robust = "all same sign (robust)" if min(loo.values()) * max(loo.values()) > 0 else "SIGN FLIPS (fragile)"
        print(f"Leave-one-out final (drop any one pillar): {min(loo.values()):+.2f} to {max(loo.values()):+.2f} — {robust}")


def print_digest() -> None:
    sig = load_json(DATA / "signals.json")
    cyc = load_json(DATA / "cycle.json")
    ps = load_json(DATA / "pillar_scores.json")
    scores = load_scores()

    print("=" * 78)
    print(f"COINPICKS NUMBERS DIGEST — {cyc['asof']} — BTC ${cyc['price']:,.2f}")
    print("=" * 78)

    print("\nTAPE COMPOSITES (as-is | completed bars only):")
    for tf in ("weekly", "monthly", "quarterly"):
        r = sig[tf]
        label = r['overall'].capitalize() if r['overall_intensity'].lower() == r['overall'].lower() \
            else f"{r['overall_intensity']} {r['overall']}"
        print(f"  {tf:9} {r['composite']:+6.1f} ({label}, "
              f"agreement {r['agreement']}/7) | completed {r['composite_completed_bars']:+.1f} | bar {r['date']}")

    print("\nKEY INDICATOR READINGS (current bar; PARTIAL until it closes):")
    for tf in ("weekly", "monthly", "quarterly"):
        ind = pd.read_csv(DATA / f"indicators_{tf}.csv", parse_dates=["date"]).set_index("date").iloc[-1]
        p = ind["close"]
        smas = "  ".join(f"SMA{n} ${ind[f'sma{n}']:,.0f} ({p/ind[f'sma{n}']-1:+.1%})"
                         for n in (20, 50, 200) if pd.notna(ind[f"sma{n}"]))
        print(f"  {tf:9} {smas}")
        print(f"            RSI {ind['rsi14']:.1f} | MACD {ind['macd']:,.0f} hist {ind['macd_hist']:+,.0f} | %B {ind['bb_pctb']:.2f}")

    print("\nLEVELS (weekly):")
    lv = pd.read_csv(DATA / "levels_weekly.csv")
    p = cyc["price"]
    sup = lv[lv.level <= p].sort_values("level", ascending=False).head(3)
    res = lv[lv.level > p].sort_values("level").head(3)
    for _, r in res.iloc[::-1].iterrows():
        print(f"  resistance ${r.level:>10,.0f}  ({r.dist_pct:+.1f}%, {r.touches}x)")
    print(f"  price      ${p:>10,.0f}")
    for _, r in sup.iterrows():
        print(f"  support    ${r.level:>10,.0f}  ({r.dist_pct:+.1f}%, {r.touches}x)")
    tl = pd.read_csv(DATA / "trendlines.csv")
    for _, t in tl[tl.timeframe == "weekly"].iterrows():
        print(f"  trendline  ${t.value_now:>10,.0f}  ({t.type}, {t.direction})")

    print(f"\nCYCLE: month {cyc['cycle_month']} | projections (avg C1–C3): "
          f"top m{cyc['projections_from_C1_C3']['m_top']}, bottom m{cyc['projections_from_C1_C3']['m_bottom']}, "
          f"momentum-turn m{cyc['projections_from_C1_C3']['m_turn']}")
    cur = cyc["cycles"][-1]
    print(f"  this cycle: top ${cur['top']:,.0f} ({cur['top_date']}), low ${cur['bottom']:,.0f} "
          f"({cur['bottom_date']}, {cur['drawdown']:+.0%})")
    print("  analogs (fwd returns at this cycle-month in C1–C3; n=3 — levels soft, direction is the signal):")
    for h in GRID:
        a = cyc["analogs"][str(h)]
        print(f"    {LBL[h]:>4}: {a['hit']} positive, median {a['median_ret']:+.1%}  (score {a['score']:+.1f})")
    pl = cyc["powerlaw"]
    print(f"  power-law: fair ${pl['fair']:,} ({pl['pct_vs_fair']:+.0%} vs fair) | −1σ ${pl['minus1sd']:,} | "
          f"−2σ ${pl['minus2sd']:,} | fit-start sensitivity {pl['fit_start_sensitivity']}")
    print(f"  froth: z {cyc['froth']['z']:+.2f} (as of {cyc['froth']['asof']} — {cyc['froth']['note']})")

    print("\nQUANT PILLAR (computed draft):")
    print(f"  {'win':>4} | {'S':>6} | {'P':>3} | {'Q':>4} | Signal")
    for h in GRID:
        w = ps["windows"][LBL[h]]
        print(f"  {LBL[h]:>4} | {w['S']:+6.1f} | {w['P']:>3} | {w['quality']:.2f} | {w['signal']:+.2f}")

    print(f"\nQUALITATIVE SCORE SETS (active: {scores['active_qual_set']}):")
    for name, ss in scores["score_sets"].items():
        paths = " · ".join(f"{p}: {'/'.join(str(ss['P'][p][str(h)]) for h in GRID)}" for p in ss["P"])
        print(f"  {name} ({ss['status']}): {paths}")

    print("\nNext: edit config/scores.json (new score set) after research, then `python run.py blend && python run.py render`.")
