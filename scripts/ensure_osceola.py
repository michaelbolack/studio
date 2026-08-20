import json
import os
from datetime import datetime, timezone

import clarity_json_recovery as clarity
import vendor_adapters as va

OUT_DIR = "data"
COUNTY = "Osceola"
SOURCE_URL = "https://results.enr.clarityelections.com/FL/Osceola/126781/web.345435/"


def main():
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    entry = manifest.setdefault("counties", {}).get(COUNTY, {})
    existing_path = entry.get("file")
    if entry.get("connected") and existing_path and os.path.exists(existing_path):
        print("OSCEOLA OK: existing connected feed preserved")
        return

    try:
        data = clarity.recover(COUNTY, SOURCE_URL)
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
