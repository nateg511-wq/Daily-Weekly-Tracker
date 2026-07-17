#!/usr/bin/env python3
"""
Fetch the longest-available daily BTC/USD price history and save as CSV.

Source: Bitstamp OHLC API (no API key required). One of the oldest USD
exchanges -> daily candles back to ~2011. Paginates 1000 candles per call.
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT_CSV = os.path.join(OUT_DIR, "btc_usd_daily.csv")

STEP = 86400          # 1 day in seconds
LIMIT = 1000          # max candles per Bitstamp call
START = 1293840000    # 2011-01-01 (data naturally begins where it exists)
BASE = "https://www.bitstamp.net/api/v2/ohlc/btcusd/"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "btc-ta/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    now = int(datetime.now(tz=timezone.utc).timestamp())

    by_ts = {}
    start = START
    while start < now:
        url = f"{BASE}?step={STEP}&limit={LIMIT}&start={start}"
        data = fetch(url)["data"]["ohlc"]
        if not data:
            break
        for c in data:
            by_ts[int(c["timestamp"])] = c
        last_ts = max(int(c["timestamp"]) for c in data)
        if last_ts <= start:           # no forward progress -> stop
            break
        start = last_ts + STEP
        time.sleep(0.4)                # be polite to the API

    rows = [by_ts[t] for t in sorted(by_ts)]
    rows = [c for c in rows if float(c["close"]) > 0]

    cols = ["date", "open", "high", "low", "close", "volume_btc"]
    with open(OUT_CSV, "w") as f:
        f.write(",".join(cols) + "\n")
        for c in rows:
            d = datetime.fromtimestamp(int(c["timestamp"]), tz=timezone.utc).strftime("%Y-%m-%d")
            f.write(",".join([d, c["open"], c["high"], c["low"], c["close"], c["volume"]]) + "\n")

    f0 = datetime.fromtimestamp(int(rows[0]["timestamp"]), tz=timezone.utc).strftime("%Y-%m-%d")
    f1 = datetime.fromtimestamp(int(rows[-1]["timestamp"]), tz=timezone.utc).strftime("%Y-%m-%d")
    print(f"Saved {len(rows)} daily rows -> {OUT_CSV}")
    print(f"Range: {f0}  ->  {f1}")
    print(f"First close: ${rows[0]['close']}   Last close: ${rows[-1]['close']}")


if __name__ == "__main__":
    main()
