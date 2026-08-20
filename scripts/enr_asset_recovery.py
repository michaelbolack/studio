import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import fix_enr_summary as summary
import update_counties as core
import vendor_asset_probe as probe
import vendor_adapters as va

OUT_DIR = "data"
MAX_ENDPOINTS_PER_COUNTY = 18
ENDPOINT_TIMEOUT = 8


def endpoint_priority(source_url, endpoint):
    """Prefer official same-host machine-readable election feeds first."""
    src = urlparse(source_url)
    dst = urlparse(endpoint)
    low = endpoint.lower()
    score = 0
    if dst.netloc and dst.netloc.lower() == src.netloc.lower():
        score -= 100
    if any(x in low for x in ("detailxml.zip", "summary.json", "results.json", "election.json")):
        score -= 50
    elif low.endswith((".json", ".xml", ".zip", ".csv")):
        score -= 30
    if "/api/" in low:
        score -= 20
    if any(x in low for x in ("report", "result", "contest", "summary", "election")):
        score -= 10
    # Push obvious page/assets behind actual data candidates.
    if low.endswith((".js", ".html", ".htm")):
        score += 30
    return score


def recover_enr(county, entry):
    url = entry.get("sourceUrl") or ""
    if "enr.electionsfl.org" not in url.lower():
        return None

    page, endpoints = probe.discover_endpoints(url)
    endpoints = sorted(
        dict.fromkeys(endpoints),
        key=lambda endpoint: endpoint_priority(url, endpoint),
    )[:MAX_ENDPOINTS_PER_COUNTY]

    errors = []
    for endpoint in endpoints:
        try:
            resp = va.fetch(endpoint, ENDPOINT_TIMEOUT)
            races = probe.parse_payload_response(resp)
            if va.valid_races(races):
                data = va.make_data(
                    county,
                    "Florida Election Night Reporting — discovered official data endpoint",
                    url,
                    races,
                    core.extract_stats(page.text),
                )
                data["dataEndpoint"] = endpoint
                return data
        except Exception as e:
            errors.append(f"{endpoint}: {e}")

    # Final direct-page retry after endpoint discovery, in case the summary HTML
    # itself became fully populated between the earlier pass and this recovery.
    races = summary.parse_summary_any(page.text)
    races = va.normalize_races(races)
    if va.valid_races(races):
        return va.make_data(
            county,
            "Florida Election Night Reporting — direct summary retry",
            url,
            races,
            core.extract_stats(page.text),
        )

    raise RuntimeError(
        f"No usable ENR data endpoint found after {len(endpoints)} bounded probes; "
        + " | ".join(errors[-5:])
    )


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
        if "enr.electionsfl.org" not in url.lower():
            continue
        try:
            data = recover_enr(county, entry)
            if not data:
                continue
            path = va.write_county(county, data)
            manifest["counties"][county] = {
                "connected": True,
                "file": path,
                "sourceUrl": url,
                "dataEndpoint": data.get("dataEndpoint"),
                "races": len(data.get("races", [])),
                "adapter": "florida-enr-endpoint-discovery",
            }
            recovered += 1
            print(f"ENR ASSET OK {county}: {len(data.get('races', []))} races")
        except Exception as e:
            failures.append({"county": county, "error": str(e)})
            print(f"ENR ASSET FAIL {county}: {e}")

    summary.rebuild_aggregates(manifest)
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    manifest["enrAssetRecovery"] = {
        "recovered": recovered,
        "maxEndpointsPerCounty": MAX_ENDPOINTS_PER_COUNTY,
        "endpointTimeoutSeconds": ENDPOINT_TIMEOUT,
        "failures": failures,
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    connected = sum(1 for e in manifest.get("counties", {}).values() if e.get("connected"))
    print(f"ENR endpoint recovery: +{recovered}; connected {connected}/{len(manifest.get('counties', {}))}")


if __name__ == "__main__":
    main()
