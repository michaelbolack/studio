import json
import os
from datetime import datetime, timezone

import direct_text_summary_recovery as controls
import fix_enr_summary as summary
import update_counties as core

OUT_DIR = "data"


def priority(entry):
    error = (entry.get("error") or "").lower()
    if entry.get("validationFailed") or "zero" in error or "candidate vote totals" in error:
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

    recovered = []
    errors = {}
    diagnostics = {}
    attempted = [county for county, _ in items[:4]]

    # Keep the live path bounded. The controls parser is now proven on Flagler
    # and Nassau, and works directly from the official summary page rather than
    # depending on the county exposing a /Reports CSV directory.
    for county, entry in items[:4]:
        try:
            data, diag = controls.recover(county, entry)
            diagnostics[county] = diag
            manifest["counties"][county] = {
                "connected": True,
                "file": f"data/{core.slugify(county)}.json",
                "sourceUrl": entry.get("sourceUrl"),
                "races": len(data.get("races", [])),
                "adapter": "florida-enr-summary-controls-priority",
            }
            recovered.append(county)
            print(f"PRIORITY CONTROL ENR OK {county}: {len(data.get('races', []))} races")
        except Exception as e:
            errors[county] = str(e)
            diagnostics[county] = getattr(e, "diagnostics", {"exception": repr(e)})
            print(f"PRIORITY CONTROL ENR FAIL {county}: {e}")

    summary.rebuild_aggregates(manifest)
    manifest["priorityEnrRecovery"] = {
        "recovered": recovered,
        "attempted": attempted,
        "errors": errors,
        "diagnostics": diagnostics,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()
