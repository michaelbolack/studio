#!/usr/bin/env python3
"""Collect public Clarity election JSON through a normal browser session.

This collector intentionally writes only to a staging directory. It never
publishes election results and never edits production data files. A separate
validator/publisher must approve staged snapshots before they reach the
Election Center.
"""

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_json_write(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def body_text(page):
    text = page.locator("body").inner_text(timeout=15000).strip()
    if not text:
        raise RuntimeError("browser returned an empty body")
    return text


def parse_version(text):
    match = re.fullmatch(r"\s*(\d{3,12})\s*", text)
    if not match:
        raise RuntimeError(f"current_ver.txt did not contain one numeric version: {text[:120]!r}")
    return match.group(1)


def validate_summary(payload):
    if not isinstance(payload, list) or not payload:
        raise RuntimeError("summary JSON is not a non-empty contest list")
    for i, contest in enumerate(payload):
        if not isinstance(contest, dict):
            raise RuntimeError(f"contest {i} is not an object")
        if not contest.get("C"):
            raise RuntimeError(f"contest {i} has no contest name")
        choices = contest.get("CH")
        votes = contest.get("V")
        if not isinstance(choices, list) or not isinstance(votes, list) or len(choices) != len(votes):
            raise RuntimeError(f"contest {contest.get('C')!r} has invalid candidate/vote arrays")
    return True


def collect_one(context, entry, output_dir):
    county = entry["county"]
    host = entry["host"].rstrip("/") + "/"
    state = entry.get("state", "FL")
    jurisdiction = entry.get("jurisdiction", county)
    election_id = str(entry["electionId"])
    root = urljoin(host, f"{state}/{jurisdiction}/{election_id}/")
    version_url = urljoin(root, "current_ver.txt")

    page = context.new_page()
    try:
        page.goto(version_url, wait_until="domcontentloaded", timeout=30000)
        version = parse_version(body_text(page))

        summary_url = urljoin(root, f"{version}/json/en/summary.json")
        page.goto(summary_url, wait_until="domcontentloaded", timeout=30000)
        raw = body_text(page)
        payload = json.loads(raw)
        validate_summary(payload)

        envelope = {
            "schemaVersion": 1,
            "collector": "clarity-browser-session",
            "county": county,
            "electionId": election_id,
            "clarityVersion": version,
            "versionUrl": version_url,
            "sourceDataUrl": summary_url,
            "collectedAt": utcnow(),
            "contestCount": len(payload),
            "payload": payload,
        }
        atomic_json_write(Path(output_dir) / f"{county.lower().replace(' ', '-')}.json", envelope)
        return {
            "county": county,
            "ok": True,
            "version": version,
            "contests": len(payload),
            "sourceDataUrl": summary_url,
        }
    finally:
        page.close()


def collect_cycle(context, config, output_dir):
    results = []
    for entry in config.get("counties", []):
        if entry.get("enabled") is not True:
            continue
        try:
            results.append(collect_one(context, entry, output_dir))
        except Exception as exc:
            results.append({"county": entry.get("county"), "ok": False, "error": str(exc)})

    status = {
        "schemaVersion": 1,
        "collectedAt": utcnow(),
        "electionId": config.get("electionId"),
        "results": results,
        "allEnabledCollectorsHealthy": bool(results) and all(r.get("ok") for r in results),
    }
    atomic_json_write(Path(output_dir) / "collector-status.json", status)
    print(json.dumps(status, indent=2), flush=True)
    return status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="collectors/clarity-counties.json")
    parser.add_argument("--output", default="collector-staging/clarity")
    parser.add_argument("--profile", default=".clarity-browser-profile")
    parser.add_argument("--interval", type=int, default=300, help="Seconds between cycles; minimum 60")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--headless", action="store_true", help="Use only after confirming the public host accepts headless sessions")
    args = parser.parse_args()

    config = load_json(args.config)
    enabled = [c for c in config.get("counties", []) if c.get("enabled") is True]
    if not enabled:
        raise SystemExit("No Clarity counties are enabled in the collector config.")
    for entry in enabled:
        if not entry.get("electionId"):
            raise SystemExit(f"{entry.get('county')}: electionId is required before collection can start.")

    interval = max(60, args.interval)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=args.profile,
            headless=args.headless,
            viewport={"width": 1280, "height": 900},
        )
        try:
            while True:
                collect_cycle(context, config, args.output)
                if args.once:
                    break
                time.sleep(interval)
        finally:
            context.close()


if __name__ == "__main__":
    main()
