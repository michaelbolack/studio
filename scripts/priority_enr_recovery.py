import json
import os
from datetime import datetime, timezone

import fix_enr_summary as summary
import update_counties as core

OUT_DIR = "data"


def priority(entry):
    if entry.get("validationFailed") and "zero" in (entry.get("error") or "").lower():
        return 0
    return 1


def main():
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    items = [
        (county, entry)
        for county, entry in manifest.get("counties", {}).items()
        if not entry.get("connected") and "enr.electionsfl.org" in (entry.get("sourceUrl") or "")
    ]
    items.sort(key=lambda item: (priority(item[1]), item[0]))

    recovered = 0
    # Keep the live path bounded: zero-vote quarantines first, then at most two others.
    for county, entry in items[:4]:
        try:
            data = summary.fix_county(county, entry)
            if not data:
                continue
            manifest["counties"][county] = {
                "connected": True,
                "file": f"data/{core.slugify(county)}.json",
                "sourceUrl": entry.get("sourceUrl"),
                "races": len(data.get("races", [])),
                "adapter": "florida-enr-summary-priority",
            }
            recovered += 1
            print(f"PRIORITY ENR OK {county}: {len(data.get('races', []))} races")
        except Exception as e:
            print(f"PRIORITY ENR FAIL {county}: {e}")

    summary.rebuild_aggregates(manifest)
    manifest["priorityEnrRecovery"] = {
        "recovered": recovered,
        "attempted": [county for county, _ in items[:4]],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()
