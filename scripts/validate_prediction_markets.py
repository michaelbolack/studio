#!/usr/bin/env python3
"""Fail-closed validation for the IRC Media prediction-market category."""

from __future__ import annotations

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
    readiness = load("prediction-markets-readiness.json")
    data = load("prediction-markets.json")
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
    }

    events = data.get("events")
    if not isinstance(events, list) or not events:
        errors.append("at least one prediction-market event is required")
        events = []

    event_ids: set[str] = set()
    tickers: set[str] = set()
    for event in events:
        event_id = str(event.get("eventId", "")).strip()
        if not event_id or event_id in event_ids:
            errors.append(f"duplicate or missing eventId: {event_id or '<missing>'}")
        event_ids.add(event_id)
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
        for outcome in outcomes:
            ticker = str(outcome.get("ticker", "")).strip()
            if not ticker or ticker in tickers:
                errors.append(f"{event_id}: duplicate or missing ticker")
            tickers.add(ticker)
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
        or not events
        or not gates
        or not all(value is True for value in gates.values())
    ):
        errors.append("public display enabled before all prediction-market gates passed")
    if readiness.get("automatedPublishingEnabled") is True:
        errors.append("automatic prediction-market publishing is not approved")

    try:
        generated = datetime.fromisoformat(str(data.get("generatedAt")).replace("Z", "+00:00"))
        if generated < datetime.now(timezone.utc) - timedelta(hours=24):
            errors.append("prediction-market snapshot is older than 24 hours")
    except (TypeError, ValueError):
        errors.append("generatedAt must be an ISO timestamp")

    if not str(data.get("disclosure", "")).strip():
        errors.append("prediction-market disclosure is required")

    report = {
        "feature": "prediction-markets",
        "eventsValidated": len(events),
        "enabledSources": sorted(enabled),
        "publicDisplayEnabled": public,
        "automatedPublishingEnabled": readiness.get("automatedPublishingEnabled") is True,
        "errors": errors,
        "passed": not errors,
    }
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit("Prediction-market readiness validation failed closed.")


if __name__ == "__main__":
    main()
