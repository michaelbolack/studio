import json
import os
from datetime import datetime, timezone

import direct_text_summary_recovery as controls
import fix_enr_summary as summary
import update_counties as core

OUT_DIR = "data"
BATCH_SIZE = 8


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
    attempted = [county for county, _ in items[:BATCH_SIZE]]

    # The controls parser is proven against the official Florida ENR summary
    # pages. Keep the live path bounded, but recover enough counties per cycle
    # to clear the remaining ENR backlog quickly without weakening validation.
    for county, entry in items[:BATCH_SIZE]:
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
        "batchSize": BATCH_SIZE,
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
