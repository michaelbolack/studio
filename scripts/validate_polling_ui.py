#!/usr/bin/env python3
"""Static fail-closed checks for the national polling interface."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")

REQUIRED = [
    'id="polling-nav" href="#national-polling" hidden',
    'id="national-polling" hidden',
    "function pollingDisplaySafe(",
    "readiness?.publicDisplayEnabled!==true",
    "data?.status!=='published'",
    "source.enabled===true&&source.permittedForRepublication===true",
    "section.hidden=true;nav.hidden=true",
    "await Promise.all([loadAll(),loadPolling()])",
    "pollingData.disclosure",
]

missing = [token for token in REQUIRED if token not in INDEX]
if missing:
    raise SystemExit("Polling UI validation failed closed; missing: " + ", ".join(missing))

if 'id="polling-nav" href="#national-polling">National Polling</a>' in INDEX:
    raise SystemExit("Polling navigation must remain hidden by default.")

print("Polling UI fail-closed checks passed.")
