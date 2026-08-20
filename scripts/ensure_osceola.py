import json
import os
from datetime import datetime, timezone

import clarity_json_recovery as clarity
import vendor_adapters as va

OUT_DIR = "data"
COUNTY = "Osceola"
SOURCE_URL = "https://results.enr.clarityelections.com/FL/Osceola/126781/web.345435/"


def bounded_recover():
    errors = []

    # Modern Clarity elections normally expose the complete official contest
    # dataset in detailxml.zip. Try that first so this required county cannot
    # spend the live publisher's entire budget cycling through speculative JSON.
    xml_urls = clarity.xml_endpoints(SOURCE_URL)
    if xml_urls:
        endpoint = xml_urls[0]
        try:
            r = va.fetch(endpoint, 12)
            races = clarity.races_from_detail_xml(r.content)
            if va.valid_races(races):
                data = va.make_data(COUNTY, "Clarity/Scytl official detail XML results", SOURCE_URL, races)
                data["dataEndpoints"] = [endpoint]
                return data
        except Exception as e:
            errors.append(f"{endpoint}: {e}")

    # Two high-value JSON fallbacks only. Keep each request short and bounded.
    for endpoint in clarity.json_endpoints(SOURCE_URL)[:2]:
        try:
            r = va.fetch(endpoint, 6)
            payload = r.json()
            races = va.normalize_races(va.race_objects_from_json(payload))
            if va.valid_races(races):
                data = va.make_data(COUNTY, "Clarity/Scytl official JSON results", SOURCE_URL, races)
                data["dataEndpoints"] = [endpoint]
                return data
        except Exception as e:
            errors.append(f"{endpoint}: {e}")

    raise RuntimeError("No usable bounded Clarity XML/JSON contests; " + " | ".join(errors[-3:]))


def main():
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    entry = manifest.setdefault("counties", {}).get(COUNTY, {})
    existing_path = entry.get("file")
    if entry.get("connected") and existing_path and os.path.exists(existing_path):
        manifest["osceolaIntegrityRecovery"] = {
            "connected": True,
            "preservedExisting": True,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        print("OSCEOLA OK: existing connected feed preserved")
        return

    try:
        data = bounded_recover()
        path = va.write_county(COUNTY, data)
        manifest["counties"][COUNTY] = {
            "connected": True,
            "file": path,
            "sourceUrl": SOURCE_URL,
            "races": len(data.get("races", [])),
            "adapter": "clarity-direct-required",
            "dataEndpoints": data.get("dataEndpoints", []),
        }
        manifest["osceolaIntegrityRecovery"] = {
            "connected": True,
            "races": len(data.get("races", [])),
            "dataEndpoints": data.get("dataEndpoints", []),
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
        print(f"OSCEOLA RECOVERED: {len(data.get('races', []))} races")
    except Exception as e:
        manifest["counties"][COUNTY] = {
            "connected": False,
            "sourceUrl": SOURCE_URL,
            "error": "Required Osceola recovery failed: " + str(e),
        }
        manifest["osceolaIntegrityRecovery"] = {
            "connected": False,
            "error": str(e),
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
        print(f"OSCEOLA FAIL: {e}")

    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()
