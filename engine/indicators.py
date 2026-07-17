"""Formulaic indicators on weekly / monthly / quarterly bars.

Stack: SMA 20/50/200, EMA 12/26, RSI-14 (Wilder), MACD 12/26/9,
Bollinger 20/2, OBV. Support/Resistance and trendlines live in levels.py.

Convention: weekly bars close Sunday (W-SUN); monthly/quarterly are calendar.
The current bar of each timeframe is PARTIAL until it closes — downstream
scoring uses bars as-is and separately reports completed-bar composites.

Input : data/btc_usd_daily_full.csv
Output: data/indicators_{weekly,monthly,quarterly}.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .common import DATA, log

TIMEFRAMES = {"weekly": "W-SUN", "monthly": "ME", "quarterly": "QE"}


def load_daily() -> pd.DataFrame:
    df = pd.read_csv(DATA / "btc_usd_daily_full.csv", parse_dates=["date"]).set_index("date").sort_index()
    for c in ["open", "high", "low", "close", "volume_btc"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume_btc": "sum"}
    return df.resample(rule).agg(agg).dropna(subset=["close"])


def wilder(series: pd.Series, n: int) -> pd.Series:
    """Wilder's smoothing == EMA with alpha = 1/n."""
    return series.ewm(alpha=1 / n, adjust=False).mean()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    c, v = df["close"], df["volume_btc"]

    for n in (20, 50, 200):
        df[f"sma{n}"] = c.rolling(n).mean()
    df["ema12"] = c.ewm(span=12, adjust=False).mean()
    df["ema26"] = c.ewm(span=26, adjust=False).mean()

    delta = c.diff()
    up, down = delta.clip(lower=0), -delta.clip(upper=0)
    rs = wilder(up, 14) / wilder(down, 14)
    df["rsi14"] = 100 - 100 / (1 + rs)

    df["macd"] = df["ema12"] - df["ema26"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    mid = c.rolling(20).mean()
    sd = c.rolling(20).std(ddof=0)
    df["bb_mid"], df["bb_upper"], df["bb_lower"] = mid, mid + 2 * sd, mid - 2 * sd
    df["bb_pctb"] = (c - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / mid

    df["obv"] = (np.sign(c.diff()).fillna(0) * v.fillna(0)).cumsum()
    return df


def run() -> None:
    daily = load_daily()
    for name, rule in TIMEFRAMES.items():
        df = add_indicators(resample(daily, rule))
        path = DATA / f"indicators_{name}.csv"
        df.round(6).to_csv(path)
        r = df.iloc[-1]
        log(f"indicators: {len(df):>4} {name:9} bars -> {path.name}  "
            f"(bar {df.index[-1].date()}, close ${r['close']:,.0f}, RSI {r['rsi14']:.1f})")
