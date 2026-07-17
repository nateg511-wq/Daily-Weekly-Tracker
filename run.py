#!/usr/bin/env python3
"""CoinPicks Direction System — single entrypoint.

Usage:
  python run.py all              full cycle: quant -> blend -> render
  python run.py quant            fetch data + indicators + levels + score + cycle + mapping + charts
  python run.py blend [--set S]  master blend + THE FINAL NUMBER (S = a score set in config/scores.json)
  python run.py render           build report HTMLs (chart tokens) + PDFs
  python run.py archive [LABEL]  snapshot reports/current + data JSONs to reports/archive/<date>/
  python run.py numbers          compact digest of every current number (for report writing)
  python run.py status           print the latest master table without recomputing
  python run.py selfcheck        verify environment, config, math invariants, data freshness
  python run.py history          rebuild the Final Number time series from reports/archive/
Options:
  --force-altcoins               refetch the altcoin basket even if refreshed today
"""
from __future__ import annotations

import sys
import traceback

REQUIRED = ("pandas", "numpy", "matplotlib", "mplfinance")


def check_env() -> None:
    missing = []
    for m in REQUIRED:
        try:
            __import__(m)
        except ImportError:
            missing.append(m)
    if missing:
        print(f"Missing packages: {', '.join(missing)}\n"
              f"Fix: ./setup.sh   (or: pip install -r requirements.txt)", file=sys.stderr)
        sys.exit(2)
    if sys.version_info < (3, 10):
        print(f"Python 3.10+ required (found {sys.version.split()[0]})", file=sys.stderr)
        sys.exit(2)


def quant(force_altcoins: bool = False) -> None:
    from engine import charts, cycle, fetch, indicators, levels, mapping, score
    print("[1/7] fetch");      fetch.run(force_altcoins=force_altcoins)
    print("[2/7] indicators"); indicators.run()
    print("[3/7] levels");     levels.run()
    print("[4/7] score");      score.run()
    print("[5/7] cycle");      cycle.run()
    print("[6/7] mapping");    mapping.run()
    print("[7/7] charts");     charts.run()


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    cmd = args[0] if args else "help"
    if cmd == "help":
        print(__doc__)
        return 0
    check_env()

    from engine import blend as blend_mod
    from engine import render as render_mod
    from engine.common import ensure_dirs
    ensure_dirs()

    try:
        if cmd == "all":
            quant("--force-altcoins" in flags)
            print("[blend]");  blend_mod.run()
            print("[render]"); render_mod.render_pdfs()
        elif cmd == "quant":
            quant("--force-altcoins" in flags)
        elif cmd == "blend":
            score_set = None
            if "--set" in sys.argv:
                i = sys.argv.index("--set")
                if i + 1 >= len(sys.argv):
                    print("usage: run.py blend --set <score_set_name>  (see config/scores.json)", file=sys.stderr)
                    return 1
                score_set = sys.argv[i + 1]
            blend_mod.run(score_set=score_set)
        elif cmd == "render":
            render_mod.render_pdfs()
        elif cmd == "archive":
            render_mod.archive(args[1] if len(args) > 1 else None)
            from engine import history as history_mod
            history_mod.run()
        elif cmd == "history":
            from engine import history as history_mod
            for r in history_mod.run():
                print(f"  {r['date']}  final(eq) {r['final_equal']:+.2f}  final(hz) {r['final_horizon']:+.2f}  "
                      f"[{r['score_set']}]")
        elif cmd == "numbers":
            from engine.digest import print_digest
            print_digest()
        elif cmd == "status":
            from engine.digest import print_status
            print_status()
        elif cmd == "selfcheck":
            from tests.selfcheck import run_all
            return run_all()
        else:
            print(__doc__)
            return 0 if cmd == "help" else 1
    except Exception:
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
