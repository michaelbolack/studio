#!/usr/bin/env python3
"""Static integration checks for the pre-election voter hub."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
MODULE = (ROOT / "assets" / "election-voter-hub.mjs").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "election-readiness-check.yml").read_text(encoding="utf-8")

INDEX_REQUIRED = [
    'id="election-countdown"',
    'id="voter-information"',
    'id="voter-county-select"',
    'id="voter-actions"',
    'id="latest-polls"',
    'id="voter-hub-status"',
    'type="module" src="assets/election-voter-hub.mjs"',
    'label for="voter-county-select"',
    'aria-live="polite"',
    'role="status"',
    ':focus-visible',
    '@media(prefers-reduced-motion:reduce)',
    '@media(max-width:640px)',
    '.voter-action-grid{grid-template-columns:1fr}',
    'href="#voter-information"',
    'href="#latest-polls"',
    'href="#florida-heatmap"',
    'href="#local-races"',
    'href="#prediction-markets"',
    'data-center-view="markets"',
    'data-center-view="results"',
    'href="#races"',
    'class="official-statewide-fallback"',
    'id="florida-heatmap"',
    'id="national-polling"',
    'id="prediction-markets"',
    'id="races"',
]

MODULE_REQUIRED = [
    "ELECTION DAY IS HERE",
    "RESULTS COVERAGE",
    "UNTIL ELECTION DAY",
    "temporarily unavailable",
    "data-local-poll-status",
    "initVoterHub",
]

missing = [token for token in INDEX_REQUIRED if token not in INDEX]
missing += [f"module:{token}" for token in MODULE_REQUIRED if token not in MODULE]
WORKFLOW_REQUIRED = [
    "python3 -m unittest scripts.test_voter_information -v",
    "python3 scripts/validate_voter_information.py",
    "node --test tests/election-voter-hub.test.mjs",
    "python3 scripts/validate_voter_hub_ui.py",
]
missing += [f"workflow:{token}" for token in WORKFLOW_REQUIRED if token not in WORKFLOW]
if missing:
    raise SystemExit("Voter hub UI validation failed closed; missing: " + ", ".join(missing))

print("Voter hub UI integration checks passed.")
