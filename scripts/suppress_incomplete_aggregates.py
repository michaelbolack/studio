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
    data["races"] = []
    data["displayStatus"] = "withheld-incomplete"
    data["integrityMessage"] = (
        f"{label} candidate totals are withheld until the official aggregate is complete. "
        "IRC Media does not publish partial aggregate totals because they can misstate the leader."
    )
    data["generatedAt"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"AGGREGATE WITHHELD {label}: incomplete coverage")
    return had_races


def main():
    changed = 0
    changed += int(suppress(os.path.join(OUT_DIR, "statewide.json"), "Florida statewide"))
    changed += int(suppress(os.path.join(OUT_DIR, "district-9.json"), "Congressional District 9"))
    print(f"Aggregate integrity gate complete: {changed} partial result set(s) suppressed")


if __name__ == "__main__":
    main()
