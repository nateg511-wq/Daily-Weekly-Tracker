#!/usr/bin/env python3
"""
Build the longest-possible daily BTC/USD master series.

  2010-07-18 .. 2011-08-17  -> Coin Metrics community reference price (close only)
  2011-08-18 .. today       -> Bitstamp true OHLC + volume

A `source` column marks each row so close-only early days are never mistaken
for real OHLC. Reads the existing Bitstamp CSV produced by fetch_btc_history.py.
"""
import csv
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BITSTAMP_CSV = os.path.join(HERE, "data", "btc_usd_daily.csv")
OUT_CSV = os.path.join(HERE, "data", "btc_usd_daily_full.csv")
CM_URL = "https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv"

SPLIT = "2011-08-18"   # first Bitstamp day; Coin Metrics covers everything before


def coinmetrics_early():
    req = urllib.request.Request(CM_URL, headers={"User-Agent": "btc-ta/1.0"})
    lines = urllib.request.urlopen(req, timeout=120).read().decode("utf-8").splitlines()
    r = csv.DictReader(lines)
    out = []
    for row in r:
        d, p = row.get("time", "")[:10], row.get("PriceUSD", "")
        if d and p and d < SPLIT:
            out.append((d, p))
    return out


def bitstamp_rows():
    with open(BITSTAMP_CSV) as f:
        return list(csv.DictReader(f))


def main():
    early = coinmetrics_early()
    late = bitstamp_rows()

    cols = ["date", "open", "high", "low", "close", "volume_btc", "source"]
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for d, p in early:                       # close-only reference price
            w.writerow([d, p, p, p, p, "", "coinmetrics_ref"])
        for r in late:                           # true OHLC
            w.writerow([r["date"], r["open"], r["high"], r["low"],
                        r["close"], r["volume_btc"], "bitstamp"])

    print(f"Master series -> {OUT_CSV}")
    print(f"  Coin Metrics (close-only): {len(early)} days, {early[0][0]} .. {early[-1][0]}")
    print(f"  Bitstamp (full OHLC):      {len(late)} days, {late[0]['date']} .. {late[-1]['date']}")
    print(f"  TOTAL: {len(early) + len(late)} days, {early[0][0]} .. {late[-1]['date']}")


if __name__ == "__main__":
    main()
