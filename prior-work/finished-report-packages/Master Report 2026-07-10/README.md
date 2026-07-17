# CoinPicks Master Package — July 10, 2026 (FINAL)

Everything current as of **July 10, 2026** (BTC $63,987). This folder is self-contained and shareable.

## THE FINAL NUMBER: **+0.66 — Mild Bull, time-arbitraged** (scale −10…+10)

Equal-weight mean of the five window signals; horizon-weighted variant **+1.13**. The structure underneath:

| Window | Master | Call |
|---|---|---|
| 1 month | −0.97 | **Mild Bear** |
| 3 months | −0.70 | **Mild Bear** |
| 6 months | +0.16 | **Neutral** |
| 1 year | +2.12 | **Bull** |
| 3 years | +2.67 | **Bull** |

Positive overall because the far windows outweigh the near ones — **not** a buy-today signal. Calls identical at every blend mix tested (60/40, 50/50, 40/60; final number +0.53 to +0.78, all Mild Bull).

## Contents

- `00_START_HERE.pdf` — two-page cover: the number, the table, reading order, the method, honesty notes.
- `CoinPicks_Master_Direction_Report.pdf` — the summary deliverable (final number, matrix, agreements, trigger calendar, sensitivity).
- `CoinPicks_Bitcoin_TA_Quant_Pillar_Report.pdf` — the quant pillar (charts; data through Jul 10; P 39/38/44/67/70).
- `Pillar Reports (updated 2026-07-10)/` — CLARITY, Iran, Tokenization, Fed & Macro (PDF + HTML), each with full score lineage June → Jul 8 → Jul 10 and fresh sources.
- `Prior versions (June 19 + July 8, for the record)/` — every earlier report, untouched.
- `master_blend.py` / `master_blend.json` — the engine (scoresets: june_committed / july8_draft / july10_draft; FINAL_WEIGHTS defines the final number).

## July 10 draft P lineage (all awaiting Alex's stamp)

| Pillar | June | Jul 8 | **Jul 10** | What moved it Jul 8→10 |
|---|---|---|---|---|
| CLARITY (25%·I9) | 55/60/65/85/92 | 52/56/61/83/92 | **50/54/60/82/92** | Odds fell (Polymarket ~40%, Kalshi EOY ~35¢); ethics frozen; WH not signed off on the imminent merged text |
| Iran (25%·I7) | 50/55/62/75/85 | 40/47/55/70/83 | **42/49/56/70/83** | ~170 targets struck with zero US casualties; oil FELL; Tehran asked to keep talking — performative war |
| Tokenization (30%·I8) | 53/57/62/72/85 | 52/56/62/73/85 | **53/58/64/74/85** | Treasuries growth resumed ($15.16B); DTCC Russell-1000 pilot this month, full launch Oct; BUIDL +6% |
| Fed & Macro (25%·I9) | 38/40/46/54/61 | 35/36/42/52/61 | **34/36/44/53/61** | Hawkish minutes (easing bias dropped) but reserves +$132B w/w on TGA spend-down; claims steady |
| Bitcoin TA (computed) | — | 37/37/46/67/70 | **39/38/44/67/70** | +2.8% bounce reclaimed the 200-week MA (unconfirmed); 6mo analog flipped 1/3→0/3 (n=3 fragility, disclosed) |

Quality/Impact/weights unchanged throughout.

## Verification (July 10 — five layers)

1. **Math:** full chain recomputed independently from raw CSVs (31/31 exact — composites, P values, signals, blend, final number).
2. **Writers verified:** four adversarial verifiers on the updated reports — zero blockers (5 minor wordings, fixed).
3. **Forensic audit:** July 8 build audited at 243 claims vs primary sources (all corrections applied); July 10 deltas re-audited on top (see audit note in each report's What Changed).
4. **Visual:** every PDF page rendered and inspected.
5. **Regression sweep:** date stamps, lineage lines, and prior-audit corrections verified present in final PDFs.

Research discipline: primary sources first (Fed releases, Senate schedule, DOL, H.4.1, exchange + prediction-market APIs); single-source items labeled in-line; market prices never presented as institutional estimates.

## To stamp / re-rate / regenerate

1. Override any P in `master_blend.py` (`july10_draft` block) → re-run → the table and final number recompute. Flip `SCORESET` to reproduce any earlier state.
2. Quant refresh: run the BTC-TA pipeline (order in the TA report's Method section), then `pillar_mapping.py`, then `master_blend.py`.
3. Re-render PDFs: `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu --no-pdf-header-footer --print-to-pdf=OUT.pdf file:///path/to.html`

## The falsifiable part (next 6 weeks)

CPI Jul 14 · Iran oil-waiver + NCUA comments Jul 17 · GENIUS rules deadline Jul 18 · CLARITY cloture tell ~Jul 20–24 · FOMC Jul 28–29 · Senate recess Aug 7 · MoU expiry ~Aug 16 · avg cycle-bottom month ~Aug 30 · TA levels $58,526 / $64,432 / ~$69.9K. Each pillar's trigger table states in advance what each outcome does to the scores.
