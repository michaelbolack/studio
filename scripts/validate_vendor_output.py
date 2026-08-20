import json, os, re
from datetime import datetime, timezone

OUT_DIR = "data"
MAX_REASONABLE_RACES = 250


def candidate_key(name):
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def race_signature(race):
    name = re.sub(r"\s+", " ", (race.get("name") or "").strip().lower())
    cands = tuple(sorted(candidate_key(c.get("name")) for c in race.get("candidates", []) if candidate_key(c.get("name"))))
    return name, cands


def validate_county(path):
    with open(path) as f:
        data = json.load(f)
    races = data.get("races", []) or []
    if not races:
        return False, "no races"
    if len(races) > MAX_REASONABLE_RACES:
        return False, f"implausible race count: {len(races)}"

    sigs = [race_signature(r) for r in races]
    sigs = [s for s in sigs if s[0] and s[1]]
    if not sigs:
        return False, "no usable race signatures"
    unique = len(set(sigs))
    duplicate_ratio = 1 - (unique / len(sigs))
    if duplicate_ratio > 0.35:
        return False, f"excess duplicate contests: {duplicate_ratio:.1%}"

    candidate_rows = 0
    positive_votes = 0
    for race in races:
        for cand in race.get("candidates", []) or []:
            if cand.get("name"):
                candidate_rows += 1
            try:
                if int(cand.get("votes") or 0) > 0:
                    positive_votes += 1
            except Exception:
                pass
    if candidate_rows < 2:
        return False, "too few candidate rows"
    if positive_votes == 0 and (int(data.get("ballotsCast") or 0) > 0 or int(data.get("precinctsReporting") or 0) > 0):
        return False, "reporting/ballots present but candidate votes are zero"
    return True, "ok"


def main():
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    quarantined = []
    checked = 0
    for county, entry in manifest.get("counties", {}).items():
        adapter = (entry.get("adapter") or "").lower()
        if not entry.get("connected") or not entry.get("file"):
            continue
        if not any(tag in adapter for tag in ("vendor", "enhanced", "clarity", "direct")):
            continue
        checked += 1
        try:
            ok, reason = validate_county(entry["file"])
        except Exception as e:
            ok, reason = False, f"validation read error: {e}"
        if not ok:
            entry["connected"] = False
            entry["validationFailed"] = True
            entry["error"] = "Vendor recovery failed sanity validation: " + reason
            quarantined.append({"county": county, "reason": reason})
            print(f"VENDOR QUARANTINE {county}: {reason}")
        else:
            entry.pop("validationFailed", None)
            if str(entry.get("error", "")).startswith("Vendor recovery failed sanity validation"):
                entry.pop("error", None)
            print(f"VENDOR VALID {county}: {entry.get('races')} races via {entry.get('adapter')}")

    manifest["vendorValidation"] = {
        "checked": checked,
        "quarantined": len(quarantined),
        "details": quarantined,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Vendor validation complete: checked={checked} quarantined={len(quarantined)}")


if __name__ == "__main__":
    main()
