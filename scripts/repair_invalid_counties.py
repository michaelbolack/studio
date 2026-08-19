import json, os
from datetime import datetime, timezone

from scripts import fix_enr_summary as fallback
from scripts import update_counties as core

OUT_DIR = "data"


def total_candidate_votes(data):
    return sum(
        int(c.get("votes") or 0)
        for race in data.get("races", [])
        for c in race.get("candidates", [])
        if not core.is_stats_choice(c.get("name", ""))
    )


def needs_repair(data):
    if not data or not data.get("races"):
        return True
    precincts_reporting = int(data.get("precinctsReporting") or 0)
    ballots_cast = int(data.get("ballotsCast") or 0)
    votes = total_candidate_votes(data)
    # A county with reported precincts or ballots cannot plausibly have zero
    # candidate votes across every contest. This usually means a stale/test CSV
    # or a vendor-specific column layout that the primary parser misread.
    return votes == 0 and (precincts_reporting > 0 or ballots_cast > 0)


def main():
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    repaired = 0
    quarantined = 0
    for county, entry in list(manifest.get("counties", {}).items()):
        if not entry.get("connected") or not entry.get("file"):
            continue
        try:
            with open(entry["file"]) as f:
                data = json.load(f)
        except Exception as e:
            entry["connected"] = False
            entry["error"] = f"Data validation failed: {e}"
            quarantined += 1
            continue

        if not needs_repair(data):
            continue

        print(f"INVALID {county}: reporting/ballots present but candidate vote total is zero")
        try:
            repaired_data = fallback.fix_county(county, entry)
            if repaired_data and total_candidate_votes(repaired_data) > 0:
                manifest["counties"][county] = {
                    "connected": True,
                    "file": f"data/{core.slugify(county)}.json",
                    "sourceUrl": entry.get("sourceUrl"),
                    "races": len(repaired_data.get("races", [])),
                    "adapter": "florida-enr-summary-repair",
                    "validated": True,
                }
                repaired += 1
                print(f"REPAIRED {county}: {len(repaired_data.get('races', []))} races")
            else:
                raise RuntimeError("summary fallback still produced zero candidate votes")
        except Exception as e:
            # Better to show a county as unavailable than publish a false 0-vote result.
            manifest["counties"][county] = {
                "connected": False,
                "sourceUrl": entry.get("sourceUrl"),
                "error": f"Quarantined invalid county data: {e}",
                "adapter": entry.get("adapter", "unknown"),
            }
            quarantined += 1
            print(f"QUARANTINED {county}: {e}")

    fallback.rebuild_aggregates(manifest)
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    connected = sum(1 for x in manifest.get("counties", {}).values() if x.get("connected"))
    print(f"Validation repaired {repaired}, quarantined {quarantined}; connected {connected}/{len(manifest.get('counties', {}))}")


if __name__ == "__main__":
    main()
