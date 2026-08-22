#!/usr/bin/env python3
"""Fail-closed validation for the IRC Media polling feature foundation."""

import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REQUIRED_POLL_FIELDS = {
    "pollId", "raceId", "pollster", "startDate", "endDate",
    "population", "sampleSize", "answers", "sourceUrl",
}
ALLOWED_POPULATIONS = {"a", "adults", "rv", "lv", "voters"}


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def valid_url(value):
    parsed = urlparse(str(value or ""))
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_poll(poll):
    errors = []
    missing = sorted(REQUIRED_POLL_FIELDS - set(poll))
    if missing:
        errors.append("missing fields: " + ", ".join(missing))
        return errors
    if not str(poll["pollId"]).strip() or not str(poll["raceId"]).strip():
        errors.append("pollId and raceId must be nonempty")
    if not str(poll["pollster"]).strip():
        errors.append("pollster must be nonempty")
    try:
        start = date.fromisoformat(poll["startDate"])
        end = date.fromisoformat(poll["endDate"])
        if start > end:
            errors.append("startDate is after endDate")
    except (TypeError, ValueError):
        errors.append("poll dates must be ISO YYYY-MM-DD")
    if str(poll["population"]).lower() not in ALLOWED_POPULATIONS:
        errors.append("unsupported population")
    if not isinstance(poll["sampleSize"], int) or poll["sampleSize"] <= 0:
        errors.append("sampleSize must be a positive integer")
    answers = poll["answers"]
    if not isinstance(answers, list) or len(answers) < 2:
        errors.append("answers must contain at least two choices")
    else:
        seen = set()
        for answer in answers:
            choice = str(answer.get("choice", "")).strip()
            pct = answer.get("pct")
            if not choice or choice.casefold() in seen:
                errors.append("answer choices must be unique and nonempty")
                break
            seen.add(choice.casefold())
            if not isinstance(pct, (int, float)) or pct < 0 or pct > 100:
                errors.append("answer pct must be between 0 and 100")
                break
    if not valid_url(poll["sourceUrl"]):
        errors.append("sourceUrl must be HTTPS")
    return errors


def main():
    readiness = load("polling-readiness.json")
    polling = load("polling.json")
    errors = []

    if readiness.get("schemaVersion") != 1 or polling.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    sources = readiness.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("at least one polling source must be declared")
        sources = []
    enabled_sources = [source for source in sources if source.get("enabled") is True]
    for source in sources:
        if source.get("permittedForRepublication") is True:
            if not valid_url(source.get("documentationUrl") or source.get("licenseUrl")):
                errors.append(f"permitted source {source.get('id')} lacks HTTPS documentation")
    polls = list(polling.get("races", [])) + list(polling.get("nationalIndicators", []))
    seen_ids = set()
    for poll in polls:
        poll_id = str(poll.get("pollId", ""))
        if poll_id in seen_ids:
            errors.append(f"duplicate pollId: {poll_id}")
        seen_ids.add(poll_id)
        errors.extend(f"{poll_id or '<unknown>'}: {error}" for error in validate_poll(poll))

    display_enabled = readiness.get("publicDisplayEnabled") is True
    automation_enabled = readiness.get("automatedPublishingEnabled") is True
    gates = readiness.get("gates", {})
    all_gates_green = bool(gates) and all(value is True for value in gates.values())
    if display_enabled and (not all_gates_green or not enabled_sources or not polls):
        errors.append("public display enabled before all gates, sources and polls are ready")
    if automation_enabled and not display_enabled:
        errors.append("automated publishing enabled while public display is disabled")
    if not display_enabled and polling.get("status") != "withheld-not-ready":
        errors.append("disabled polling must remain withheld-not-ready")
    if polling.get("generatedAt") is None and polls:
        errors.append("polling with data requires generatedAt")
    if not str(polling.get("disclosure", "")).strip():
        errors.append("polling disclosure is required")

    report = {
        "feature": "polling-center",
        "pollsValidated": len(polls),
        "enabledSources": [source.get("id") for source in enabled_sources],
        "publicDisplayEnabled": display_enabled,
        "automatedPublishingEnabled": automation_enabled,
        "errors": errors,
        "passed": not errors,
    }
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit("Polling readiness validation failed closed.")


if __name__ == "__main__":
    main()
