#!/usr/bin/env python3
"""
Formulaic indicators for the BTC TA stack, on daily / weekly / monthly.

Final list (formulaic part of the 7-indicator stack):
  Moving Averages (SMA 20/50/200, EMA 12/26), RSI 14, MACD 12/26/9,
  Bollinger Bands 20/2, Volume + OBV.
(Support/Resistance and Trendlines live in levels.py.)

Input : data/btc_usd_daily_full.csv
Output: data/indicators_{daily,weekly,monthly}.csv
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "data", "btc_usd_daily_full.csv")
OUT = os.path.join(HERE, "data")

# Crypto convention: weekly closes Sunday (Monday open); monthly/quarterly = calendar.
TIMEFRAMES = {"weekly": "W-SUN", "monthly": "ME", "quarterly": "QE"}


def load_daily():
    df = pd.read_csv(SRC, parse_dates=["date"]).set_index("date").sort_index()
    for c in ["open", "high", "low", "close", "volume_btc"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def resample(df, rule):
    if rule is None:
        return df[["open", "high", "low", "close", "volume_btc"]].copy()
    agg = {"open": "first", "high": "max", "low": "min",
           "close": "last", "volume_btc": "sum"}
    return df.resample(rule).agg(agg).dropna(subset=["close"])


def wilder(series, n):
    """Wilder's smoothing == EMA with alpha = 1/n."""
    return series.ewm(alpha=1 / n, adjust=False).mean()


def add_indicators(df):
    c, v = df["close"], df["volume_btc"]

    # 1. Moving averages
    for n in (20, 50, 200):
        df[f"sma{n}"] = c.rolling(n).mean()
    df["ema12"] = c.ewm(span=12, adjust=False).mean()
    df["ema26"] = c.ewm(span=26, adjust=False).mean()

    # 2. RSI 14 (Wilder)
    delta = c.diff()
    up, down = delta.clip(lower=0), -delta.clip(upper=0)
    rs = wilder(up, 14) / wilder(down, 14)
    df["rsi14"] = 100 - 100 / (1 + rs)

    # 3. MACD 12/26/9
    df["macd"] = df["ema12"] - df["ema26"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # 4. Bollinger Bands 20 / 2
    mid = c.rolling(20).mean()
    sd = c.rolling(20).std(ddof=0)
    df["bb_mid"], df["bb_upper"], df["bb_lower"] = mid, mid + 2 * sd, mid - 2 * sd
    df["bb_pctb"] = (c - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / mid

    # 5. Volume + OBV
    df["obv"] = (np.sign(c.diff()).fillna(0) * v.fillna(0)).cumsum()
    return df


def snapshot(name, df):
    r = df.iloc[-1]
    tags = []
    for n in (20, 50, 200):
        mv = r[f"sma{n}"]
        if pd.notna(mv):
            tags.append(f"{'above' if r['close'] > mv else 'below'} SMA{n}")
    rsi = r["rsi14"]
    rsi_tag = "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral"
    bb = r["bb_pctb"]
    bb_tag = ("above upper band" if bb > 1 else "below lower band" if bb < 0
              else f"{bb*100:.0f}% of band")
    print(f"\n=== {name.upper()}  (bar {df.index[-1].date()}) ===")
    print(f"  Close      : ${r['close']:,.2f}")
    print(f"  Trend      : {', '.join(tags)}")
    print(f"  RSI(14)    : {rsi:.1f}  ({rsi_tag})")
    print(f"  MACD hist  : {r['macd_hist']:+.1f}  ({'bullish' if r['macd_hist'] > 0 else 'bearish'})")
    print(f"  Bollinger  : {bb_tag}")


def main():
    daily = load_daily()
    for name, rule in TIMEFRAMES.items():
        df = add_indicators(resample(daily, rule))
        path = os.path.join(OUT, f"indicators_{name}.csv")
        df.round(6).to_csv(path)
        print(f"Wrote {len(df):>5} {name:7} rows -> {path}")
        snapshot(name, df)


if __name__ == "__main__":
    main()
