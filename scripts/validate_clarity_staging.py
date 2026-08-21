#!/usr/bin/env python3
"""Validate Clarity browser-session snapshots without publishing them."""

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_timestamp(value):
    if not isinstance(value, str) or not value:
        raise ValueError("missing timestamp")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def valid_vote(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(value) and value >= 0
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        try:
            number = float(cleaned)
        except ValueError:
            return False
        return math.isfinite(number) and number >= 0
    return False


def validate_snapshot(path, expected, now, max_age_seconds):
    errors = []
    try:
        data = load_json(path)
    except Exception as exc:
        return {"county": expected["county"], "valid": False, "errors": [f"cannot read snapshot: {exc}"]}

    county = expected["county"]
    election_id = str(expected["electionId"])
    expected_host = urlparse(expected["host"]).netloc.lower()

    if data.get("schemaVersion") != 1:
        errors.append("unsupported snapshot schemaVersion")
    if data.get("collector") != "clarity-browser-session":
        errors.append("unexpected collector identity")
    if data.get("county") != county:
        errors.append("county does not match configuration")
    if str(data.get("electionId")) != election_id:
        errors.append("electionId does not match configuration")
    if not str(data.get("clarityVersion", "")).isdigit():
        errors.append("clarityVersion is not numeric")

    source_url = data.get("sourceDataUrl")
    parsed_source = urlparse(source_url) if isinstance(source_url, str) else None
    if not parsed_source or parsed_source.scheme != "https" or parsed_source.netloc.lower() != expected_host:
        errors.append("sourceDataUrl host does not match configuration")
    elif f"/{election_id}/" not in parsed_source.path or not parsed_source.path.endswith("/json/en/summary.json"):
        errors.append("sourceDataUrl path does not match the configured election")

    try:
        collected_at = parse_timestamp(data.get("collectedAt"))
        age_seconds = (now - collected_at).total_seconds()
        if age_seconds < -300:
            errors.append("snapshot timestamp is in the future")
        elif age_seconds > max_age_seconds:
            errors.append(f"snapshot is stale ({int(age_seconds)} seconds old)")
    except Exception as exc:
        errors.append(f"invalid collectedAt: {exc}")

    contests = data.get("payload")
    choice_count = 0
    vote_count = 0
    if not isinstance(contests, list) or not contests:
        errors.append("payload is not a non-empty contest list")
        contests = []

    for index, contest in enumerate(contests):
        if not isinstance(contest, dict):
            errors.append(f"contest {index} is not an object")
            continue
        name = contest.get("C")
        choices = contest.get("CH")
        votes = contest.get("V")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"contest {index} has no name")
        if not isinstance(choices, list) or not choices:
            errors.append(f"contest {index} has no choices")
            continue
        if not isinstance(votes, list) or len(votes) != len(choices):
            errors.append(f"contest {index} has mismatched choice/vote arrays")
            continue
        if any(choice in (None, "") for choice in choices):
            errors.append(f"contest {index} contains an empty choice")
        invalid_votes = [vote for vote in votes if not valid_vote(vote)]
        if invalid_votes:
            errors.append(f"contest {index} contains invalid vote values")
        choice_count += len(choices)
        vote_count += len(votes)

    if data.get("contestCount") != len(contests):
        errors.append("contestCount does not match payload length")

    return {
        "county": county,
        "valid": not errors,
        "contests": len(contests),
        "choices": choice_count,
        "voteValues": vote_count,
        "errors": errors,
    }


def validate(config_path, staging_dir, max_age_seconds, now=None):
    config = load_json(config_path)
    enabled = [entry for entry in config.get("counties", []) if entry.get("enabled") is True]
    now = now or datetime.now(timezone.utc)
    results = []
    for entry in enabled:
        filename = entry["county"].lower().replace(" ", "-") + ".json"
        results.append(validate_snapshot(Path(staging_dir) / filename, entry, now, max_age_seconds))

    structural_valid = bool(results) and all(result["valid"] for result in results)
    general_source_ready = structural_valid and config.get("mode") == "live-general" and config.get("electionId") == "2026-fl-general"
    return {
        "schemaVersion": 1,
        "configElectionId": config.get("electionId"),
        "configMode": config.get("mode"),
        "structuralValidationPassed": structural_valid,
        "generalElectionSourceReady": general_source_ready,
        "publishesProductionData": False,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="collectors/clarity-counties.json")
    parser.add_argument("--staging", default="collector-staging/clarity")
    parser.add_argument("--max-age", type=int, default=900, help="Maximum snapshot age in seconds")
    args = parser.parse_args()

    report = validate(args.config, args.staging, args.max_age)
    print(json.dumps(report, indent=2))
    if not report["structuralValidationPassed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
