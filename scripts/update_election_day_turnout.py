#!/usr/bin/env python3
import json, re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "election-day-turnout.json"
TZ = ZoneInfo("America/New_York")
SOURCES = [
    "https://floridaelectionwatch.gov/ElectionDayTurnout",
    "https://floridaelectionwatch.gov/CountyReportingStatus",
]

def clean(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()

def num(s):
    s = re.sub(r"[^0-9.-]", "", clean(s))
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None

def pct(s):
    s = re.sub(r"[^0-9.-]", "", clean(s))
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None

def norm_header(s):
    return re.sub(r"[^a-z0-9]+", " ", clean(s).lower()).strip()

def fetch_table():
    last_error = None
    headers = {
        "User-Agent": "IRC-Media-Election-Center/1.0 (+https://www.ircmedia.net/election-center)",
        "Accept": "text/html,application/xhtml+xml",
    }
    for url in SOURCES:
        try:
            r = requests.get(url, headers=headers, timeout=25)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            for table in soup.find_all("table"):
                rows = table.find_all("tr")
                if not rows:
                    continue
                head = [norm_header(x.get_text(" ", strip=True)) for x in rows[0].find_all(["th","td"])]
                joined = " | ".join(head)
                if "county" in joined and ("turnout" in joined or "registered voters" in joined):
                    return url, head, rows[1:]
        except Exception as e:
            last_error = e
    raise RuntimeError(f"Unable to fetch Florida Election Watch turnout table: {last_error}")

def main():
    source_url, headers, rows = fetch_table()
    counties = []
    for row in rows:
        cells = [clean(x.get_text(" ", strip=True)) for x in row.find_all(["th","td"])]
        if not cells or len(cells) < 3:
            continue
        record = dict(zip(headers, cells))
        county = record.get("county soe website") or record.get("county") or cells[0]
        county = re.sub(r"\s+County$", "", clean(county), flags=re.I)
        if not county or county.lower() in {"total","statewide","florida"}:
            continue

        turnout = None
        eligible = None
        turnout_pct = None
        precinct_reporting = None
        precinct_completed = None
        ev_completed = None
        vbm_completed = None

        for h, v in record.items():
            if h == "voter turnout" or h.endswith(" voter turnout"):
                turnout = num(v)
            elif "eligible active registered voters" in h or h == "eligible registered voters":
                eligible = num(v)
            elif "turnout percentage" in h:
                turnout_pct = pct(v)
            elif h == "precincts reporting":
                precinct_reporting = pct(v)
            elif h == "precincts completed":
                precinct_completed = pct(v)
            elif "early voting ballots completed" in h:
                ev_completed = num(v)
            elif "vote by mail ballots completed" in h or "vote-by-mail ballots completed" in h:
                vbm_completed = num(v)

        counties.append({
            "county": county,
            "turnout": turnout,
            "eligibleActiveRegisteredVoters": eligible,
            "turnoutPercentage": turnout_pct,
            "precinctsReportingPercentage": precinct_reporting,
            "precinctsCompletedPercentage": precinct_completed,
            "earlyVotingBallotsCompleted": ev_completed,
            "voteByMailBallotsCompleted": vbm_completed,
        })

    if len(counties) < 60:
        raise RuntimeError(f"Only parsed {len(counties)} counties; refusing to publish incomplete turnout data")

    total_turnout = sum(x["turnout"] or 0 for x in counties)
    total_eligible = sum(x["eligibleActiveRegisteredVoters"] or 0 for x in counties)
    statewide_pct = round((total_turnout / total_eligible * 100), 2) if total_eligible else None

    indian = next((x for x in counties if x["county"].lower() == "indian river"), None)
    payload = {
        "schemaVersion": 1,
        "election": "2026 General Election",
        "electionDate": "2026-11-03",
        "generatedAt": datetime.now(TZ).isoformat(),
        "source": "Florida Election Watch",
        "sourceUrl": source_url,
        "note": "Election Day turnout figures are administrative participation counts, not vote results.",
        "statewide": {
            "turnout": total_turnout,
            "eligibleActiveRegisteredVoters": total_eligible,
            "turnoutPercentage": statewide_pct,
        },
        "indianRiver": indian,
        "counties": sorted(counties, key=lambda x: x["county"]),
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source": source_url, "counties": len(counties), "indianRiver": indian, "statewide": payload["statewide"]}, indent=2))

if __name__ == "__main__":
    main()
