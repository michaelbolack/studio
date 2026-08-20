import json
import os
import re
from datetime import datetime, timezone

import official_state_results as dos

OUT_DIR = "data"


def probe_party(party):
    lines, url = dos.fetch_party(party)
    rep_idx = dos.find_title(lines, ["United States Representative"])
    district_hits = []
    if rep_idx is not None:
        end = min(len(lines), rep_idx + 1200)
        for i in range(rep_idx + 1, end):
            raw = lines[i]
            compact = re.sub(r"\s+", "", raw.lower())
            if "district" in compact:
                district_hits.append({"offset": i - rep_idx, "text": raw})
    race = dos.district9_from_party(lines, party)
    return {
        "url": url,
        "lineCount": len(lines),
        "unitedStatesRepresentativeIndex": rep_idx,
        "districtLabels": district_hits[:80],
        "district9Parsed": bool(race),
        "district9CandidateCount": len((race or {}).get("candidates", [])),
        "district9Candidates": (race or {}).get("candidates", []),
        "representativeWindow": lines[rep_idx:rep_idx + 140] if rep_idx is not None else [],
    }


def main():
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except Exception:
        manifest = {}

    results = {}
    for party in ("REP", "DEM"):
        try:
            results[party] = probe_party(party)
            print(f"DOS D9 PROBE {party}: parsed={results[party]['district9Parsed']}")
        except Exception as e:
            results[party] = {"error": str(e)}
            print(f"DOS D9 PROBE FAIL {party}: {e}")

    manifest["officialDistrict9Probe"] = {
        "parties": results,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()
