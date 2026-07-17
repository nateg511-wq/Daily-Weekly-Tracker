# Market Direction Bot (a CoinPicks system)

A self-contained crypto market-direction research app: five scored pillars
(CLARITY Act, Iran war risk, RWA tokenization, Fed & macro, and a fully-computed
Bitcoin TA pillar) blended into a master table and **one final direction number**,
published as polished HTML/PDF reports.

**New here? Open `00_READ_ME_FIRST.md` first** — it's a short human tour that walks you
into the code and the judgment behind the number, so you can decide whether to trust it
instead of taking it at face value.

## Quickstart

```bash
./setup.sh                        # one-time: venv + dependencies (Python 3.10+)
./.venv/bin/python run.py all     # full cycle: data -> scores -> blend -> PDFs
./.venv/bin/python run.py status  # the master table + final number
```

Reports land in `reports/current/pdf/` (start with `00_START_HERE.pdf`).

## Operating it with an AI

Open this folder in Claude Code (or any AI coding agent) and say
"run the update cycle per the runbook". The agent reads **CLAUDE.md / AGENTS.md**
— the complete operator runbook: quant refresh is one command; the four
qualitative pillars need fresh research + score re-rates in `config/scores.json`
under strict sourcing rules; then blend, render, verify, archive.

The deterministic core (data, indicators, scoring, blending, charts, PDFs) is
pure Python — no AI required. AI is only needed for the qualitative research and
report prose.

## Guarantees this system makes

- Every score change is lineaged (dated score sets; old sets never edited).
- Draft vs owner-committed scores are always labeled.
- Formulas, bands, caps, and known limitations are printed in the reports and
  enforced by `run.py selfcheck`.
- Everything regenerates from `run.py all` + the two config files.

Research & education. Not financial advice.
