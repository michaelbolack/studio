#!/usr/bin/env python3
"""Fail-closed checks for the isolated polling source monitor."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/polling-source-monitor.yml").read_text(encoding="utf-8")
SCRIPT = (ROOT / "scripts/monitor_polling_sources.py").read_text(encoding="utf-8")

required_workflow = (
    "schedule:",
    "cron: '15 11 * * *'",
    "contents: read",
    "without publishing",
    "actions/upload-artifact@v4",
)
for marker in required_workflow:
    assert marker in WORKFLOW, f"Missing polling monitor safety marker: {marker}"

for forbidden in ("contents: write", "git push", "create-pull-request", "polling.json >"):
    assert forbidden not in WORKFLOW, f"Publishing capability forbidden in monitor: {forbidden}"

required_script = (
    '"mode": "monitor-only-no-publishing"',
    "known_source_urls",
    "check_votehub",
    "check_rasmussen",
    "check_emerson",
)
for marker in required_script:
    assert marker in SCRIPT, f"Missing polling monitor behavior: {marker}"

assert "write_text" in SCRIPT
assert 'DATA / "polling.json"' in SCRIPT
assert ".write_text" not in SCRIPT.split('def known_source_urls', 1)[1].split('def check_votehub', 1)[0]

print("Polling source monitor isolation checks passed.")
