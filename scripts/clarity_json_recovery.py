import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urljoin

import vendor_adapters as va
import fix_enr_summary as enr_summary

OUT_DIR = "data"


def election_root(url):
    clean = (url or "").split("#", 1)[0]
    # Modern Clarity URLs: .../<election-id>/web.<build>/
    m = re.search(r"^(.*?/\d{3,9}/)(?:web\.[^/]+/?)$", clean, re.I)
    if m:
        return m.group(1)
    m = re.search(r"^(.*?/\d{3,9}/)", clean, re.I)
    return m.group(1) if m else clean.rsplit("/", 1)[0] + "/"


def json_endpoints(url):
    root = election_root(url)
    rels = [
        "json/en/summary.json",
        "json/en/election.json",
        "json/en/electionsettings.json",
        "json/en/contests.json",
        "json/en/results.json",
        "json/en/contest.json",
        "json/summary.json",
        "json/results.json",
    ]
    return [urljoin(root, r) for r in rels]


def recover(county, url):
    errors = []
    races = []
    used = []
    for endpoint in json_endpoints(url):
        try:
            r = va.fetch(endpoint, 35)
            payload = r.json()
            found = va.normalize_races(va.race_objects_from_json(payload))
            if found:
                races.extend(found)
                used.append(endpoint)
        except Exception as e:
            errors.append(f"{endpoint}: {e}")

    races = va.normalize_races(races)
    if not va.valid_races(races):
        raise RuntimeError("No usable Clarity JSON contests; " + " | ".join(errors[-5:]))

    data = va.make_data(county, "Clarity/Scytl official JSON results", url, races)
    data["dataEndpoints"] = used
    return data


def main():
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    recovered = 0
    failures = []
    for county, entry in list(manifest.get("counties", {}).items()):
        if entry.get("connected"):
            continue
        url = entry.get("sourceUrl") or ""
        if "clarityelections.com" not in url.lower() and "votepinellas.gov" not in url.lower():
            continue
        try:
            data = recover(county, url)
            path = va.write_county(county, data)
            manifest["counties"][county] = {
                "connected": True,
                "file": path,
                "sourceUrl": url,
                "races": len(data.get("races", [])),
                "adapter": "clarity-json",
                "dataEndpoints": data.get("dataEndpoints", []),
            }
            recovered += 1
            print(f"CLARITY JSON OK {county}: {len(data.get('races', []))} races")
        except Exception as e:
            failures.append({"county": county, "error": str(e)})
            print(f"CLARITY JSON FAIL {county}: {e}")

    enr_summary.rebuild_aggregates(manifest)
    manifest["clarityJsonRecovery"] = {
        "recovered": recovered,
        "failures": failures,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Clarity JSON recovery: +{recovered}")


if __name__ == "__main__":
    main()
