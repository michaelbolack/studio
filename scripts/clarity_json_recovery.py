import io
import json
import os
import re
import zipfile
from datetime import datetime, timezone
from urllib.parse import urljoin

import clarify

import vendor_adapters as va
import fix_enr_summary as enr_summary
import update_counties as core

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


def xml_endpoints(url):
    root = election_root(url)
    return [
        urljoin(root, "reports/detailxml.zip"),
        urljoin(root, "reports/detailxml.xml"),
        urljoin(root, "detailxml.zip"),
    ]


def races_from_detail_xml(content):
    if content[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            xml_names = [n for n in archive.namelist() if n.lower().endswith(".xml")]
            if not xml_names:
                raise RuntimeError("Clarity detail XML ZIP contained no XML")
            xml_name = max(xml_names, key=lambda n: archive.getinfo(n).file_size)
            xml_bytes = archive.read(xml_name)
    else:
        xml_bytes = content

    parser = clarify.Parser()
    parser.parse(io.BytesIO(xml_bytes))
    races = []
    for contest in getattr(parser, "contests", []) or []:
        candidates = []
        contest_text = getattr(contest, "text", "Contest")
        for choice in getattr(contest, "choices", []) or []:
            raw = getattr(choice, "text", "")
            name = core.clarity_clean_choice(raw)
            if not name or core.is_stats_choice(name):
                continue
            candidates.append({
                "name": name,
                "party": core.clarity_choice_party(raw, contest_text),
                "votes": core.clean_num(getattr(choice, "total_votes", 0)),
                "percent": 0.0,
            })
        if not candidates:
            continue
        total = sum(c["votes"] for c in candidates)
        for c in candidates:
            c["percent"] = round((c["votes"] / total * 100) if total else 0, 2)
        races.append({"name": contest_text, "candidates": candidates})
    return va.normalize_races(races)


def recover(county, url):
    errors = []
    races = []
    used = []

    for endpoint in json_endpoints(url):
        try:
            r = va.fetch(endpoint, 12)
            payload = r.json()
            found = va.normalize_races(va.race_objects_from_json(payload))
            if found:
                races.extend(found)
                used.append(endpoint)
        except Exception as e:
            errors.append(f"{endpoint}: {e}")

    races = va.normalize_races(races)
    if va.valid_races(races):
        data = va.make_data(county, "Clarity/Scytl official JSON results", url, races)
        data["dataEndpoints"] = used
        return data

    # Direct official detail XML fallback. This bypasses the legacy clarify
    # Jurisdiction.report_url() resolver that can return None on modern URLs.
    for endpoint in xml_endpoints(url):
        try:
            r = va.fetch(endpoint, 20)
            found = races_from_detail_xml(r.content)
            if va.valid_races(found):
                data = va.make_data(county, "Clarity/Scytl official detail XML results", url, found)
                data["dataEndpoints"] = [endpoint]
                return data
        except Exception as e:
            errors.append(f"{endpoint}: {e}")

    raise RuntimeError("No usable Clarity JSON/XML contests; " + " | ".join(errors[-8:]))


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
                "adapter": "clarity-direct",
                "dataEndpoints": data.get("dataEndpoints", []),
            }
            recovered += 1
            print(f"CLARITY DIRECT OK {county}: {len(data.get('races', []))} races")
        except Exception as e:
            failures.append({"county": county, "error": str(e)})
            print(f"CLARITY DIRECT FAIL {county}: {e}")

    enr_summary.rebuild_aggregates(manifest)
    manifest["clarityJsonRecovery"] = {
        "recovered": recovered,
        "failures": failures,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Clarity direct recovery: +{recovered}")


if __name__ == "__main__":
    main()
