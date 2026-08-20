import json
import os
import subprocess
from datetime import datetime, timezone

OUT_DIR = "data"
MANIFEST = os.path.join(OUT_DIR, "manifest.json")


def clean_num(v):
    try:
        return int(float(str(v).replace(",", "").strip()))
    except Exception:
        return 0


def county_file_is_sane(path):
    if not path or not os.path.exists(path):
        return False
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        return False
    races = data.get("races") or []
    if not races or len(races) > 300:
        return False
    candidates = 0
    votes = 0
    for race in races:
        for cand in race.get("candidates") or []:
            candidates += 1
            votes += clean_num(cand.get("votes"))
    if candidates == 0:
        return False
    reporting = clean_num(data.get("precinctsReporting"))
    ballots = clean_num(data.get("ballotsCast"))
    if (reporting > 0 or ballots > 0) and votes <= 0:
        return False
    return True


def recent_manifests(limit=25):
    try:
        commits = subprocess.check_output(
            ["git", "log", f"-n{limit}", "--format=%H", "--", "data/manifest.json"],
            text=True,
        ).splitlines()
    except Exception:
        return []
    out = []
    for sha in commits:
        try:
            raw = subprocess.check_output(
                ["git", "show", f"{sha}:data/manifest.json"], text=True, stderr=subprocess.DEVNULL
            )
            out.append((sha, json.loads(raw)))
        except Exception:
            continue
    return out


def main():
    with open(MANIFEST) as f:
        current = json.load(f)

    history = recent_manifests()
    restored = []
    for county, entry in list((current.get("counties") or {}).items()):
        if entry.get("connected"):
            continue
        for sha, old in history:
            old_entry = ((old.get("counties") or {}).get(county) or {})
            if not old_entry.get("connected"):
                continue
            path = old_entry.get("file")
            if not county_file_is_sane(path):
                continue
            restored_entry = dict(old_entry)
            restored_entry["lastKnownGood"] = True
            restored_entry["refreshFailed"] = True
            restored_entry["refreshError"] = entry.get("error")
            restored_entry["restoredFromCommit"] = sha
            restored_entry["restoredAt"] = datetime.now(timezone.utc).isoformat()
            current["counties"][county] = restored_entry
            restored.append(county)
            break

    current["lastKnownGoodRestore"] = {
        "restored": restored,
        "count": len(restored),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    current["generatedAt"] = datetime.now(timezone.utc).isoformat()
    with open(MANIFEST, "w") as f:
        json.dump(current, f, indent=2)
    print(f"Restored {len(restored)} last-known-good counties: {', '.join(restored)}")


if __name__ == "__main__":
    main()
