#!/usr/bin/env python3
"""Fail-closed validation for the IRC Media prediction-market category."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def https(value: object) -> bool:
    parsed = urlparse(str(value or ""))
    return parsed.scheme == "https" and bool(parsed.netloc)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(DATA / "prediction-markets.json"))
    args = parser.parse_args()
    readiness = load("prediction-markets-readiness.json")
    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    errors: list[str] = []

    if readiness.get("schemaVersion") != 1 or data.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")

    sources = readiness.get("sources") or []
    enabled = {
        source.get("id")
        for source in sources
        if source.get("enabled") is True
        and source.get("publicMarketDataWithoutAuthentication") is True
        and https(source.get("documentationUrl"))
        and str(source.get("apiBaseUrl", "")).startswith(
            "https://external-api.kalshi.com/trade-api/v2"
        )
    }

    core_events = data.get("events")
    if not isinstance(core_events, list) or not core_events:
        errors.append("at least one prediction-market event is required")
        core_events = []

    long_range_present = "longRangeEvents" in data
    long_range_events = data.get("longRangeEvents", [])
    if not isinstance(long_range_events, list):
        errors.append("longRangeEvents must be an array when present")
        long_range_events = []
    elif long_range_present and len(long_range_events) < 6:
        errors.append("at least six validated 2028 events are required when published")

    event_ids: set[str] = set()
    event_tickers: set[str] = set()
    tickers: set[str] = set()
    event_rows = [(event, False) for event in core_events] + [
        (event, True) for event in long_range_events
    ]
    for event, is_long_range in event_rows:
        event_id = str(event.get("eventId", "")).strip()
        if not event_id or event_id in event_ids:
            errors.append(f"duplicate or missing eventId: {event_id or '<missing>'}")
        event_ids.add(event_id)
        event_ticker = str(event.get("eventTicker", "")).strip()
        if is_long_range:
            if not event_ticker or event_ticker in event_tickers:
                errors.append(f"{event_id}: duplicate or missing eventTicker")
            event_tickers.add(event_ticker)
        if event.get("sourceId") not in enabled:
            errors.append(f"{event_id}: source is not enabled")
        if not https(event.get("sourceUrl")) or not https(event.get("apiUrl")):
            errors.append(f"{event_id}: HTTPS source and API URLs are required")
        if not str(event.get("resolutionSummary", "")).strip():
            errors.append(f"{event_id}: resolution summary is required")
        outcomes = event.get("outcomes")
        if not isinstance(outcomes, list) or len(outcomes) < 2:
            errors.append(f"{event_id}: at least two outcomes are required")
            continue
        labels: set[str] = set()
        for outcome in outcomes:
            ticker = str(outcome.get("ticker", "")).strip()
            label = str(outcome.get("label", "")).strip()
            if not ticker or ticker in tickers:
                errors.append(f"{event_id}: duplicate or missing ticker")
            tickers.add(ticker)
            if not label or label in labels:
                errors.append(f"{event_id}: duplicate or missing outcome label")
            labels.add(label)
            bid = outcome.get("bidPct")
            ask = outcome.get("askPct")
            if not isinstance(bid, (int, float)) or not isinstance(ask, (int, float)):
                errors.append(f"{ticker}: numeric bidPct and askPct are required")
            elif not (0 <= bid <= ask <= 100) or ask - bid > 5:
                errors.append(f"{ticker}: invalid or excessively wide quote spread")
            if not isinstance(outcome.get("volumeContracts"), (int, float)) or outcome["volumeContracts"] < 1000:
                errors.append(f"{ticker}: insufficient total contract volume")
            if not isinstance(outcome.get("openInterestContracts"), (int, float)) or outcome["openInterestContracts"] < 100:
                errors.append(f"{ticker}: insufficient open interest")

    public = readiness.get("publicDisplayEnabled") is True
    gates = readiness.get("gates") or {}
    if public and (
        data.get("status") != "published"
        or not enabled
        or not core_events
        or not gates
        or not all(value is True for value in gates.values())
    ):
        errors.append("public display enabled before all prediction-market gates passed")
    automated = readiness.get("automatedPublishingEnabled") is True
    if automated and gates.get("automationIsolationValidated") is not True:
        errors.append("automatic publishing lacks an isolation validation gate")

    try:
        generated = datetime.fromisoformat(str(data.get("generatedAt")).replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if generated < now - timedelta(hours=24):
            errors.append("prediction-market snapshot is older than 24 hours")
        if generated > now + timedelta(minutes=5):
            errors.append("prediction-market snapshot timestamp is in the future")
    except (TypeError, ValueError):
        errors.append("generatedAt must be an ISO timestamp")

    if not str(data.get("disclosure", "")).strip():
        errors.append("prediction-market disclosure is required")
    if data.get("disclosure") != readiness.get("disclosure"):
        errors.append("prediction-market disclosure does not match readiness policy")

    report = {
        "feature": "prediction-markets",
        "eventsValidated": len(core_events),
        "longRangeEventsValidated": len(long_range_events),
        "enabledSources": sorted(enabled),
        "publicDisplayEnabled": public,
        "automatedPublishingEnabled": automated,
        "errors": errors,
        "passed": not errors,
    }
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit("Prediction-market readiness validation failed closed.")


if __name__ == "__main__":
    main()
