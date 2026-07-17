#!/usr/bin/env python3
"""
Render one annotated BTC/USD chart per timeframe (monthly/weekly/daily):
candles + SMA20/50/200 + Bollinger + S/R lines + trendlines, with RSI, MACD
and volume sub-panels. Title carries the overall verdict from score.py.

Output: charts/btc_{daily,weekly,monthly}.png
"""
import json
import os
import pandas as pd
import mplfinance as mpf
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CH = os.path.join(HERE, "charts")
os.makedirs(CH, exist_ok=True)

WIN = {"weekly": 130, "monthly": 60, "quarterly": 44}
DATEFMT = {"weekly": "%Y-%m-%d", "monthly": "%b %Y", "quarterly": "%b %Y"}
XROT = {"weekly": 30, "monthly": 0, "quarterly": 0}
LABEL = {"weekly": "WEEKLY", "monthly": "MONTHLY", "quarterly": "3-MONTH"}
SIG = json.load(open(f"{DATA}/signals.json"))


def chart(tf):
    df = pd.read_csv(f"{DATA}/indicators_{tf}.csv", parse_dates=["date"]).set_index("date")
    df = df.iloc[-WIN[tf]:].copy()
    o = df.rename(columns={"open": "Open", "high": "High", "low": "Low",
                           "close": "Close", "volume_btc": "Volume"})[
        ["Open", "High", "Low", "Close", "Volume"]]

    aps = []

    def add(col, **kw):
        if col in df and df[col].notna().any():
            kw.setdefault("secondary_y", False)
            aps.append(mpf.make_addplot(df[col], **kw))

    # Main panel overlays
    add("sma20", color="#1f77b4", width=1.0, label="SMA20")
    add("sma50", color="#ff7f0e", width=1.0, label="SMA50")
    add("sma200", color="#9467bd", width=1.3, label="SMA200")
    add("bb_upper", color="#999", width=0.8, linestyle="--", label="BB")
    add("bb_lower", color="#999", width=0.8, linestyle="--")

    # RSI panel (2)
    add("rsi14", panel=2, color="#d62728", width=1.1, ylabel="RSI", ylim=(0, 100))
    for lvl, c in [(70, "#bbb"), (50, "#ddd"), (30, "#bbb")]:
        aps.append(mpf.make_addplot(pd.Series(lvl, index=df.index), panel=2,
                                    color=c, width=0.7, linestyle="--", secondary_y=False))

    # MACD panel (3)
    add("macd", panel=3, color="#1f77b4", width=1.0, ylabel="MACD")
    add("macd_signal", panel=3, color="#ff7f0e", width=1.0)
    hcol = ["#2ca02c" if v >= 0 else "#d62728" for v in df["macd_hist"]]
    aps.append(mpf.make_addplot(df["macd_hist"], panel=3, type="bar", color=hcol,
                                alpha=0.5, secondary_y=False))

    # Horizontal S/R
    lv = pd.read_csv(f"{DATA}/levels_{tf}.csv")
    p = df["close"].iloc[-1]
    res = lv[lv["level"] > p].sort_values("level").head(2)
    sup = lv[lv["level"] <= p].sort_values("level", ascending=False).head(2)
    hl = list(res["level"]) + list(sup["level"])
    hlc = ["#d62728"] * len(res) + ["#2ca02c"] * len(sup)

    # Sloped trendlines (drawn across the visible window via fitted slope)
    tl = pd.read_csv(f"{DATA}/trendlines.csv")
    tl = tl[tl["timeframe"] == tf]
    n, first, last = len(df), df.index[0], df.index[-1]
    alines, acol = [], []
    for _, t in tl.iterrows():
        vfirst = t["value_now"] - t["slope_per_bar"] * (n - 1)
        alines.append([(first, vfirst), (last, t["value_now"])])
        acol.append("#2ca02c" if t["type"] == "support" else "#d62728")

    s = SIG[tf]
    title = (f"BTC/USD   {LABEL[tf]}   {s['date']}   "
             f"{s['overall_intensity']} {s['overall'].upper()}  ({s['composite']:+.0f}/100)")
    style = mpf.make_mpf_style(base_mpf_style="yahoo", gridstyle=":", facecolor="white")

    kw = dict(type="candle", style=style, addplot=aps, volume=True, volume_panel=1,
              panel_ratios=(6, 1.4, 2, 2), figratio=(16, 11), figscale=1.2,
              returnfig=True, tight_layout=True,
              datetime_format=DATEFMT[tf], xrotation=XROT[tf],
              alines=dict(alines=alines, colors=acol, linewidths=1.3, linestyle="--"))
    if hl:
        kw["hlines"] = dict(hlines=hl, colors=hlc, linestyle="-.", linewidths=0.9)

    fig, ax = mpf.plot(o, **kw)
    fig.suptitle(title, y=0.995, fontsize=12, fontweight="bold")
    # breathing room on the right so the latest bars + date labels aren't clipped
    ax[0].set_xlim(-1, len(df) - 1 + max(4, int(len(df) * 0.06)))
    leg = [Line2D([0], [0], color="#1f77b4", label="SMA20"),
           Line2D([0], [0], color="#ff7f0e", label="SMA50")]
    if df["sma200"].notna().any():
        leg.append(Line2D([0], [0], color="#9467bd", label="SMA200"))
    leg += [Line2D([0], [0], color="#999", ls="--", label="Bollinger"),
            Line2D([0], [0], color="#d62728", ls="-.", label="Resistance"),
            Line2D([0], [0], color="#2ca02c", ls="-.", label="Support")]
    ax[0].legend(handles=leg, loc="upper left", fontsize=7.5, ncol=2, framealpha=0.9)
    out = f"{CH}/btc_{tf}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print("saved", out)


for tf in ("quarterly", "monthly", "weekly"):
    chart(tf)
