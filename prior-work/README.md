# prior-work — frozen history (read-only)

This folder is **archive only**. Nothing here runs, is maintained, or is part of the live
system. The live Market Direction Bot is everything in the parent folder (`run.py`,
`engine/`, `config/`, `reports/`). If you are an AI operator: **do not edit, import, or run
anything under `prior-work/`** — it exists purely so a human can see where the system came
from and what it has produced.

## What's in here

### `finished-report-packages/`
The polished report bundles delivered on each dated cycle, kept exactly as shipped:

- `Pillar Reports 2026-06-19/` — the original hand-authored pillar reports (June baseline).
- `Master Report 2026-07-08/` — first fully-blended package: master report + TA quant
  pillar + the four July-8 pillar updates + the June originals, with its own README.
- `Master Report 2026-07-10/` — the July-10 package that introduced THE FINAL NUMBER and
  full score lineage; the current live app was built from this.
- `Pillar Reports 2026-07-08/`, `Pillar Reports 2026-07-10/` — the standalone dated pillar
  sets those packages drew from.

These are frozen snapshots. The *current* versions of the same reports are generated live
by the app into `../reports/current/pdf/`.

### `original-prototype (BTC-TA)/BTC-TA/`
The very first version of the technical-analysis engine, written as a loose collection of
scripts before it was refactored into the clean `engine/` package. Kept because it's the
most honest way to see how the scoring evolved — the raw `score.py`, `cycle_analysis.py`,
`crash_model_v2.py` (the crash model that **failed** out-of-sample and was deliberately
excluded), `downside_map.py`, etc. If you want to understand *why* the live system is built
the way it is, this is the before-picture. It is superseded in every way by the parent app.

## Why keep it?

Two reasons, both about trust: (1) the finished packages are proof of what the system
actually produces over time, and (2) the prototype shows the messy real work behind the
clean number — including a model that was tested and thrown out. A system you can watch
being built is a system you can decide to trust. That's the whole point (see
`../00_READ_ME_FIRST.md`).
