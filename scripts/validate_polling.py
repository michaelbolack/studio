#!/usr/bin/env python3
"""Fail-closed validation for the IRC Media polling feature foundation."""

import json
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REQUIRED_POLL_FIELDS = {
    "pollId", "raceId", "sourceId", "pollster", "startDate", "endDate",
    "population", "sampleSize", "answers", "sourceUrl",
}
ALLOWED_POPULATIONS = {"a", "adults", "rv", "lv", "voters"}
ALLOWED_SCOPES = {"county-relevant", "florida-statewide", "national"}
ALLOWED_DISPLAY_STATUSES = {"current", "older-poll", "incomplete-metadata", "source-unavailable"}
ALLOWED_COVERAGE_STATES = {"current", "no-current-verified-poll"}


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def valid_url(value):
    parsed = urlparse(str(value or ""))
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_poll(poll, today=None, freshness_days=14):
    today = today or date.today()
    errors = []
    missing = sorted(REQUIRED_POLL_FIELDS - set(poll))
    if missing:
        errors.append("missing fields: " + ", ".join(missing))
        return errors
    if not str(poll["pollId"]).strip() or not str(poll["raceId"]).strip():
        errors.append("pollId and raceId must be nonempty")
    if not str(poll["pollster"]).strip():
        errors.append("pollster must be nonempty")
    start = end = None
    try:
        start = date.fromisoformat(poll["startDate"])
        end = date.fromisoformat(poll["endDate"])
        if start > end:
            errors.append("startDate is after endDate")
        if start > today or end > today:
            errors.append("poll dates cannot be in the future")
    except (TypeError, ValueError):
        errors.append("poll dates must be ISO YYYY-MM-DD")
    scope = poll.get("scope")
    if scope not in ALLOWED_SCOPES:
        errors.append("unsupported scope")
    county_ids = poll.get("countyIds")
    if not isinstance(county_ids, list):
        errors.append("countyIds must be an array")
    elif scope == "county-relevant" and not county_ids:
        errors.append("county-relevant polls require countyIds")
    elif any(not str(county_id).strip() for county_id in county_ids):
        errors.append("countyIds must contain nonempty ids")
    publication_date = poll.get("publicationDate")
    if publication_date is not None:
        try:
            published = date.fromisoformat(publication_date)
            if published > today:
                errors.append("publicationDate cannot be in the future")
            if end is not None and published < end:
                errors.append("publicationDate cannot precede endDate")
        except (TypeError, ValueError):
            errors.append("publicationDate must be ISO YYYY-MM-DD")
    margin = poll.get("marginOfError")
    if margin is not None and (not isinstance(margin, (int, float)) or isinstance(margin, bool) or margin < 0):
        errors.append("marginOfError must be a nonnegative number")
    if poll.get("sponsor") is not None and not str(poll.get("sponsor")).strip():
        errors.append("sponsor must be nonempty when provided")
    display_status = poll.get("displayStatus")
    if display_status not in ALLOWED_DISPLAY_STATUSES:
        errors.append("unsupported displayStatus")
    elif end is not None:
        is_fresh = end >= today - timedelta(days=freshness_days)
        if display_status == "current" and not is_fresh:
            errors.append("current poll is outside freshness window")
        if display_status == "older-poll" and is_fresh:
            errors.append("older-poll status used within freshness window")
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
    source_ids = {str(source.get("id", "")).strip() for source in sources}
    enabled_sources = [
        source for source in sources
        if source.get("enabled") is True
        and source.get("permittedForRepublication") is True
    ]
    enabled_source_ids = {source.get("id") for source in enabled_sources}
    for source in sources:
        if source.get("permittedForRepublication") is True:
            if not valid_url(source.get("documentationUrl") or source.get("licenseUrl")):
                errors.append(f"permitted source {source.get('id')} lacks HTTPS documentation")
    freshness_days = readiness.get("methodology", {}).get("freshnessDays", 14)
    if not isinstance(freshness_days, int) or freshness_days < 1:
        errors.append("methodology.freshnessDays must be a positive integer")
        freshness_days = 14
    polls = list(polling.get("races", [])) + list(polling.get("nationalIndicators", []))
    seen_ids = set()
    for poll in polls:
        poll_id = str(poll.get("pollId", ""))
        if poll_id in seen_ids:
            errors.append(f"duplicate pollId: {poll_id}")
        seen_ids.add(poll_id)
        errors.extend(
            f"{poll_id or '<unknown>'}: {error}"
            for error in validate_poll(poll, freshness_days=freshness_days)
        )
        if str(poll.get("sourceId", "")).strip() not in source_ids:
            errors.append(f"{poll_id or '<unknown>'}: sourceId is not declared")

    coverage_states = polling.get("coverageStates")
    if not isinstance(coverage_states, dict):
        errors.append("coverageStates must be declared")
        coverage_states = {}
    for scope in sorted(ALLOWED_SCOPES):
        declared = coverage_states.get(scope)
        if declared not in ALLOWED_COVERAGE_STATES:
            errors.append(f"coverageStates.{scope} is invalid")
            continue
        has_current = any(
            poll.get("scope") == scope and poll.get("displayStatus") == "current"
            for poll in polls
        )
        expected = "current" if has_current else "no-current-verified-poll"
        if declared != expected:
            errors.append(f"coverageStates.{scope} must be {expected}")

    display_enabled = readiness.get("publicDisplayEnabled") is True
    automation_enabled = readiness.get("automatedPublishingEnabled") is True
    gates = readiness.get("gates", {})
    all_gates_green = bool(gates) and all(value is True for value in gates.values())
    if display_enabled and (not all_gates_green or not enabled_sources or not polls):
        errors.append("public display enabled before all gates, sources and polls are ready")
    if display_enabled:
        if polling.get("status") != "published":
            errors.append("public display requires polling status published")
        undeployable = [
            str(poll.get("pollId", "<unknown>"))
            for poll in polls
            if poll.get("sourceId") not in enabled_source_ids
        ]
        if undeployable:
            errors.append("public display contains polls from disabled or unpermitted sources: " + ", ".join(undeployable))
        valid_end_dates = []
        for poll in polls:
            try:
                valid_end_dates.append(date.fromisoformat(poll["endDate"]))
            except (KeyError, TypeError, ValueError):
                pass
        if not valid_end_dates or max(valid_end_dates) < date.today() - timedelta(days=14):
            errors.append("public polling is stale; newest poll must have ended within 14 days")
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
