#!/usr/bin/env python3
"""Prove the scheduled prediction-market collector cannot publish election results."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/prediction-markets-collector.yml").read_text(encoding="utf-8")
SCRIPT = (ROOT / "scripts/collect_prediction_markets.py").read_text(encoding="utf-8")

required_workflow = (
    "schedule:",
    "push:",
    "branches: [main]",
    "cron: '45 11 * * *'",
    "concurrency:",
    "python scripts/collect_prediction_markets.py",
    "python scripts/validate_prediction_markets.py",
    "python scripts/validate_prediction_markets_collector.py",
    "if: github.event_name != 'pull_request'",
    "git add data/prediction-markets.json",
)
for marker in required_workflow:
    assert marker in WORKFLOW, f"Missing collector safety marker: {marker}"

assert "data/prediction-markets.json" not in WORKFLOW.split("push:", 1)[1].split("pull_request:", 1)[0], "Data-only commits must not retrigger the collector"

for forbidden in (
    "git add .",
    "data/manifest.json",
    "data/statewide.json",
    "data/congressional.json",
    "data/legislative.json",
    "polling.json",
    "election-config.json",
):
    assert forbidden not in WORKFLOW, f"Collector may touch a protected file: {forbidden}"

required_script = (
    'API_BASE = "https://external-api.kalshi.com/trade-api/v2"',
    '"CONTROLH-2026-D"',
    '"CONTROLH-2026-R"',
    '"CONTROLS-2026-D"',
    '"CONTROLS-2026-R"',
    '"KXPRESNOMD-28"',
    '"KXPRESNOMR-28"',
    '"KXPRESPERSON-28"',
    '"KXPRESPARTY-2028"',
    '"POWER-28"',
    '"POPVOTEMOV-28NOV07"',
    "fewer than six 2028 events passed live compatibility gates",
    "duplicate configured ticker",
    "maximum five-point spread gate",
    "failed liquidity gates",
    'default="data/prediction-markets.json"',
)
for marker in required_script:
    assert marker in SCRIPT, f"Missing collector validation: {marker}"

for forbidden in (
    'DATA / "manifest.json"',
    'DATA / "statewide.json"',
    'DATA / "polling.json"',
    "subprocess",
    "git push",
):
    assert forbidden not in SCRIPT, f"Collector script contains forbidden capability: {forbidden}"

print("Prediction-market collector isolation checks passed.")
