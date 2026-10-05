#!/usr/bin/env python3
"""Static fail-closed checks for the national polling interface."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
MODULE = (ROOT / "assets" / "election-voter-hub.mjs").read_text(encoding="utf-8")

REQUIRED = [
    'id="polling-nav" href="#national-polling" hidden',
    'id="national-polling" hidden',
    "function pollingDisplaySafe(",
    "readiness?.publicDisplayEnabled!==true",
    "data?.status!=='published'",
    "source.enabled===true&&source.permittedForRepublication===true",
    "section.hidden=true;nav.hidden=true",
    "await Promise.all([loadAll(),loadPolling(),loadPredictionMarkets()])",
    "function setCenterView(view,",
    "ELECTION_VIEW_IDS.forEach",
    "element.hidden=centerView!=='results'",
    "setCenterView('polling')",
    "setCenterView('results',{scroll:false})",
    '<body class="results-view">',
    ".results-view #national-polling",
    ".polling-view #county-note",
    ".markets-view #national-polling",
    "function initCenterViewNavigation()",
    "initCenterViewNavigation();hideExpiredCurrentMarkets();setCenterView('results'",
    "document.body.classList.toggle('polling-view'",
    "pollingData.disclosure",
]

missing = [token for token in REQUIRED if token not in INDEX]
if missing:
    raise SystemExit("Polling UI validation failed closed; missing: " + ", ".join(missing))

if 'id="polling-nav" href="#national-polling">National Polling</a>' in INDEX:
    raise SystemExit("Polling navigation must remain hidden by default.")

MODULE_REQUIRED = [
    "poll.displayStatus",
    "poll.sponsor",
    "poll.publicationDate",
    "poll.marginOfError",
    "county-relevant",
    "florida-statewide",
    "national",
]
module_missing = [token for token in MODULE_REQUIRED if token not in MODULE]
if module_missing:
    raise SystemExit("Polling metadata UI validation failed closed; missing: " + ", ".join(module_missing))

print("Polling UI fail-closed checks passed.")
