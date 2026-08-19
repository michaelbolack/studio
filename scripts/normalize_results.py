import json, os, re
from scripts import update_counties as core

OUT_DIR = "data"

ALIASES = {
    "bryondonalds": ("byrondonalds", "Byron Donalds"),
    "davidjjolly": ("davidjolly", "David Jolly"),
    "djolly": ("davidjolly", "David Jolly"),
}


def compact(name):
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def is_stats(name):
    s = re.sub(r"[^a-z]", "", (name or "").lower())
    return s.startswith("undervote") or s.startswith("overvote")


def normalize_name(name):
    raw = (name or "").strip()
    key = compact(raw)
    if "jolly" in raw.lower() and "graham" in raw.lower():
        return "davidjolly", "David Jolly"
    if key in ALIASES:
        return ALIASES[key]
    return key, raw


def clean_race(race):
    merged = {}
    for c in race.get("candidates", []):
        name = c.get("name", "")
        if not name or is_stats(name):
            continue
        key, display = normalize_name(name)
        if not key:
            continue
        party = (c.get("party") or "NON").upper()
        item = merged.setdefault((key, party), {"name": display, "party": party, "votes": 0})
        item["votes"] += int(c.get("votes") or 0)
    candidates = list(merged.values())
    total = sum(c["votes"] for c in candidates)
    for c in candidates:
        c["percent"] = round((c["votes"] / total * 100) if total else 0, 2)
    race["candidates"] = candidates
    return race


def clean_county_file(path):
    with open(path) as f:
        data = json.load(f)
    if "races" not in data:
        return None
    data["races"] = [clean_race(r) for r in data.get("races", [])]
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return data


def main():
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    county_data = []
    cleaned = 0
    for county, entry in manifest.get("counties", {}).items():
        if not entry.get("connected") or entry.get("validationFailed") or not entry.get("file"):
            continue
        path = entry["file"]
        if not os.path.exists(path):
            continue
        data = clean_county_file(path)
        if data:
            county_data.append(data)
            cleaned += 1

    statewide = core.build_statewide(county_data, len(manifest.get("counties", {})))
    district9 = core.build_cd9(county_data)
    manifest["statewide"] = {
        "file": "data/statewide.json",
        "countiesIncluded": statewide["countiesIncluded"],
        "countiesDiscovered": statewide["countiesDiscovered"],
        "coverageComplete": statewide["coverageComplete"],
    }
    manifest["district9"] = {
        "file": "data/district-9.json",
        "countiesIncluded": district9["countiesIncluded"],
        "countiesExpected": district9["countiesExpected"],
        "coverageComplete": district9["coverageComplete"],
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Normalized {cleaned} county result files and rebuilt aggregates")


if __name__ == "__main__":
    main()
