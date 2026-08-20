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

# Human-observed validation fixture from the official Osceola Clarity page.
# These values are NEVER used as production results. They only verify that an
# official machine-readable extraction corresponds to the same live contest.
CD9_REP_CHECKSUM = {
    "benbutler": 1855,
    "marcuscarter": 628,
    "thomasechalifouxjr": 4664,
    "dangreen": 2515,
    "jorgemartinez": 2857,
    "steverance": 327,
    "justinstory": 1079,
}
CD9_REP_TOTAL = 13925


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


def current_version_root(source_url):
    """Return Clarity's immutable current report-version root.

    Modern Clarity URLs have two different version concepts: the web frontend
    build (for example web.345435) and the election-result publication version
    (a numeric directory such as 373172). Structured JSON/XML is served under
    the numeric publication version, discoverable via current_ver.txt.
    """
    root = clarity.election_root(source_url)
    endpoint = urljoin(root, "current_ver.txt")
    r = va.fetch(endpoint, 8)
    version = (r.text or "").strip().splitlines()[0].strip()
    if not re.fullmatch(r"[0-9]{3,12}", version):
        raise RuntimeError(f"unexpected Clarity current_ver.txt value: {version!r}")
    return urljoin(root, version + "/"), endpoint, version


def versioned_endpoints(version_root):
    xml_urls = [
        urljoin(version_root, "reports/detailxml.zip"),
        urljoin(version_root, "reports/detailxml.xml"),
    ]
    json_urls = [
        urljoin(version_root, "json/en/summary.json"),
        urljoin(version_root, "json/sum.json"),
        urljoin(version_root, "json/en/electionsettings.json"),
        urljoin(version_root, "json/en/election.json"),
    ]
    return xml_urls, json_urls


def compact(name):
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def validate_cd9_fixture(data):
    """Validate official extraction against the observed official CD9 card.

    This is a checksum only. A mismatch fails closed; these constants never
    populate or alter candidate totals in the production result file.
    """
    for race in data.get("races", []) or []:
        title = (race.get("name") or "").lower()
        if "representative" not in title or "district" not in title or "9" not in title:
            continue
        found = {compact(c.get("name")): int(c.get("votes") or 0) for c in race.get("candidates", [])}
        if all(found.get(name) == votes for name, votes in CD9_REP_CHECKSUM.items()):
            total = sum(found.get(name, 0) for name in CD9_REP_CHECKSUM)
            if total == CD9_REP_TOTAL:
                return True
    return False


def bounded_recover(source_url):
    errors = []
    version_root = None
    version_endpoint = None
    version = None

    try:
        version_root, version_endpoint, version = current_version_root(source_url)
    except Exception as e:
        errors.append(f"current version discovery: {e}")

    if version_root:
        xml_urls, json_urls = versioned_endpoints(version_root)

        # Version-pinned detail XML first: this is Clarity's canonical structured
        # report and avoids the anti-bot-protected JavaScript frontend entirely.
        for endpoint in xml_urls:
            try:
                r = va.fetch(endpoint, 12)
                races = clarity.races_from_detail_xml(r.content)
                if va.valid_races(races):
                    data = va.make_data(COUNTY, "Clarity/Scytl official version-pinned detail XML results", source_url, races)
                    data["dataEndpoints"] = [endpoint]
                    data["clarityVersion"] = version
                    data["clarityVersionEndpoint"] = version_endpoint
                    data["cd9FixtureValidated"] = validate_cd9_fixture(data)
                    return data
                errors.append(f"{endpoint}: no valid races")
            except Exception as e:
                errors.append(f"{endpoint}: {e}")

        # The current Clarity generation also exposes version-pinned summary JSON.
        for endpoint in json_urls:
            try:
                r = va.fetch(endpoint, 8)
                payload = r.json()
                races = va.normalize_races(va.race_objects_from_json(payload))
                if va.valid_races(races):
                    data = va.make_data(COUNTY, "Clarity/Scytl official version-pinned JSON results", source_url, races)
                    data["dataEndpoints"] = [endpoint]
                    data["clarityVersion"] = version
                    data["clarityVersionEndpoint"] = version_endpoint
                    data["cd9FixtureValidated"] = validate_cd9_fixture(data)
                    return data
                errors.append(f"{endpoint}: no valid races")
            except Exception as e:
                errors.append(f"{endpoint}: {e}")

    # Legacy unversioned probes remain diagnostic fallbacks only. They are useful
    # if a vendor changes current_ver behavior, but successful production data is
    # expected to come from the version-pinned routes above.
    for endpoint in clarity.xml_endpoints(source_url)[:1]:
        try:
            r = va.fetch(endpoint, 6)
            races = clarity.races_from_detail_xml(r.content)
            if va.valid_races(races):
                data = va.make_data(COUNTY, "Clarity/Scytl official legacy detail XML results", source_url, races)
                data["dataEndpoints"] = [endpoint]
                data["cd9FixtureValidated"] = validate_cd9_fixture(data)
                return data
        except Exception as e:
            errors.append(f"legacy {endpoint}: {e}")

    raise RuntimeError("No usable version-pinned Clarity contests; " + " | ".join(errors[-8:]))


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
            "adapter": "clarity-version-pinned-required",
            "dataEndpoints": data.get("dataEndpoints", []),
            "clarityVersion": data.get("clarityVersion"),
            "cd9FixtureValidated": data.get("cd9FixtureValidated", False),
        }
        manifest["osceolaIntegrityRecovery"] = {
            "connected": True,
            "sourceUrl": source_url,
            "discovery": discovery,
            "races": len(data.get("races", [])),
            "dataEndpoints": data.get("dataEndpoints", []),
            "clarityVersion": data.get("clarityVersion"),
            "clarityVersionEndpoint": data.get("clarityVersionEndpoint"),
            "cd9FixtureValidated": data.get("cd9FixtureValidated", False),
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
        print(f"OSCEOLA RECOVERED: {len(data.get('races', []))} races from {source_url}; version={data.get('clarityVersion')}; fixture={data.get('cd9FixtureValidated')}")
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
