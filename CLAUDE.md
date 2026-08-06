# Market Direction Bot — Operator Runbook (a CoinPicks system)

You are operating a crypto market-direction research system. This folder is fully
self-contained: everything you need is here, and nothing depends on any prior
conversation. Read this file top to bottom before your first run.

## FIRST INTERACTION — greet the human, then push them to look inside

If this is the start of a session (the human's first message is a greeting, "what is
this?", "help", or anything showing they just opened the folder), do this BEFORE anything
else — do not wait to be asked:

1. Greet them and summarize in ~3 sentences: *this is Market Direction Bot — it scores five
   forces that move Bitcoin (a crypto law in Congress, Iran war risk, RWA tokenization, the
   Fed, and Bitcoin technical analysis) on one standard, blends them, and produces a single
   direction number from −10 to +10, published as PDF reports.*
2. Point them to **`00_READ_ME_FIRST.md`** and to `reports/current/pdf/00_START_HERE.pdf`.
3. **Offer the guided tour** and mean it: *"Want me to walk you through how this actually
   works — open the scoring code, the human-judgment file, and the honesty caps so you can
   decide whether to trust it, instead of taking the number at face value?"* If they say
   yes, open each file in the tour list inside `00_READ_ME_FIRST.md` one at a time, explain
   it in plain language, show the exact math, and invite them to disagree and change it.

The whole philosophy of this system is **don't trust the number, interrogate it.** Your job
on first contact is to make the human open the hood, not to hand them a verdict.

## Owner & cadence

The owner is **Alex (CoinPicks)**. Stamping is normally owner-only (see Stamping
below) — but as of **2026-08-06** Alex has granted standing authority to
auto-stamp daily runs; see "Delegated auto-stamp authority" under Stamping.
Default cadence: **weekly**, or ad-hoc when a trigger fires; the owner may ask for daily.
Deliver finished PDFs from `reports/current/pdf/` to the owner (start with 00_START_HERE.pdf).
All dates/stamps use the owner's local date (US Eastern) in YYYY-MM-DD.

## What this system produces

Five research "pillars" — four qualitative (CLARITY Act legislation, Iran war risk,
RWA tokenization, Fed & macro) and one quantitative (Bitcoin technical analysis,
fully computed) — each scored on the same standard, blended into a master table
and ONE FINAL NUMBER. Outputs are polished HTML/PDF reports in `reports/current/`
that the owner reads and shares.

**The scoring standard (never change it):** every pillar answers, on five windows
(1mo / 3mo / 6mo / 1yr / 3yr): **P** = odds 0–100 this force is *good for crypto* by
then (50 = coin flip) · **Quality** = evidence trustworthiness 0–1 · **Impact** = how
hard it moves the whole market — a single **uniform value (8)** shared by every pillar,
set in `config/settings.json`. **Signal = ((P − 50) ÷ 50) × Quality × Impact** (range ±10).
Call bands on |signal|: <0.5 Neutral · <1.5 Mild · <3 Bull/Bear · <5 Strong · else Very
Strong. **EQUAL WEIGHT:** the master for each window is the *simple mean of ALL pillar
signals* — the qualitative pillars plus the computed Bitcoin-TA pillar, each counting 1/N
(currently 20% of five). Add a pillar and it auto-rebalances; there is no per-pillar weight
and no qual/quant split to tune. The FINAL NUMBER is the equal-weight mean of the five master
window signals (a horizon-weighted variant, and a leave-one-out robustness check, are always
reported beside it).

## First run on a new machine

```bash
./setup.sh                       # creates .venv, installs deps (needs Python 3.10+, internet)
./.venv/bin/python run.py selfcheck
./.venv/bin/python run.py all    # data refresh -> scores -> blend -> PDFs
```
PDFs need Chrome/Chromium/Edge installed; without one you still get HTML.
Windows: run `python -m venv .venv && .venv\Scripts\pip install -r requirements.txt`
then `.venv\Scripts\python run.py all`.

## The update cycle (daily or weekly — same steps)

### Step 1 — Quant refresh (fully automatic)
```bash
./.venv/bin/python run.py quant
./.venv/bin/python run.py numbers   # digest of every current figure
```
This fetches prices incrementally, recomputes all indicators/scores/charts, and
produces the quant pillar's draft P automatically. You never hand-edit quant scores.

### Step 2 — Qualitative research (your judgment, strict rules)
Research each of the four pillars for what changed since the previous score set
(see `note` fields and dates in `config/scores.json`, and each report's
"What Changed" section). **Research discipline — these are hard rules:**
- Prefer PRIMARY sources: federalreserve.gov, congress.gov / the Senate schedule,
  bls.gov, dol.gov, treasury.gov, federalregister.gov, CENTCOM releases, exchange
  APIs, rwa.xyz, prediction-market APIs. Then 2+ independent outlets.
- Date every fact. **Label anything single-source as single-source, in the report text.**
- Never present a market price (Polymarket/Kalshi/analyst-cited odds) as an
  institutional estimate, or vice versa. Note which it is.
- Each pillar report has a **trigger table** — check what fired since last time;
  fired triggers drive the re-rates and get logged in "What Changed".
- Check the previous report's facts still hold; correct anything stale.

### Step 3 — Re-rate the qualitative scores
Add a NEW dated score set in `config/scores.json` (copy the latest one, change
the values, set `"status": "draft"`, write a one-line `note`), then point
`active_qual_set` at it. Rules:
- Key format: `YYYY-MM-DD_draft`. Second run the same day BEFORE delivery: you may
  amend your own same-day, not-yet-delivered draft in place. After delivery, or on
  a new day, always create a new set ( `YYYY-MM-DD_draft2` if the key collides).
- "Old" = any set from a delivered cycle or any committed set — those are never
  edited (single exception: stamping, below). Lineage is sacred.
- Move P only as far as evidence moved — a few points per cycle is typical.
  Keep a one-line rationale per changed window (goes in the report's What Changed).
- **Sufficiency rule:** a single-source claim may be REPORTED (labeled) but may
  not, by itself, move a P. Re-rates need a primary source or 2+ independents.
- Do NOT change a pillar's Quality, the uniform Impact (settings.json), or the
  equal-weight model without an explicit owner decision. There are no per-pillar
  weights to change (every pillar is 1/N by design). If the owner does change the
  uniform Impact, note that recompute-checks against pre-change archives will differ.
- If you have NO web research capability, do NOT invent a new score set — run the
  quant refresh only, keep the previous qualitative set, and say so in the report.

**Stamping:** stamping = editing the set IN PLACE to `"status": "committed"`
plus `"stamped_by": "<owner>"`. The `status` field is authoritative; a `_draft`
key suffix is historical naming, never rename keys. `status` and `stamped_by`
are the ONLY fields ever edited on an existing set.

**Delegated auto-stamp authority (as of 2026-08-06):** Alex has asked that
DAILY light-touch runs auto-stamp themselves — no separate manual approval
step. For a daily run only, after Step 6 (render/selfcheck/verify) passes
clean, stamp the new set in the same pass: set `"status": "committed"` and
`"stamped_by": "Alex (auto-stamped)"` — the `(auto-stamped)` suffix is
mandatory so the lineage honestly shows which commits a human actually
reviewed versus which were self-approved by the pipeline; never write plain
`"Alex"` for an auto-stamped set. This delegation covers ordinary daily
re-rates only. Do NOT auto-stamp, and instead leave the set as `"draft"` and
flag it prominently for Alex's manual review, if any of the following hold:
- it's a **full weekly refresh**, not a light daily touch;
- any pillar's P moved by **more than ~8 points** on any window in one cycle;
- the equal-weight FINAL NUMBER's **call band flips** (e.g. Bear→Neutral,
  Neutral→Mild Bull) versus the last stamped set;
- the change rests on a **single-source claim**, a claim you're materially
  unsure about, or a genuinely novel/ambiguous situation not clearly covered
  by the Research Discipline rules;
- verification (Step 6) surfaces any inconsistency you can't fully resolve.
When in doubt, leave it as a draft and say why — auto-stamp authority is for
routine, well-evidenced moves, not a blanket license to skip judgment.

### Step 4 — Blend
```bash
./.venv/bin/python run.py blend     # prints the master table + THE FINAL NUMBER
```

### Step 5 — Update the reports (`reports/current/*.html`)
Edit each pillar report to reflect the research; update the master report and
START_HERE with the new blend numbers. House rules:
- Keep the existing HTML template/CSS exactly; edit content only.
- Every date stamp moves to today (runfoot, cover "Updated & Re-verified",
  decision stamp "UPDATED DRAFT — <DATE> · AWAITING MY STAMP").
- The scores table shows the FULL LINEAGE: one column per set = the last
  committed set + every draft issued since that commit (when the owner commits,
  earlier drafts collapse out of the table — they remain in scores.json forever).
- Glossary: "runfoot" = the footer line (CSS `.runfoot`); the "decision stamp" =
  the `.decision .stamp` div; the cover info line = `.infobox .m`. PROVENANCE
  dates ("Written ...", "committed ...") never change — only Updated/Re-verified,
  runfoot, and stamp dates move to today.
- Sections (house order): cover · Scores · The Claim · The Facts (dated, sourced)
  · The Prize · The Other Side (strongest honest bear case) · The Triggers (dated,
  falsifiable, with a flip line) · My Decision · What Changed · Sources.
- The TA report keeps its `{{CHART_*}}` tokens — `run.py render` substitutes them.
- Numbers in prose must match `run.py numbers` / `run.py status` EXACTLY.
  Field checklist per report — update ALL of these: BTC price (cover infobox +
  facts + any claim prose), the five master signals and calls (master table,
  START_HERE table, story bullets), THE FINAL NUMBER (master cover box +
  START_HERE box + decision line), each pillar's P row + signal column + lineage
  line, trigger-table levels, and every date stamp. `run.py selfcheck` verifies
  the built master/START_HERE quote the current final number — it does NOT check
  every figure, so sweep manually.

### Step 6 — Render, verify, archive
```bash
./.venv/bin/python run.py render
./.venv/bin/python run.py selfcheck
```
Then VERIFY like money depends on it (it does) — and only ARCHIVE after
verification passes (`./.venv/bin/python run.py archive`); if verification forced
changes, re-render, re-selfcheck, and archive then. Archives never overwrite:
a same-date snapshot gets a `-2` suffix. Archives are permanent — never prune
them; pass a label (`run.py archive 2026-07-10-fixup`) when a date needs context.
Verification list:
1. Recompute a couple of signals by hand from the formula; spot-check them in the PDFs.
2. Re-open each changed report and check every new fact against its source once more.
3. Cross-check: the same fact quoted in two reports (BTC price, oil, odds) must
   match or carry an explicit basis label.
4. Check the PDFs page by page for rendering breakage.
If you have subagent capability, run independent adversarial verification of the
new claims (primary sources, not the report's own citations) before delivering.

## Honesty rules baked into this system (do not soften)

- The quant pillar's P is capped at 50 ± 25 (config) because measured TA edge is
  modest; a 5-feature crash model FAILED out-of-sample (AUC 0.44) and stays excluded.
- Cycle-analog claims rest on n=3 completed cycles; single windows flip when
  alignment shifts days — direction is the signal, levels are soft. Say so.
- Current weekly/monthly/quarterly bars are PARTIAL; completed-bar composites are
  computed and must be quoted alongside (see `run.py numbers`).
- The power-law fair value swings with the fit window (sensitivity is computed);
  quote it as a range/scenario bound, not a target.
- Froth data lags ~6 weeks — tilt, not score input.
- Drafts are drafts: only the owner stamps scores. Never relabel a draft as committed.

## Layout

```
00_READ_ME_FIRST.md    human onboarding — the "look inside before you trust it" tour
run.py                 CLI (all/quant/blend/render/archive/numbers/status/selfcheck)
config/scores.json     qualitative P score sets + pillar meta  <- what you edit
config/settings.json   engine knobs (uniform impact, final-number window weights, quant mapping)
engine/                the pipeline (fetch, indicators, levels, score, cycle,
                       mapping, blend, charts, render, digest, common)
data/                  CSV/JSON state (regenerated; safe to delete except the
                       *.csv caches, which just make the next fetch slower)
charts/                generated PNGs
reports/current/       report HTML sources (edit) + build/ + pdf/ (generated)
reports/archive/       dated snapshots (run.py archive)
tests/selfcheck.py     health + math-invariant checks
prior-work/            FROZEN HISTORY — past report packages + the original prototype.
                       Read-only reference; nothing here runs or is maintained. The live
                       system is everything OUTSIDE prior-work. Do not edit or import it.
```

## Troubleshooting

- `run.py selfcheck` first — it names the problem.
- Fetch failures: Bitstamp/Coin Metrics/GitHub occasionally rate-limit; the fetcher
  retries with backoff. Rerun later if it still fails; caches mean no data loss.
- Stale altcoin/froth data is EXPECTED (~6-week lag) and disclosed in reports.
- No PDFs: install Chrome/Chromium; HTML in `reports/current/build/` still works.
- A fresh machine with an empty `data/` does a full ~5-minute Bitstamp history
  fetch once; afterwards everything is incremental.
