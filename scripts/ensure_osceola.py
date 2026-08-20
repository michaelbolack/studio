import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import clarity_json_recovery as clarity
import vendor_adapters as va

OUT_DIR = "data"
COUNTY = "Osceola"
OFFICIAL_BRIDGE_URL = "https://vrcdn.electionsfl.org/StaticPages/osceola.html"
LEGACY_FALLBACK_URL = "https://results.enr.clarityelections.com/FL/Osceola/126781/web.345435/"


def discover_source_url():
    """Resolve Osceola's current official ENR target instead of hardcoding an election id."""
    errors = []
    try:
        r = va.fetch(OFFICIAL_BRIDGE_URL, 8)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            label = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).lower()
            href = urljoin(OFFICIAL_BRIDGE_URL, a["href"])
            if "election night results" in label and "clarityelections.com" in href.lower():
                return href, {"bridgeUrl": OFFICIAL_BRIDGE_URL, "discovered": True}
        for a in soup.find_all("a", href=True):
            href = urljoin(OFFICIAL_BRIDGE_URL, a["href"])
            if "results.enr.clarityelections.com/fl/osceola/" in href.lower():
                return href, {"bridgeUrl": OFFICIAL_BRIDGE_URL, "discovered": True}
        errors.append("official bridge contained no Osceola Clarity link")
    except Exception as e:
        errors.append(f"official bridge fetch failed: {e}")

    return LEGACY_FALLBACK_URL, {
        "bridgeUrl": OFFICIAL_BRIDGE_URL,
        "discovered": False,
        "discoveryErrors": errors,
    }


def bounded_recover(source_url):
    errors = []

    # Try the official Clarity structured XML first. The election root is derived
    # from the county's current official bridge target, so election-id changes do
    # not silently strand this required county.
    xml_urls = clarity.xml_endpoints(source_url)
    for endpoint in xml_urls[:2]:
        try:
            r = va.fetch(endpoint, 12)
            races = clarity.races_from_detail_xml(r.content)
            if va.valid_races(races):
                data = va.make_data(COUNTY, "Clarity/Scytl official detail XML results", source_url, races)
                data["dataEndpoints"] = [endpoint]
                return data
            errors.append(f"{endpoint}: no valid races")
        except Exception as e:
            errors.append(f"{endpoint}: {e}")

    # Short bounded JSON fallbacks from the same dynamically discovered root.
    for endpoint in clarity.json_endpoints(source_url)[:3]:
        try:
            r = va.fetch(endpoint, 6)
            payload = r.json()
            races = va.normalize_races(va.race_objects_from_json(payload))
            if va.valid_races(races):
                data = va.make_data(COUNTY, "Clarity/Scytl official JSON results", source_url, races)
                data["dataEndpoints"] = [endpoint]
                return data
            errors.append(f"{endpoint}: no valid races")
        except Exception as e:
            errors.append(f"{endpoint}: {e}")

    raise RuntimeError("No usable bounded Clarity XML/JSON contests; " + " | ".join(errors[-5:]))


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

    source_url, discovery = discover_source_url()
    try:
        data = bounded_recover(source_url)
        path = va.write_county(COUNTY, data)
        manifest["counties"][COUNTY] = {
            "connected": True,
            "file": path,
            "sourceUrl": source_url,
            "officialBridgeUrl": OFFICIAL_BRIDGE_URL,
            "races": len(data.get("races", [])),
            "adapter": "clarity-direct-required",
            "dataEndpoints": data.get("dataEndpoints", []),
        }
        manifest["osceolaIntegrityRecovery"] = {
            "connected": True,
            "sourceUrl": source_url,
            "discovery": discovery,
            "races": len(data.get("races", [])),
            "dataEndpoints": data.get("dataEndpoints", []),
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
        print(f"OSCEOLA RECOVERED: {len(data.get('races', []))} races from {source_url}")
    except Exception as e:
        manifest["counties"][COUNTY] = {
            "connected": False,
            "sourceUrl": source_url,
            "officialBridgeUrl": OFFICIAL_BRIDGE_URL,
            "error": "Required Osceola recovery failed: " + str(e),
        }
        manifest["osceolaIntegrityRecovery"] = {
            "connected": False,
            "sourceUrl": source_url,
            "discovery": discovery,
            "error": str(e),
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
        print(f"OSCEOLA FAIL: {e}")

    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()
