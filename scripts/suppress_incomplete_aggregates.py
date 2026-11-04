import json
import os
from datetime import datetime, timezone

OUT_DIR = "data"


def authoritative_complete(data):
    source = (data.get("source") or "").lower()
    if "florida department of state" in source:
        return True
    return bool(data.get("coverageComplete"))


def suppress(path, label):
    if not os.path.exists(path):
        return False
    with open(path) as f:
        data = json.load(f)

    if authoritative_complete(data):
        data.pop("displayStatus", None)
        data.pop("integrityMessage", None)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"AGGREGATE OK {label}: authoritative/complete")
        return False

    had_races = bool(data.get("races"))
    data["displayStatus"] = "partial-live"
    included = data.get("countiesIncluded")
    discovered = data.get("countiesDiscovered") or data.get("countiesExpected")
    coverage = f"{included}/{discovered} counties included" if included is not None and discovered else "partial county coverage"
    data["integrityMessage"] = (
        f"{label} is updating live from official county election-night feeds ({coverage}). "
        "Totals are partial and may change as additional counties report."
    )
    data["generatedAt"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"AGGREGATE PARTIAL {label}: incomplete coverage retained for live election-night display")
    return had_races


def main():
    changed = 0
    changed += int(suppress(os.path.join(OUT_DIR, "statewide.json"), "Florida statewide"))
    changed += int(suppress(os.path.join(OUT_DIR, "district-9.json"), "Congressional District 9"))
    print(f"Aggregate integrity gate complete: {changed} partial result set(s) retained with live coverage labels")


if __name__ == "__main__":
    main()
