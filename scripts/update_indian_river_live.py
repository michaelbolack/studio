#!/usr/bin/env python3
"""Fast-path Indian River County election-night updater.

Bypasses the statewide 67-county publish pipeline and refreshes only
data/indian-river.json from the official Florida ENR source.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import update_counties as uc  # noqa: E402

OUT = ROOT / "data" / "indian-river.json"

def main() -> int:
    counties = uc.discover_counties()
    summary_url = counties.get("Indian River")
    if not summary_url:
        raise RuntimeError("Indian River General Election ENR source not discovered")

    data = uc.update_one("Indian River", summary_url)

    if data.get("electionDate") != uc.ELECTION_DATE:
        raise RuntimeError(f"Wrong election date: {data.get('electionDate')}")
    races = data.get("races") or []
    if len(races) < 20:
        raise RuntimeError(f"Indian River race set incomplete: {len(races)} races")

    # update_one writes to data/ relative to CWD; normalize to the repo path.
    written = ROOT / "data" / "indian-river.json"
    if not written.exists():
        raise RuntimeError("Indian River output was not written")

    current = json.loads(written.read_text(encoding="utf-8"))
    print(json.dumps({
        "sourceUrl": current.get("sourceUrl"),
        "csvUrl": current.get("csvUrl"),
        "lastUpdated": current.get("lastUpdated"),
        "ballotsCast": current.get("ballotsCast"),
        "precinctsReporting": current.get("precinctsReporting"),
        "precinctsTotal": current.get("precinctsTotal"),
        "races": len(current.get("races") or []),
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
