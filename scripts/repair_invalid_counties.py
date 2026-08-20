import json, os
from datetime import datetime, timezone

import fix_enr_summary as fallback
import update_counties as core
import vendor_adapters

OUT_DIR = "data"


def total_candidate_votes(data):
    return sum(
        int(c.get("votes") or 0)
        for race in data.get("races", [])
        for c in race.get("candidates", [])
        if not core.is_stats_choice(c.get("name", ""))
    )


def is_suspicious(data):
    votes = total_candidate_votes(data)
    reporting = int(data.get("precinctsReporting") or 0)
    ballots = int(data.get("ballotsCast") or 0)
    return votes == 0 and (reporting > 0 or ballots > 0)


def try_summary_repair(county, entry):
    try:
        fresh = fallback.fix_county(county, entry)
        if fresh and not is_suspicious(fresh) and total_candidate_votes(fresh) > 0:
            return fresh, "florida-enr-summary-repair"
    except Exception as e:
        print(f"SUMMARY REPAIR FAIL {county}: {e}")
    return None, None


def try_vendor_repair(county, entry):
    try:
        fresh, adapter = vendor_adapters.recover_one(county, entry)
        fresh["races"] = vendor_adapters.normalize_races(fresh.get("races", []))
        if vendor_adapters.valid_races(fresh["races"]) and not is_suspicious(fresh) and total_candidate_votes(fresh) > 0:
            vendor_adapters.write_county(county, fresh)
            return fresh, adapter + "-repair"
    except Exception as e:
        print(f"VENDOR REPAIR FAIL {county}: {e}")
    return None, None


def main():
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)
    repaired = 0
    invalid = 0
    for county, entry in list(manifest.get("counties", {}).items()):
        if not entry.get("connected") or not entry.get("file"):
            continue
        try:
            with open(entry["file"]) as f:
                data = json.load(f)
        except Exception as e:
            print(f"VALIDATE READ FAIL {county}: {e}")
            continue
        if not is_suspicious(data):
            continue
        print(f"SUSPICIOUS {county}: reporting={data.get('precinctsReporting')} ballots={data.get('ballotsCast')} candidateVotes=0")

        fresh, adapter = try_summary_repair(county, entry)
        if not fresh:
            # The original entry may already be marked as a Florida ENR source;
            # vendor recovery can use the same official URL with a different
            # extraction strategy rather than trusting the bad CSV.
            fresh, adapter = try_vendor_repair(county, entry)

        if fresh:
            entry["connected"] = True
            entry.pop("error", None)
            entry.pop("validationFailed", None)
            entry["adapter"] = adapter
            entry["races"] = len(fresh.get("races", []))
            repaired += 1
            print(f"REPAIRED {county}: {total_candidate_votes(fresh)} candidate votes via {adapter}")
            continue

        entry["connected"] = False
        entry["error"] = "Feed failed validation: precincts/ballots reported but candidate vote totals were zero"
        entry["validationFailed"] = True
        invalid += 1
        print(f"QUARANTINED {county}")

    fallback.rebuild_aggregates(manifest)
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    manifest["validation"] = {"repaired": repaired, "quarantined": invalid}
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Validation complete: repaired={repaired}, quarantined={invalid}")


if __name__ == "__main__":
    main()
