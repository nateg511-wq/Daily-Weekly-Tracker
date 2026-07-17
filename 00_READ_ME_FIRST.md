# READ ME FIRST
## Market Direction Bot — and why you shouldn't trust it until you've looked inside

**You just opened this folder in Claude Code.** The AI has already read the runbook
(`CLAUDE.md`) and knows exactly what this is. Type **"give me the guided tour"** and
it will walk you through the system file by file, opening and explaining each piece.

But read this page first. It's for **you, the human** — and its one job is to talk you
out of trusting the number before you understand it.

---

### What this is, in 60 seconds

This is a crypto **market-direction** system. It weighs five forces that move Bitcoin:

- **Four you have to _judge_** — a crypto law moving through Congress (CLARITY Act),
  Middle-East / Iran war risk, real-world-asset tokenization, and the Fed & macro regime.
- **One it _computes_** straight from the price chart — Bitcoin technical analysis.

It scores each force on the same scale — the odds (0–100) it's *good for crypto* — across
five horizons (1 month → 3 years), blends them, and distills everything to **one number**
from −10 (maximum bearish) to +10 (maximum bullish).

That number is on the cover of **`reports/current/pdf/00_START_HERE.pdf`**. Open it. Then
come back here, because the number is the *least* important thing in this folder.

---

### The one rule: don't trust the number. Interrogate it.

This system was built to be **argued with**, not obeyed. The number is a documented
*opinion*, not an oracle — and every part of it is deliberately openable. This page exists
to make you open it. If you act on the number without doing the short tour below, you are
doing the exact thing this whole system was designed to prevent: **taking an indicator at
face value.**

The promise: **by the end of the 20-minute tour, you'll be able to defend or reject every
number yourself.** If you can't — don't trade on it.

*(One-time setup if you haven't already: run `./setup.sh`, which builds the local Python
environment. Then the commands below work.)*

---

### The 20-minute tour — do this before you rely on anything

Do it by hand, or (better) tell Claude Code: **"Walk me through the tour in READ ME FIRST,
opening each file and explaining it."** Either way, actually open these:

**1. The output — 2 min.** Open `reports/current/pdf/00_START_HERE.pdf`, then
`CoinPicks_Master_Direction_Report.pdf`. Look at the five-window table and the final number.
Now stop admiring it and open the hood.

**2. The human judgment — `config/scores.json` — 4 min.** This is where a *person* set the
odds. Each pillar has a `P` value per window: the odds that force is good for crypto. These
are opinions with dated rationale, and the `score_sets` show how they've moved over time
(committed → draft → draft — a full lineage that never gets rewritten).
> **Ask yourself:** do you actually believe the CLARITY Act is 82% likely to help crypto
> over a year? If not — *change the number and re-run.* It's your call, not the bot's.

**3. The machine's half — `engine/score.py` — 5 min.** This is how a raw indicator becomes
a conviction score. Read the function `s_rsi` (RSI → a −100…+100 number), then `s_macd`,
then the comment inside `s_trend`. There is **no magic** — it's arithmetic you can check by
hand.
> **Ask yourself:** is that how *you'd* turn an oversold RSI into a bullish signal? The
> weights that combine the seven indicators are in `config/settings.json` under
> `indicator_weights`. Disagree? Change them.

**4. The honesty caps — `config/settings.json` — 3 min.** Find `honesty_cap: 25`. The
technical-analysis pillar is *forbidden* from ever claiming odds more than 25 points off a
coin flip, because its real-world predictive edge is modest and the system refuses to
pretend otherwise. Then read the `quality_basis` notes — the system tells you, in writing,
where its own evidence is thin (n=3 cycles, small samples).
> Most "bots" hide their uncertainty. This one prints it. That's the point.

**5. Cross-check reality — 4 min.** Run:
```
./.venv/bin/python run.py numbers
```
It dumps every raw figure it's using — the BTC price, the moving averages, the
support/resistance levels, the cycle math. **Open a chart you trust (e.g. TradingView) and
verify three of them yourself.** If the price or a level is off, the data is stale — find
out why *before* you trust anything built on top of it.

**6. The blend — `engine/blend.py` — 2 min.** See exactly how five pillars become one
number: a plain average — every pillar counts the same 1/N (add a pillar and it auto-rebalances). No neural net. No black box. If you can
read a spreadsheet, you can read this.

---

### The skeptic's checklist — answer these before acting

- **Are the chart bars finished?** They're not — the current week/month/quarter are still
  forming. The reports quote both the live number *and* the completed-bar number. Which one
  are you looking at?
- **Is `n = 3` doing the heavy lifting?** The bullish long-term call leans on only **three**
  past Bitcoin cycles. Three coin-flips landing heads is not a law of nature — and the
  reports say so out loud.
- **What's single-sourced?** Anything the research couldn't confirm twice is labeled
  "single-source" in the pillar reports. Weight it accordingly.
- **How old is the human research?** The *price* refreshes in seconds; the *judgment* is
  only as fresh as the last time someone did the work. Check the dates in `config/scores.json`.

Can't answer all four? You haven't understood it yet. Go back to the tour.

---

### Running your own update

When you want fresh numbers, the complete instructions live in **`CLAUDE.md`** (Claude Code
reads it automatically). The short version: `run.py quant` refreshes all the price-based
math on its own; the four judgment pillars need *you* — or your AI, under strict sourcing
rules — to research what changed and edit `config/scores.json`; then `run.py blend` and
`run.py render`. The runbook spells out every rule, including the big one: **a single news
article is never enough to move a score.**

---

### Where everything is

```
reports/current/pdf/   the finished reports — start with 00_START_HERE.pdf
config/scores.json     the human judgment (P odds per pillar) — the file you edit
config/settings.json   the indicator weights, the honesty caps, the uniform impact
engine/                the code — data, indicators, scoring, blend, charts (all readable)
CLAUDE.md / AGENTS.md   the full operator runbook for any AI
prior-work/            frozen history: past report packages + the original prototype,
                       kept so you can see how it was built and what it has produced.
                       (Read-only. The live system is everything OUTSIDE prior-work.)
```

---

### What this is NOT

- **Not financial advice.** It's a research instrument — probabilities with evidence,
  built to be challenged.
- **Not a black box.** Every number traces to a file you can open and a formula you can check.
- **Not an oracle.** It has a modest, documented edge, and it tells you exactly where it's
  weak. Respect that and it's useful. Obey it blindly and it's dangerous.

**The moment you catch yourself trusting the number without being able to explain it — stop,
and open the folder.**
