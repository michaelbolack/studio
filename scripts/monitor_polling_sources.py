#!/usr/bin/env python3
"""Non-publishing daily monitor for approved national polling sources."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
USER_AGENT = "IRC-Media-Election-Center/1.0 (polling source monitor)"
VOTEHUB_QUERIES = {
    "trump-job-approval": {
        "poll_type": "approval",
        "subject": "donald-trump",
    },
    "national-generic-ballot": {
        "poll_type": "generic-ballot",
    },
    "trump-favorability": {
        "poll_type": "favorability",
        "subject": "donald-trump",
    },
}
RASMUSSEN_WATCH_URL = (
    "https://www.rasmussenreports.com/public_content/politics/"
    "obama_administration/daily_Presidential_tracking_poll"
)
EMERSON_FEED_URL = "https://emersoncollegepolling.com/feed/"


def fetch(url: str) -> tuple[str, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return response.geturl(), response.read().decode("utf-8", errors="replace")


def known_source_urls() -> set[str]:
    polling = json.loads((DATA / "polling.json").read_text(encoding="utf-8"))
    polls = list(polling.get("races", [])) + list(polling.get("nationalIndicators", []))
    return {str(poll.get("sourceUrl", "")).rstrip("/") for poll in polls}


def check_votehub() -> dict:
    indicators = {}
    for race_id, params in VOTEHUB_QUERIES.items():
        url = "https://api.votehub.com/polls?" + urlencode(params)
        try:
            final_url, body = fetch(url)
            payload = json.loads(body)
            polls = payload.get("polls", []) if isinstance(payload, dict) else payload
            if not isinstance(polls, list):
                raise ValueError("response is neither an array nor a polls wrapper")
            end_dates = [
                str(poll.get("end_date"))
                for poll in polls
                if isinstance(poll, dict) and poll.get("end_date")
            ]
            valid = [
                poll for poll in polls
                if isinstance(poll, dict)
                and poll.get("id")
                and poll.get("pollster")
                and isinstance(poll.get("sample_size"), int)
                and isinstance(poll.get("answers"), list)
                and len(poll["answers"]) >= 2
                and str(poll.get("url", "")).startswith("https://")
            ]
            indicators[race_id] = {
                "reachable": True,
                "finalUrl": final_url,
                "records": len(polls),
                "validRecords": len(valid),
                "latestEndDate": max(end_dates) if end_dates else None,
            }
        except Exception as error:
            indicators[race_id] = {"reachable": False, "error": str(error)}
    return {"sourceId": "votehub", "indicators": indicators}


def check_rasmussen(known: set[str]) -> dict:
    try:
        final_url, body = fetch(RASMUSSEN_WATCH_URL)
        match = re.search(
            r"(\d{1,3})% of Likely U\.S\. Voters approve.*?"
            r"(\d{1,3})%\)? disapprove",
            re.sub(r"<[^>]+>", " ", body),
            flags=re.IGNORECASE | re.DOTALL,
        )
        normalized = final_url.rstrip("/")
        return {
            "sourceId": "rasmussen-reports",
            "reachable": True,
            "finalUrl": final_url,
            "newCandidate": normalized not in known,
            "headlineValuesDetected": bool(match),
            "approve": int(match.group(1)) if match else None,
            "disapprove": int(match.group(2)) if match else None,
        }
    except Exception as error:
        return {"sourceId": "rasmussen-reports", "reachable": False, "error": str(error)}


def check_emerson(known: set[str]) -> dict:
    try:
        final_url, body = fetch(EMERSON_FEED_URL)
        links = re.findall(r"<link>(https://emersoncollegepolling\.com/[^<]+)</link>", body)
        national = [link.rstrip("/") for link in links if "national-poll" in link]
        candidates = [link for link in national if link not in known]
        return {
            "sourceId": "emerson-college-polling",
            "reachable": True,
            "finalUrl": final_url,
            "nationalLinksDetected": len(national),
            "newCandidates": candidates[:10],
        }
    except Exception as error:
        return {
            "sourceId": "emerson-college-polling",
            "reachable": False,
            "error": str(error),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="polling-source-monitor-report.json")
    args = parser.parse_args()

    known = known_source_urls()
    sources = [
        check_votehub(),
        check_rasmussen(known),
        check_emerson(known),
    ]
    new_candidate = any(
        source.get("newCandidate") is True or bool(source.get("newCandidates"))
        for source in sources
    )
    report = {
        "schemaVersion": 1,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "mode": "monitor-only-no-publishing",
        "newPollCandidateDetected": new_candidate,
        "sources": sources,
    }
    output = Path(args.output)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
