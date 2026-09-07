"""Self-check: environment, config validity, math invariants, data freshness,
and cross-file consistency. Exit code 0 = healthy; 1 = problems listed.

Run: python run.py selfcheck
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.common import (  # noqa: E402
    CONFIG, DATA, GRID, LBL, REPORTS, call, load_json, load_scores, load_settings, signal,
)

results: list[tuple[bool, str]] = []


def check(ok: bool, name: str, detail: str = "") -> None:
    results.append((ok, name))
    print(("  PASS " if ok else "  FAIL ") + name + (f"  — {detail}" if detail and not ok else ""))


def run_all() -> int:
    print("== environment ==")
    for m in ("pandas", "numpy", "matplotlib", "mplfinance"):
        try:
            __import__(m)
            check(True, f"import {m}")
        except ImportError as e:
            check(False, f"import {m}", str(e))
    from engine.render import find_chrome
    chrome = find_chrome()
    check(chrome is not None, "Chrome/Chromium/Edge for PDFs", "not found — PDFs will be skipped (HTML still works)")

    print("== config ==")
    try:
        settings = load_settings()
        scores = load_scores()
        check(True, "config JSONs parse")
    except Exception as e:  # noqa: BLE001
        check(False, "config JSONs parse", str(e))
        return finish()
    active = scores.get("active_qual_set")
    check(active in scores.get("score_sets", {}), "active_qual_set exists", str(active))
    for name, ss in scores["score_sets"].items():
        check(set(ss["P"]) == set(scores["pillars"]),
              f"score set {name} covers all pillars", f"has {sorted(ss['P'])}")
        for p, path in ss["P"].items():
            ok = (p in scores["pillars"]
                  and set(path) == {"1", "3", "6", "12", "36"}
                  and all(0 <= v <= 100 for v in path.values()))
            check(ok, f"score set {name} / {p} valid")
    for p, meta in scores["pillars"].items():
        ok = set(meta["quality"]) == {"1", "3", "6", "12", "36"} and all(0 <= q <= 1 for q in meta["quality"].values())
        check(ok, f"pillar {p} quality valid")
    check(0 <= settings["impact"] <= 10, "uniform impact in range", str(settings.get("impact")))
    fw = settings["final_weights"]
    for k, w in fw.items():
        check(abs(sum(w.values()) - 1.0) < 1e-9, f"final_weights[{k}] sums to 1")
    check(abs(sum(settings["indicator_weights"].values()) - 1.0) < 1e-9, "indicator_weights sum to 1")
    VALID_SRC = {"weekly", "monthly", "quarterly", "analog", "powerlaw"}
    for h in GRID:
        wb = settings["quant"]["window_blend"][str(h)]
        check(abs(sum(wb.values()) - 1.0) < 1e-9, f"quant window_blend[{h}] sums to 1")
        check(set(wb) <= VALID_SRC, f"quant window_blend[{h}] sources valid", str(set(wb) - VALID_SRC))
    W5 = {"1", "3", "6", "12", "36"}
    check(set(settings["quant"]["quality"]) == W5, "quant quality covers all windows")
    check(set(settings["quant"]["quality_basis"]) == W5, "quant quality_basis covers all windows")

    print("== formula invariants ==")
    check(signal(50, 0.9, 9) == 0.0, "signal(P=50) == 0")
    check(abs(signal(100, 1, 10) - 10) < 1e-9 and abs(signal(0, 1, 10) + 10) < 1e-9, "signal range ±10")
    check(call(0.49) == "Neutral" and call(0.5) == "Mild Bull" and call(-1.5) == "Bear"
          and call(2.99) == "Bull" and call(3.0) == "Strong Bull" and call(-5.0) == "Very Strong Bear",
          "call bands at boundaries")

    print("== data ==")
    needed = ["btc_usd_daily_full.csv", "signals.json", "cycle.json", "pillar_scores.json", "master_blend.json"]
    have_all = True
    for f in needed:
        ok = (DATA / f).exists()
        have_all &= ok
        check(ok, f"data/{f} present", "run `python run.py all`")
    if have_all:
        import pandas as pd
        close = pd.read_csv(DATA / "btc_usd_daily_full.csv", parse_dates=["date"]).set_index("date")["close"]
        age = (dt.date.today() - close.index[-1].date()).days
        check(age <= 2, f"price data fresh (last bar {close.index[-1].date()})", f"{age} days old — run quant")
        check(close.index.is_monotonic_increasing, "dates sorted ascending")
        check((pd.to_numeric(close, errors="coerce") > 0).all(), "all closes positive")
        check(close.index.is_unique, "no duplicate dates")
        gaps = pd.date_range(close.index[100], close.index[-1], freq="D").difference(close.index[100:])
        check(len(gaps) == 0, "no missing days after warmup", f"{len(gaps)} gaps")

        # recompute the equal-weight blend from configs and compare to master_blend.json
        mb = load_json(DATA / "master_blend.json")
        ps = load_json(DATA / "pillar_scores.json")
        ss = scores["score_sets"][mb["score_set"]]["P"]
        impact = settings["impact"]
        n_pillars = len(scores["pillars"]) + 1                       # +1 for the quant pillar
        check(mb["n_pillars"] == n_pillars, "stored n_pillars matches config", str(mb.get("n_pillars")))
        ok_all, calls_ok = True, True
        exact_masters = {}
        for h in GRID:
            sigs = [signal(ss[nm][str(h)], scores["pillars"][nm]["quality"][str(h)], impact)
                    for nm in scores["pillars"]]
            sigs.append(ps["windows"][LBL[h]]["signal"])            # quant pillar, equal member
            exact_masters[h] = sum(sigs) / n_pillars
            if abs(round(exact_masters[h], 2) - mb["windows"][LBL[h]]["master"]) > 0.006:
                ok_all = False
            if call(exact_masters[h]) != mb["windows"][LBL[h]]["call"]:
                calls_ok = False
        check(ok_all, "stored masters match equal-weight recompute (±0.006)")
        check(calls_ok, "stored window calls match bands at EXACT values")
        fw2 = settings["final_weights"]
        fin_ok, fincall_ok = True, True
        for name, w in fw2.items():
            exact_final = sum(w[str(h)] * exact_masters[h] for h in GRID)
            if abs(round(exact_final, 2) - mb["final_number"][name]["value"]) > 0.006:
                fin_ok = False
            if call(exact_final) != mb["final_number"][name]["call"]:
                fincall_ok = False
        check(fin_ok, "BOTH final numbers (equal + horizon) match exact recompute")
        check(fincall_ok, "final-number calls match bands at exact values")
        # EQUAL-WEIGHT STRUCTURAL GUARDS (added after the owner caught the old
        # sleeve model giving the quant pillar an undisplayed 50% weight):
        check(abs(mb["weight_each"] * mb["n_pillars"] - 1.0) < 1e-6,
              "weight_each × n_pillars == 1 (true equal weight)")
        check(mb.get("model") == "equal-weight", "blend model is equal-weight", str(mb.get("model")))
        check(ps["impact"] == settings["impact"],
              "quant pillar uses the same uniform impact as everyone", f"{ps.get('impact')} vs {settings['impact']}")
        loo = mb.get("leave_one_out_final_equal", {})
        check(set(loo) == set(scores["pillars"]) | {"Bitcoin TA"}, "leave-one-out covers every pillar")
        ew = settings["final_weights"]["equal"]
        loo_ok = True
        for drop in loo:
            wm = []
            for h in GRID:
                vals = [signal(ss[nm][str(h)], scores["pillars"][nm]["quality"][str(h)], impact)
                        for nm in scores["pillars"] if nm != drop]
                if drop != "Bitcoin TA":
                    vals.append(ps["windows"][LBL[h]]["signal"])
                wm.append(sum(vals) / (n_pillars - 1))
            if abs(round(sum(ew[str(h)] * m for h, m in zip(GRID, wm)), 2) - loo[drop]) > 0.006:
                loo_ok = False
        check(loo_ok, "leave-one-out values match recompute")
        # quant P respects the honesty cap
        cap = settings["quant"]["honesty_cap"]
        check(all(50 - cap <= ps["windows"][LBL[h]]["P"] <= 50 + cap for h in GRID),
              f"quant P within honesty cap 50±{cap}")

    print("== reports ==")
    cur = REPORTS / "current"
    EXPECTED = {"00_START_HERE.html", "CoinPicks_Master_Direction_Report.html",
                "CoinPicks_Bitcoin_TA_Quant_Pillar_Report.html",
                "CoinPicks_CLARITY_Act_Pillar_Report.html", "CoinPicks_Iran_War_Pillar_Report.html",
                "CoinPicks_Tokenization_RWA_Pillar_Report.html", "CoinPicks_Fed_Macro_Pillar_Report.html"}
    htmls = list(cur.glob("*.html")) if cur.exists() else []
    names = {h.name for h in htmls}
    check(EXPECTED <= names, "all 7 expected report sources present", f"missing {EXPECTED - names}")
    for h in htmls:
        t = h.read_text(encoding="utf-8")
        check("{{" not in t.replace("{{CHART_", ""), f"{h.name}: no unknown placeholders")
    # stamp-status guard: every report's decision-stamp div must agree with the
    # ACTUAL status field in config/scores.json for the active set. Added after
    # a real incident (2026-09-05): a daily cycle wrote "COMMITTED —
    # AUTO-STAMPED" into every report's stamp div (class="stamp", the
    # committed/green style) and its own commit message, but never actually
    # flipped active_qual_set's status field from "draft" -- an execution-order
    # bug that six reports and a commit message all echoed without ever
    # touching the source of truth. Caught that time only by luck, because a
    # full weekly refresh happened to run the same day and cross-checked it.
    # House style ties status to CSS class: class="stamp" (green) means
    # committed, class="stamp pending" (amber) means draft — see
    # `.decision .stamp` / `.decision .stamp.pending` in any report's <style>.
    import re
    stamp_re = re.compile(r'class="stamp( pending)?"')
    active_status = scores["score_sets"].get(active, {}).get("status") if active in scores.get("score_sets", {}) else None
    if active_status is not None:
        for h in htmls:
            if h.name == "00_START_HERE.html":
                continue  # summary page, no decision-stamp div of its own
            t = h.read_text(encoding="utf-8")
            m = stamp_re.search(t)
            check(m is not None, f"{h.name}: has a decision-stamp div")
            if m:
                claims_committed = m.group(1) is None
                if active_status == "committed":
                    check(claims_committed, f"{h.name}: stamp div matches committed status",
                          "report shows a pending/draft stamp (class=\"stamp pending\") but "
                          "config/scores.json says this set is committed")
                else:
                    check(not claims_committed, f"{h.name}: stamp div matches draft status",
                          "report shows a committed stamp (class=\"stamp\") but "
                          "config/scores.json's status field for this set is still \"draft\" — "
                          "the report is claiming a stamp that was never actually written")

    # prose-consistency guard: built master/START_HERE must quote the current final number
    build = REPORTS / "current" / "build"
    if build.exists() and (DATA / "master_blend.json").exists():
        mb = load_json(DATA / "master_blend.json")
        fe = f"{mb['final_number']['equal']['value']:+.2f}"
        for name in ("CoinPicks_Master_Direction_Report.html", "00_START_HERE.html"):
            b = build / name
            if b.exists():
                check(fe in b.read_text(encoding="utf-8"),
                      f"built {name} quotes current final number {fe}",
                      "report prose is stale — update reports/current and re-render")

    return finish()


def finish() -> int:
    n_ok = sum(1 for ok, _ in results if ok)
    print(f"\n{'ALL CHECKS PASS' if n_ok == len(results) else 'PROBLEMS FOUND'} ({n_ok}/{len(results)})")
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(run_all())
