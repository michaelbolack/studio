import json, os
from datetime import datetime, timezone

OUT_DIR = "data"
MAX_REASONABLE_RACES = 250


def total_candidate_votes(data):
    total = 0
    rows = 0
    for race in data.get("races", []) or []:
        for cand in race.get("candidates", []) or []:
            if cand.get("name"):
                rows += 1
            try:
                total += int(cand.get("votes") or 0)
            except Exception:
                pass
    return rows, total


def main():
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    quarantined = []
    checked = 0
    for county, entry in manifest.get("counties", {}).items():
        if not entry.get("connected"):
            continue
        checked += 1
        path = entry.get("file")
        reason = None
        data = None

        if not path or not os.path.exists(path):
            reason = "connected county has no readable result file"
        else:
            try:
                with open(path) as f:
                    data = json.load(f)
            except Exception as e:
                reason = f"result file unreadable: {e}"

        if data is not None:
            races = data.get("races", []) or []
            if not races:
                reason = "result file contains no races"
            elif len(races) > MAX_REASONABLE_RACES:
                reason = f"implausible race count: {len(races)}"
            else:
                rows, votes = total_candidate_votes(data)
                if rows < 2:
                    reason = f"too few candidate rows: {rows}"
                elif votes == 0 and (int(data.get("ballotsCast") or 0) > 0 or int(data.get("precinctsReporting") or 0) > 0):
                    reason = "reporting/ballots present but candidate vote totals are zero"

        if reason:
            entry["connected"] = False
            entry["validationFailed"] = True
            entry["error"] = "Final integrity gate: " + reason
            quarantined.append({"county": county, "reason": reason})
            print(f"FINAL QUARANTINE {county}: {reason}")
        else:
            entry.pop("validationFailed", None)
            if str(entry.get("error", "")).startswith("Final integrity gate:"):
                entry.pop("error", None)

    manifest["finalIntegrity"] = {
        "checked": checked,
        "quarantined": len(quarantined),
        "details": quarantined,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    connected = sum(1 for e in manifest.get("counties", {}).values() if e.get("connected"))
    total = len(manifest.get("counties", {}))
    print(f"Final integrity gate: connected={connected}/{total}, quarantined={len(quarantined)}")


if __name__ == "__main__":
    main()
