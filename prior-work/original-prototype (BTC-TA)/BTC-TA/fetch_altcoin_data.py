#!/usr/bin/env python3
"""
Acquire the inputs for an 'altcoin froth' index from Coin Metrics community data
(free, no key). For BTC + a basket of major alts we pull daily PriceUSD and
market cap (CapMrktCurUSD), then derive BTC dominance, altcoin market cap, and
the ETH/BTC ratio.

Output: data/altcoin_data.csv
"""
import io
import os
import urllib.request
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "altcoin_data.csv")
BASE = "https://raw.githubusercontent.com/coinmetrics/data/master/csv/{}.csv"

# btc + a basket of large, long-history alts (skip any that fail / lack mcap)
ASSETS = ["btc", "eth", "xrp", "ltc", "bch", "ada", "doge", "bnb",
          "sol", "dot", "link", "xlm", "trx", "etc", "xmr", "eos"]


def fetch(asset):
    url = BASE.format(asset)
    req = urllib.request.Request(url, headers={"User-Agent": "btc-ta/1.0"})
    raw = urllib.request.urlopen(req, timeout=120).read().decode("utf-8")
    df = pd.read_csv(io.StringIO(raw), usecols=lambda c: c in ("time", "PriceUSD", "CapMrktCurUSD"),
                     parse_dates=["time"])
    df = df.rename(columns={"time": "date"}).set_index("date").sort_index()
    return df


price, mcap = {}, {}
ok = []
for a in ASSETS:
    try:
        d = fetch(a)
        if "CapMrktCurUSD" in d and d["CapMrktCurUSD"].notna().any():
            price[a] = d["PriceUSD"]
            mcap[a] = d["CapMrktCurUSD"]
            ok.append(a)
    except Exception as e:
        print(f"  skip {a}: {e}")

P = pd.DataFrame(price)
M = pd.DataFrame(mcap)
alts = [a for a in ok if a != "btc"]

out = pd.DataFrame(index=M.index)
out["btc_price"] = P["btc"]
out["btc_mcap"] = M["btc"]
out["alt_mcap"] = M[alts].sum(axis=1, min_count=1)        # basket of major alts
out["total_mcap"] = out["btc_mcap"] + out["alt_mcap"]
out["btc_dominance"] = out["btc_mcap"] / out["total_mcap"]
out["alt_share"] = 1 - out["btc_dominance"]
out["eth_btc"] = P["eth"] / P["btc"]
out["n_alts"] = M[alts].notna().sum(axis=1)
out = out[out["btc_mcap"].notna() & (out["alt_mcap"] > 0)].dropna(subset=["btc_dominance"])

out.to_csv(OUT)
print(f"Assets used: {ok}")
print(f"Saved {len(out)} rows -> {OUT}")
print(f"Range: {out.index[0].date()} -> {out.index[-1].date()}")
print("\nSanity check (BTC dominance / alt share at key dates):")
for d in ["2017-06-01", "2017-12-15", "2019-06-01", "2021-05-10", "2021-11-08", "2022-11-21", "2026-06-15"]:
    r = out.asof(pd.Timestamp(d))
    print(f"  {d}: dominance {r['btc_dominance']*100:4.0f}%  alt_share {r['alt_share']*100:4.0f}%  eth/btc {r['eth_btc']:.4f}  (n_alts {int(r['n_alts'])})")
