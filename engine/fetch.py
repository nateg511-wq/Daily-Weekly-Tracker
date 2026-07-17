"""Data acquisition: BTC/USD daily history (Bitstamp + Coin Metrics stub) and the
altcoin basket for the froth index.

Incremental by design — reruns only fetch what's new, so a daily run is fast:
  * Bitstamp: resumes from the last cached day (refetches the last 3 days so the
    final partial candle gets replaced by the settled one).
  * Coin Metrics early-history stub (2010-07-18 .. 2011-08-17): fetched once, cached.
  * Altcoin basket: skipped when already refreshed today (Coin Metrics community
    files lag ~6 weeks anyway); force with --force.

Outputs (all in data/):
  btc_usd_daily.csv        Bitstamp OHLC, 2011-08-18 .. today
  btc_usd_daily_full.csv   Coin Metrics close-only stub + Bitstamp, source-tagged
  altcoin_data.csv         daily BTC/alt market caps, dominance, ETH/BTC
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import re
import tempfile

import pandas as pd

from .common import DATA, ensure_dirs, http_get, load_settings, log

BITSTAMP_CSV = DATA / "btc_usd_daily.csv"
FULL_CSV = DATA / "btc_usd_daily_full.csv"
CM_STUB_CSV = DATA / "coinmetrics_2010_2011_stub.csv"
ALT_CSV = DATA / "altcoin_data.csv"

BITSTAMP_URL = "https://www.bitstamp.net/api/v2/ohlc/btcusd/"
CM_URL = "https://raw.githubusercontent.com/coinmetrics/data/master/csv/{}.csv"
STEP = 86400
LIMIT = 1000


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _valid_row(row: list[str]) -> bool:
    if len(row) != 6 or not _DATE_RE.match(row[0]):
        return False
    try:
        return all(float(v) >= 0 for v in row[1:6]) and float(row[4]) > 0
    except ValueError:
        return False


def _load_existing_bitstamp() -> dict[str, list[str]]:
    """Load the cache, silently dropping corrupt rows (they get refetched)."""
    rows: dict[str, list[str]] = {}
    dropped = 0
    if BITSTAMP_CSV.exists():
        with open(BITSTAMP_CSV, encoding="utf-8", newline="") as f:
            for row in csv.reader(f):
                if _valid_row(row):
                    rows[row[0]] = row
                elif row and row[0] != "date":
                    dropped += 1
    if dropped:
        log(f"bitstamp: dropped {dropped} corrupt cache rows (will refetch)")
    return rows


def _atomic_write_csv(path, header: list[str], rows_iter) -> None:
    """Write CSV to a temp file in the same dir, then atomically replace."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows_iter)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def fetch_bitstamp(settings: dict) -> None:
    """Incremental daily OHLC from Bitstamp. Refetches the trailing 3 days to
    replace any previously-cached partial candle with the settled one."""
    rows = _load_existing_bitstamp()
    if rows:
        last = max(rows)
        start_ts = int(dt.datetime.strptime(last, "%Y-%m-%d")
                       .replace(tzinfo=dt.timezone.utc).timestamp()) - 2 * STEP
        log(f"bitstamp: cache through {last}; resuming from {last} − 2d")
    else:
        start_ts = settings["data"]["bitstamp_start"]
        log("bitstamp: no cache — full history fetch (takes a few minutes)")

    now = int(dt.datetime.now(tz=dt.timezone.utc).timestamp())
    start, fetched = start_ts, 0
    while start < now:
        url = f"{BITSTAMP_URL}?step={STEP}&limit={LIMIT}&start={start}"
        body = http_get(url).decode()
        try:
            data = json.loads(body)["data"]["ohlc"]
        except (KeyError, ValueError, TypeError) as e:
            raise RuntimeError(f"Bitstamp response shape unexpected at {url}: {body[:200]}") from e
        if not data:
            break
        for c in data:
            if float(c["close"]) <= 0:
                continue
            d = dt.datetime.fromtimestamp(int(c["timestamp"]), tz=dt.timezone.utc).strftime("%Y-%m-%d")
            rows[d] = [d, c["open"], c["high"], c["low"], c["close"], c["volume"]]
            fetched += 1
        last_ts = max(int(c["timestamp"]) for c in data)
        if last_ts <= start:
            break
        start = last_ts + STEP

    _atomic_write_csv(BITSTAMP_CSV, ["date", "open", "high", "low", "close", "volume_btc"],
                      (rows[d] for d in sorted(rows)))
    log(f"bitstamp: {len(rows)} days cached ({fetched} candles fetched), "
        f"{min(rows)} .. {max(rows)}, last close ${float(rows[max(rows)][4]):,.2f}")


def fetch_cm_stub(settings: dict) -> None:
    """One-time close-only reference price for 2010-07-18 .. day before Bitstamp."""
    if CM_STUB_CSV.exists():
        return
    split = settings["data"]["coinmetrics_split"]
    log("coinmetrics: fetching 2010–2011 early-history stub (one-time)")
    lines = http_get(CM_URL.format("btc"), timeout=120).decode().splitlines()
    out = []
    for row in csv.DictReader(lines):
        d, p = row.get("time", "")[:10], row.get("PriceUSD", "")
        if d and p and d < split:
            out.append((d, p))
    _atomic_write_csv(CM_STUB_CSV, ["date", "close"], out)
    log(f"coinmetrics: stub cached, {len(out)} days")


def build_full_series() -> None:
    """Master series: CM stub (close-only, source-tagged) + Bitstamp OHLC."""
    out = []
    with open(CM_STUB_CSV, encoding="utf-8", newline="") as g:
        for row in csv.DictReader(g):
            p = row["close"]
            out.append([row["date"], p, p, p, p, "", "coinmetrics_ref"])
    with open(BITSTAMP_CSV, encoding="utf-8", newline="") as g:
        for row in csv.DictReader(g):
            out.append([row["date"], row["open"], row["high"], row["low"],
                        row["close"], row["volume_btc"], "bitstamp"])
    _atomic_write_csv(FULL_CSV, ["date", "open", "high", "low", "close", "volume_btc", "source"], out)
    log(f"master series: {len(out)} days -> {FULL_CSV.name}")


def fetch_altcoins(settings: dict, force: bool = False) -> None:
    """Altcoin market caps for the froth index. Skips if refreshed today.
    Note: Coin Metrics community data lags ~6 weeks — froth is a tilt, not a score input."""
    if ALT_CSV.exists() and not force:
        mtime = dt.date.fromtimestamp(ALT_CSV.stat().st_mtime)
        has_rows = sum(1 for _ in open(ALT_CSV, encoding="utf-8")) > 100
        if mtime == dt.date.today() and has_rows:
            log("altcoins: already refreshed today — skipping (use --force-altcoins to refetch)")
            return
    assets = settings["data"]["altcoin_assets"]
    price, mcap, ok = {}, {}, []
    for a in assets:
        try:
            raw = http_get(CM_URL.format(a), timeout=120, retries=2).decode()
            df = pd.read_csv(io.StringIO(raw),
                             usecols=lambda c: c in ("time", "PriceUSD", "CapMrktCurUSD"),
                             parse_dates=["time"]).rename(columns={"time": "date"}).set_index("date").sort_index()
            if "CapMrktCurUSD" in df and df["CapMrktCurUSD"].notna().any():
                price[a], mcap[a] = df.get("PriceUSD"), df["CapMrktCurUSD"]
                ok.append(a)
                log(f"altcoins: {a} ok")
            else:
                log(f"altcoins: {a} skipped (no market cap)")
        except Exception as e:  # noqa: BLE001 — skip assets that fail, basket is robust to gaps
            log(f"altcoins: {a} failed ({e}) — skipped")
    if "btc" not in ok or "eth" not in ok:
        raise RuntimeError("altcoins: need at least btc and eth market caps")

    caps = pd.DataFrame(mcap)
    alts = [a for a in ok if a != "btc"]
    out = pd.DataFrame({
        "btc_price": price["btc"],
        "btc_mcap": caps["btc"],
        "alt_mcap": caps[alts].sum(axis=1, min_count=3),
        "n_alts": caps[alts].notna().sum(axis=1),
        "eth_btc": price["eth"] / price["btc"],
    }).dropna(subset=["btc_mcap", "alt_mcap"])
    out["alt_share"] = out["alt_mcap"] / (out["alt_mcap"] + out["btc_mcap"])
    if len(out) < 1000 or len(ok) < 4:
        raise RuntimeError(f"altcoins: too little data fetched ({len(out)} rows from {len(ok)} assets) — "
                           "cache left untouched; rerun with --force-altcoins later")
    tmp = ALT_CSV.with_suffix(".tmp")
    out.to_csv(tmp)
    os.replace(tmp, ALT_CSV)
    log(f"altcoins: {len(out)} rows, {out.index[0].date()} .. {out.index[-1].date()}")


def run(force_altcoins: bool = False) -> None:
    ensure_dirs()
    settings = load_settings()
    fetch_bitstamp(settings)
    fetch_cm_stub(settings)
    build_full_series()
    fetch_altcoins(settings, force=force_altcoins)
