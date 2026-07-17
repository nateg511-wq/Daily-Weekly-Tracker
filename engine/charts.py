"""Chart rendering: annotated tape charts per timeframe, the halving-cycle
overlay, and the downside map.

Everything on the downside map is COMPUTED from data (no hand-set levels):
cycle-low trigger, Fib golden pocket (61.8–65% retrace of prior-bear low ->
cycle high), power-law −1σ/−2σ bands, the 200-week MA, and the historic
trough zone (−77%/−85% of ATH). Narrative odds live in the reports, not here.

Output: charts/btc_{weekly,monthly,quarterly}.png, charts/halving_cycle.png,
        charts/downside_map.png
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mplfinance as mpf  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .common import CHARTS, DATA, load_json, load_settings, log  # noqa: E402
from .indicators import load_daily  # noqa: E402

WIN = {"weekly": 130, "monthly": 60, "quarterly": 44}
LABEL = {"weekly": "WEEKLY", "monthly": "MONTHLY", "quarterly": "3-MONTH"}


def esc(t: str) -> str:
    """Escape $ so matplotlib doesn't enter mathtext mode on paired dollars."""
    return t.replace("$", "\\$")


def tape_chart(tf: str, sig: dict) -> None:
    ind = pd.read_csv(DATA / f"indicators_{tf}.csv", parse_dates=["date"]).set_index("date")
    lv = pd.read_csv(DATA / f"levels_{tf}.csv")
    tl = pd.read_csv(DATA / "trendlines.csv")
    tl = tl[tl["timeframe"] == tf]

    df = ind.iloc[-WIN[tf]:].copy()
    price = df["close"].iloc[-1]

    def ap(series, **kw):
        """Skip overlays that are entirely NaN in this window (e.g. SMA200 on
        monthly bars when fewer than 200 bars exist) — mplfinance crashes on them."""
        return mpf.make_addplot(series, **kw) if series.notna().any() else None

    aps = [p for p in [
        ap(df["sma20"], color="#1f77b4", width=1.2),
        ap(df["sma50"], color="#ff7f0e", width=1.2),
        ap(df["sma200"], color="#9467bd", width=1.4),
        ap(df["bb_upper"], color="#aaaaaa", width=0.8, linestyle="--"),
        ap(df["bb_lower"], color="#aaaaaa", width=0.8, linestyle="--"),
        ap(df["rsi14"], panel=2, color="#c62828", ylabel="RSI"),
        ap(df["macd"], panel=3, color="#1f77b4", ylabel="MACD"),
        ap(df["macd_signal"], panel=3, color="#ff7f0e"),
        mpf.make_addplot(df["macd_hist"], panel=3, type="bar", color=
                         ["#a5d6a7" if v >= 0 else "#ef9a9a" for v in df["macd_hist"]]),
    ] if p is not None]
    r = sig[tf]
    title = (f"BTC/USD  {LABEL[tf]}  {r['date']}  {r['overall_intensity']} "
             f"{r['overall'].upper()}  ({r['composite']:+.0f}/100)")
    fig, axes = mpf.plot(
        df.rename(columns={"volume_btc": "volume"}),
        type="candle", style="yahoo", volume=True, addplot=aps,
        returnfig=True, figsize=(15, 10.5), panel_ratios=(5, 1, 1, 1),
        datetime_format="%Y-%m-%d", xrotation=30, tight_layout=True,
    )
    ax = axes[0]
    lo, hi = ax.get_ylim()
    for _, row in lv.iterrows():
        if lo <= row["level"] <= hi:
            c = "#b71c1c" if row["type"] == "resistance" else "#1b5e20"
            ax.axhline(row["level"], color=c, ls="-.", lw=0.9, alpha=0.8)
    x0 = df.index[0]
    n = len(df)
    for _, t in tl.iterrows():
        y_now = t["value_now"]
        y0 = y_now - t["slope_per_bar"] * (n - 1)
        c = "#b71c1c" if t["type"] == "resistance" else "#1b5e20"
        ax.plot([0, n - 1], [y0, y_now], color=c, ls="--", lw=1.6, alpha=0.9)
    ax.set_title(title, fontsize=15, fontweight="bold")
    out = CHARTS / f"btc_{tf}.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    log(f"charts: {out.name}  (price ${price:,.0f})")


def halving_chart(cyc: dict, close: pd.Series, halvings: list[pd.Timestamp]) -> None:
    today = close.index[-1]
    fig, ax = plt.subplots(figsize=(13, 7))
    colors = ["#9ca3af", "#60a5fa", "#f59e0b", "#dc2626"]
    labels = [f"C{i+1} ({h.year})" for i, h in enumerate(halvings)]
    for i, (h, c, lab) in enumerate(zip(halvings, colors, labels)):
        end = halvings[i + 1] if i + 1 < len(halvings) else today
        seg = close[(close.index >= h) & (close.index < end)]
        hp = close.asof(h)
        x = [(d - h).days / 30.44 for d in seg.index]
        ax.plot(x, seg.values / hp, color=c, lw=2.6 if i == 3 else 1.4,
                label=lab, alpha=0.95 if i == 3 else 0.8)

    done = cyc["cycles"][:3]
    turns = [r["m_turn"] for r in done if r["m_turn"]]
    t_avg, t_lo, t_hi = float(np.mean(turns)), min(turns), max(turns)
    turn_date = (halvings[-1] + pd.Timedelta(days=t_avg * 30.44)).date()
    cm = cyc["cycle_month"]
    ax.axvspan(t_lo, t_hi, color="#16a34a", alpha=0.10, zorder=0)
    ax.axvline(t_avg, color="#16a34a", ls="--", lw=2.2, zorder=4,
               label=f"projected momentum turn · {turn_date}")
    ax.axvline(cm, color="#dc2626", ls=":", lw=1.7, alpha=0.85, zorder=4)
    ax.scatter([cm], [close.iloc[-1] / close.asof(halvings[-1])], color="#dc2626",
               s=150, zorder=6, marker="o", edgecolor="black", linewidth=1.1,
               label=f"we are here · {today.date()}")
    days_to = (pd.Timestamp(turn_date) - today).days
    ax.text(0.5, 0.97,
            esc(f"≈ {days_to} days to projected momentum turn (point {turn_date}; "
                f"range months {t_lo:.0f}–{t_hi:.0f} from completed cycles, n=3)"),
            transform=ax.transAxes, ha="center", va="top", fontsize=10.5, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.35", fc="#ecfdf5", ec="#16a34a", alpha=0.95))
    ax.set_yscale("log")
    ax.set_xlabel("months since halving")
    ax.set_ylabel("price ÷ price at halving (log)")
    ax.set_title("BTC halving cycles, aligned  (green line = avg 1-yr-momentum turn of completed cycles)")
    ax.legend(loc="lower right", fontsize=8.5, framealpha=0.92)
    ax.grid(True, which="both", ls=":", alpha=0.4)
    ax.set_xlim(0, 50)
    fig.tight_layout()
    fig.savefig(CHARTS / "halving_cycle.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    log("charts: halving_cycle.png")


def downside_chart(cyc: dict, daily: pd.DataFrame, halvings: list[pd.Timestamp]) -> None:
    close = daily["close"]
    cur = close.iloc[-1]
    cycles = cyc["cycles"]
    cur_cycle = cycles[-1]
    ath_close = cur_cycle["top"]
    top_date = pd.Timestamp(cur_cycle["top_date"])

    # computed anchors
    trigger = close[close.index >= top_date].min()                       # cycle-low close
    prev_low = daily["low"][cycles[-2]["bottom_date"]:cur_cycle["top_date"]].min()
    ath_high = daily["high"][cur_cycle["top_date"]:].max()
    ath_high = max(ath_high, daily["high"][:cur_cycle["top_date"]].max())
    pocket_hi = ath_high - 0.618 * (ath_high - prev_low)                 # golden pocket
    pocket_lo = ath_high - 0.650 * (ath_high - prev_low)
    ma200w = close.rolling(1400).mean()
    pl = cyc["powerlaw"]

    fig, ax = plt.subplots(figsize=(13, 7.5))
    r = close[close.index >= top_date - pd.Timedelta(days=500)]
    ax.plot(r.index, r, color="#111", lw=1.5, label="BTC")
    m = ma200w[ma200w.index >= r.index[0]]
    ax.plot(m.index, m, color="#7c3aed", lw=1.5, alpha=0.8, label="200-week MA")
    ax.axhspan(pocket_lo, pocket_hi, color="#86efac", alpha=0.30,
               label=esc(f"Fib golden pocket ${pocket_lo:,.0f}–${pocket_hi:,.0f}"))
    lines = [
        (cur, "#2563eb", "-", f"now  ${cur:,.0f}  ({cur/ath_close-1:+.0%} from ATH close)", "bottom"),
        (trigger, "#0891b2", ":", f"cycle-low close ${trigger:,.0f} — the trigger level", "top"),
        (pl["minus1sd"], "#16a34a", "--", f"power-law −1σ ${pl['minus1sd']:,.0f}", "bottom"),
        (ath_close * 0.23, "#f59e0b", "--", f"historic −77% trough equiv ${ath_close*0.23:,.0f}", "bottom"),
        (ath_close * 0.15, "#dc2626", "--", f"historic −85% trough equiv ${ath_close*0.15:,.0f}", "bottom"),
    ]
    for lvl, c, ls, lab, va in lines:
        if lvl < r.max() * 1.05:
            ax.axhline(lvl, color=c, ls=ls, lw=1.6, alpha=0.95)
            ax.text(r.index[2], lvl, "  " + esc(lab), color=c, va=va, fontsize=8.6, fontweight="bold")
    ax.set_ylim(min(ath_close * 0.13, trigger * 0.9), r.max() * 1.06)
    ax.set_ylabel("BTC price (USD)")
    ax.set_title(esc(f"BTC downside map — computed anchors   (ATH ${ath_close:,.0f} → now ${cur:,.0f})\n"
                     f"Golden pocket, cycle low, power-law bands, and historic troughs — all derived from data; "
                     f"scenario odds live in the report."))
    ax.grid(True, ls=":", alpha=0.4)
    ax.legend(loc="upper right", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(CHARTS / "downside_map.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    log(f"charts: downside_map.png (trigger ${trigger:,.0f}, pocket ${pocket_lo:,.0f}–${pocket_hi:,.0f})")


def run() -> None:
    CHARTS.mkdir(exist_ok=True)
    settings = load_settings()
    halvings = [pd.Timestamp(d) for d in settings["data"]["halvings"]]
    sig = load_json(DATA / "signals.json")
    cyc = load_json(DATA / "cycle.json")
    daily = load_daily()
    for tf in ("weekly", "monthly", "quarterly"):
        # resample for chart uses the indicator csv directly (already resampled)
        tape_chart(tf, sig)
    halving_chart(cyc, daily["close"], halvings)
    downside_chart(cyc, daily, halvings)
