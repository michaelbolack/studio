import io
import json
import os
import re
import zipfile
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

import update_counties as core
import fix_enr_summary as enr_summary
import vendor_adapters as va

OUT_DIR = "data"


def same_origin(base, target):
    a, b = urlparse(base), urlparse(target)
    return not b.netloc or a.netloc.lower() == b.netloc.lower()


def likely_endpoint(s):
    low = s.lower()
    if any(x in low for x in (".map", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".css", ".woff", ".ttf")):
        return False
    return (
        any(x in low for x in (".json", ".xml", ".zip", ".csv"))
        or any(x in low for x in ("/api/", "results", "contest", "election", "summary", "detailxml", "report"))
    )


def endpoint_strings(text):
    found = []
    patterns = [
        r"https?://[^\"'`<>\s]+",
        r"/[A-Za-z0-9_./?=&%:-]+(?:\.json|\.xml|\.zip|\.csv)(?:\?[^\"'`<>\s]*)?",
        r"/[A-Za-z0-9_./?=&%:-]*(?:api|results|contests|elections|summary|reports)[A-Za-z0-9_./?=&%:-]*",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, text, re.I):
            match = match.replace("\\/", "/").rstrip("),;]")
            if likely_endpoint(match):
                found.append(match)
    return found


def page_assets(url):
    r = va.fetch(url, 45)
    soup = BeautifulSoup(r.text, "html.parser")
    scripts = []
    for tag in soup.find_all("script", src=True):
        src = urljoin(url, tag["src"])
        if same_origin(url, src):
            scripts.append(src)
    # Keep request volume bounded. Modern apps normally expose config in the
    # final bundles; include first and last assets to cover vendor bootstraps.
    if len(scripts) > 14:
        scripts = scripts[:5] + scripts[-9:]
    return r, list(dict.fromkeys(scripts))


def parse_payload_response(resp):
    ctype = (resp.headers.get("content-type") or "").lower()
    body = resp.content
    text = None
    try:
        text = resp.text
    except Exception:
        pass

    races = []
    if "json" in ctype or (text and text.lstrip().startswith(("{", "["))):
        try:
            payload = resp.json()
        except Exception:
            try:
                payload = json.loads(text)
            except Exception:
                payload = None
        if payload is not None:
            races = va.normalize_races(va.race_objects_from_json(payload))
            if va.valid_races(races):
                return races

    if zipfile.is_zipfile(io.BytesIO(body)):
        try:
            with zipfile.ZipFile(io.BytesIO(body)) as z:
                members = [n for n in z.namelist() if n.lower().endswith((".xml", ".json"))]
                members.sort(key=lambda n: z.getinfo(n).file_size, reverse=True)
                for name in members:
                    raw = z.read(name)
                    if name.lower().endswith(".xml"):
                        try:
                            races = va.parse_clarity_xml(raw)
                        except Exception:
                            continue
                    else:
                        try:
                            races = va.normalize_races(va.race_objects_from_json(json.loads(raw.decode("utf-8-sig"))))
                        except Exception:
                            continue
                    if va.valid_races(races):
                        return races
        except Exception:
            pass

    if "xml" in ctype or (text and text.lstrip().startswith("<")):
        try:
            races = va.parse_clarity_xml(body)
            if va.valid_races(races):
                return races
        except Exception:
            pass

    if text:
        try:
            races = va.normalize_races(enr_summary.parse_summary_any(text))
            if va.valid_races(races):
                return races
        except Exception:
            pass
    return []


def discover_endpoints(url):
    page, scripts = page_assets(url)
    candidates = []
    candidates.extend(endpoint_strings(page.text))

    for src in scripts:
        try:
            js = va.fetch(src, 30).text
        except Exception:
            continue
        for raw in endpoint_strings(js):
            full = urljoin(src, raw)
            # Official election apps occasionally call a same-vendor API on a
            # sibling host. Keep HTTPS URLs but reject obvious third-party SDKs.
            host = urlparse(full).netloc.lower()
            if any(x in host for x in ("google", "facebook", "doubleclick", "cloudflareinsights", "sentry", "segment")):
                continue
            candidates.append(full)

    # Add conventional vendor endpoints around the public page/root.
    clean = url.split("#", 1)[0]
    root = clean.rsplit("/", 1)[0] + "/"
    for rel in (
        "results.json", "summary.json", "data.json", "election.json",
        "api/results", "api/summary", "api/election", "api/contests",
        "Reports/DetailXML.zip", "reports/detailxml.zip",
    ):
        candidates.append(urljoin(root, rel))

    out = []
    seen = set()
    for c in candidates:
        c = urljoin(url, c)
        if not c.startswith(("http://", "https://")) or c in seen:
            continue
        seen.add(c)
        out.append(c)
    return page, out[:100]


def recover(county, entry):
    url = entry.get("sourceUrl") or ""
    page, endpoints = discover_endpoints(url)
    errors = []
    for endpoint in endpoints:
        try:
            resp = va.fetch(endpoint, 35)
            races = parse_payload_response(resp)
            if va.valid_races(races):
                data = va.make_data(
                    county,
                    "Official election vendor data endpoint",
                    url,
                    races,
                    core.extract_stats(page.text),
                )
                data["dataEndpoint"] = endpoint
                return data, endpoint
        except Exception as e:
            errors.append(f"{endpoint}: {e}")
    raise RuntimeError(f"No usable vendor endpoint found after {len(endpoints)} probes; " + " | ".join(errors[-5:]))


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
        # Florida ENR static pages are handled more efficiently by the earlier
        # summary adapter. This probe targets app-driven vendors and may still
        # be used for quarantined ENR feeds only when explicitly non-static.
        if "enr.electionsfl.org" in url.lower():
            continue
        try:
            data, endpoint = recover(county, entry)
            path = va.write_county(county, data)
            manifest["counties"][county] = {
                "connected": True,
                "file": path,
                "sourceUrl": url,
                "dataEndpoint": endpoint,
                "races": len(data.get("races", [])),
                "adapter": "vendor-endpoint-discovery",
            }
            recovered += 1
            print(f"ASSET OK {county}: {len(data.get('races', []))} races via {endpoint}")
        except Exception as e:
            failures.append({"county": county, "error": str(e)})
            print(f"ASSET FAIL {county}: {e}")

    enr_summary.rebuild_aggregates(manifest)
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    manifest["assetRecovery"] = {
        "recovered": recovered,
        "failures": failures,
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    connected = sum(1 for e in manifest.get("counties", {}).values() if e.get("connected"))
    print(f"Asset endpoint recovery: +{recovered}; connected {connected}/{len(manifest.get('counties', {}))}")


if __name__ == "__main__":
    main()
