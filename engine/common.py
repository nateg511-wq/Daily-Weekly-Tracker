"""Shared plumbing for the CoinPicks Direction System.

Everything path-related resolves from ROOT (the folder containing run.py),
so the whole app can be moved to any machine and just work.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CHARTS = ROOT / "charts"
CONFIG = ROOT / "config"
REPORTS = ROOT / "reports"
TEMPLATES = ROOT / "templates"

USER_AGENT = "coinpicks-direction/1.0"


def ensure_dirs() -> None:
    for d in (DATA, CHARTS, REPORTS):
        d.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def http_get(url: str, timeout: int = 60, retries: int = 4, backoff: float = 2.0) -> bytes:
    """GET with polite retries and exponential backoff. Raises after all retries fail."""
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 — network errors come in many shapes
            last_err = e
            if attempt < retries - 1:
                wait = backoff * (2 ** attempt)
                log(f"fetch failed ({e.__class__.__name__}: {e}) — retry {attempt + 1}/{retries} in {wait:.0f}s")
                time.sleep(wait)
    raise RuntimeError(f"GET {url} failed after {retries} retries: {last_err}")


def http_get_json(url: str, **kw) -> dict:
    return json.loads(http_get(url, **kw).decode("utf-8"))


def load_json(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        if DATA in path.parents:
            die(f"{path.name} missing — run `python run.py quant` (or `python run.py all`) first")
        raise


def save_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def load_settings() -> dict:
    return load_json(CONFIG / "settings.json")


def load_scores() -> dict:
    return load_json(CONFIG / "scores.json")


# ---- house standard (single source of truth for formulas/labels) ----
GRID = [1, 3, 6, 12, 36]
LBL = {1: "1mo", 3: "3mo", 6: "6mo", 12: "1yr", 36: "3yr"}


def signal(p: float, quality: float, impact: float) -> float:
    """House formula: Signal = ((P − 50) / 50) × Quality × Impact, range −10..+10."""
    return ((p - 50) / 50) * quality * impact


def call(s: float) -> str:
    """House bands on |signal|: <0.5 Neutral | <1.5 Mild | <3 Bull/Bear | <5 Strong | else Very Strong."""
    a = abs(s)
    d = "Bull" if s > 0 else "Bear"
    if a < 0.5:
        return "Neutral"
    if a < 1.5:
        return f"Mild {d}"
    if a < 3.0:
        return d
    if a < 5.0:
        return f"Strong {d}"
    return f"Very Strong {d}"
