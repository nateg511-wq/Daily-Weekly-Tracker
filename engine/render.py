"""Report rendering: substitute chart tokens, render HTML -> PDF, archive runs.

Report sources live in reports/current/*.html (the AI operator edits those per
the CLAUDE.md runbook). {{CHART_*}} tokens are replaced with base64-embedded
PNGs from charts/. PDFs land in reports/current/pdf/.

Cross-platform Chrome/Chromium detection (macOS/Linux/Windows). If no browser
is found, HTML output still works and PDFs are skipped with a warning.
"""
from __future__ import annotations

import base64
import datetime as dt
import os
import shutil
import subprocess
from pathlib import Path

from .common import CHARTS, REPORTS, log

CURRENT = REPORTS / "current"
BUILD = REPORTS / "current" / "build"
PDF = REPORTS / "current" / "pdf"
ARCHIVE = REPORTS / "archive"

CHART_TOKENS = {
    "{{CHART_WEEKLY}}": "btc_weekly.png",
    "{{CHART_MONTHLY}}": "btc_monthly.png",
    "{{CHART_QUARTERLY}}": "btc_quarterly.png",
    "{{CHART_CYCLE}}": "halving_cycle.png",
    "{{CHART_DOWNSIDE}}": "downside_map.png",
}


def find_chrome() -> str | None:
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "msedge",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in candidates:
        path = c if os.path.sep in c or c.endswith(".exe") else shutil.which(c)
        if path and Path(path).exists():
            return str(path)
    return None


def substitute_charts(html: str) -> str:
    for token, png in CHART_TOKENS.items():
        if token in html:
            p = CHARTS / png
            if not p.exists():
                raise FileNotFoundError(f"{png} referenced by a report but not generated — run `python run.py quant` first")
            b64 = base64.b64encode(p.read_bytes()).decode()
            html = html.replace(token, f"data:image/png;base64,{b64}")
    return html


def render_pdfs() -> None:
    """Build final HTMLs (token substitution) and render each to PDF."""
    if not CURRENT.exists():
        raise FileNotFoundError("reports/current/ missing — nothing to render")
    BUILD.mkdir(parents=True, exist_ok=True)
    PDF.mkdir(parents=True, exist_ok=True)
    chrome = find_chrome()
    if not chrome:
        log("render: WARNING — no Chrome/Chromium/Edge found; HTML built, PDFs skipped")

    sources = sorted(CURRENT.glob("*.html"))
    if not sources:
        raise FileNotFoundError("reports/current/ has no .html sources")
    failures = 0
    for src in sources:
        html = substitute_charts(src.read_text(encoding="utf-8"))
        built = BUILD / src.name
        built.write_text(html, encoding="utf-8")
        if chrome:
            out = PDF / (src.stem + ".pdf")
            out.unlink(missing_ok=True)          # never let a stale PDF pass as fresh
            try:
                res = subprocess.run(
                    [chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                     f"--print-to-pdf={out}", built.resolve().as_uri()],
                    capture_output=True, text=True, timeout=180,
                )
            except subprocess.TimeoutExpired:
                log(f"render: FAILED {src.name} — Chrome timed out after 180s")
                failures += 1
                continue
            if res.returncode == 0 and out.exists() and out.stat().st_size > 10_000:
                log(f"render: {out.name} ({out.stat().st_size//1024} KB)")
            else:
                log(f"render: FAILED {src.name} — rc={res.returncode} {res.stderr.strip()[:200]}")
                failures += 1
    if failures:
        raise RuntimeError(f"render: {failures} report(s) failed to produce a PDF — see log above")


def archive(label: str | None = None) -> Path:
    """Snapshot reports/current (+pdf) and the data JSONs into reports/archive/<date>/."""
    stamp = label or dt.date.today().isoformat()
    dest = ARCHIVE / stamp
    n = 2
    while dest.exists():                          # never overwrite — lineage is sacred
        dest = ARCHIVE / f"{stamp}-{n}"
        n += 1
    dest.mkdir(parents=True)
    for src in CURRENT.glob("*.html"):
        shutil.copy2(src, dest / src.name)
    if PDF.exists():
        (dest / "pdf").mkdir()
        for p in PDF.glob("*.pdf"):
            shutil.copy2(p, dest / "pdf" / p.name)
    from .common import DATA
    for j in ("signals.json", "cycle.json", "pillar_scores.json", "master_blend.json"):
        if (DATA / j).exists():
            shutil.copy2(DATA / j, dest / j)
    log(f"archive: snapshot -> {dest}")
    return dest
