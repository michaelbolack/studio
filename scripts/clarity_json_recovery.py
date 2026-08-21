import io
import json
import os
import re
import tempfile
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
    m = re.search(r"^(.*?/\d{3,9}/)(?:web\.[^/]+/?)$", clean, re.I)
    if m:
        return m.group(1)
    m = re.search(r"^(.*?/\d{3,9}/)", clean, re.I)
    return m.group(1) if m else clean.rsplit("/", 1)[0] + "/"


def current_version_root(url):
    """Discover Clarity's numeric publication version via current_ver.txt."""
    clean = (url or "").split("#", 1)[0]
    root = election_root(url)
    candidates = [
        urljoin(root, "current_ver.txt"),
        urljoin(clean if clean.endswith("/") else clean + "/", "current_ver.txt"),
        urljoin(root, "web/current_ver.txt"),
    ]
    seen = set()
    diagnostics = []
    for endpoint in candidates:
        if endpoint in seen:
            continue
        seen.add(endpoint)
        try:
            r = va.fetch(endpoint, 10)
            raw = (r.text or "").strip()
            diagnostics.append({"url": endpoint, "status": getattr(r, "status_code", None), "value": raw[:120]})
            m = re.search(r"(?<!\d)(\d{3,12})(?!\d)", raw)
            if m:
                version = m.group(1)
                return urljoin(root, version + "/"), endpoint, version, diagnostics
        except Exception as e:
            diagnostics.append({"url": endpoint, "error": str(e)})
    raise RuntimeError("no numeric Clarity publication version found; probes=" + json.dumps(diagnostics, separators=(",", ":")))


def json_endpoints(url, version_root=None):
    root = version_root or election_root(url)
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


def xml_endpoints(url, version_root=None):
    root = version_root or election_root(url)
    return [
        urljoin(root, "reports/detailxml.zip"),
        urljoin(root, "reports/detailxml.xml"),
        urljoin(root, "detailxml.zip"),
    ]


def races_from_detail_xml(content):
    if content[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = archive.infolist()
            xml_infos = [i for i in infos if i.filename.lower().endswith(".xml") and i.file_size > 0]
            if not xml_infos:
                members = ", ".join(f"{i.filename}:{i.file_size}" for i in infos[:20])
                raise RuntimeError("Clarity detail XML ZIP contained no non-empty XML; members=" + members)
            info = max(xml_infos, key=lambda i: i.file_size)
            xml_bytes = archive.read(info.filename)
            if not xml_bytes.strip():
                raise RuntimeError(f"Selected Clarity XML member was empty after read: {info.filename}:{info.file_size}")
    else:
        xml_bytes = content

    if not xml_bytes or not xml_bytes.strip():
        raise RuntimeError("Clarity detail XML response was empty")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
            tmp.write(xml_bytes)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = tmp.name
        parser = clarify.Parser()
        parser.parse(tmp_path)
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

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
    version_root = None
    version_endpoint = None
    version = None
    version_diagnostics = []

    try:
        version_root, version_endpoint, version, version_diagnostics = current_version_root(url)
        print(f"CLARITY VERSION {county}: {version} via {version_endpoint}")
    except Exception as e:
        errors.append(f"current version discovery: {e}")

    roots = []
    if version_root:
        roots.append((version_root, True))
    roots.append((None, False))

    for root, pinned in roots:
        races = []
        used = []
        for endpoint in json_endpoints(url, root):
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
            data = va.make_data(county, "Clarity/Scytl official version-pinned JSON results" if pinned else "Clarity/Scytl official JSON results", url, races)
            data["dataEndpoints"] = used
            data["clarityVersion"] = version if pinned else None
            data["clarityVersionEndpoint"] = version_endpoint if pinned else None
            data["clarityVersionDiagnostics"] = version_diagnostics
            return data

        for endpoint in xml_endpoints(url, root):
            try:
                r = va.fetch(endpoint, 20)
                found = races_from_detail_xml(r.content)
                if va.valid_races(found):
                    data = va.make_data(county, "Clarity/Scytl official version-pinned detail XML results" if pinned else "Clarity/Scytl official detail XML results", url, found)
                    data["dataEndpoints"] = [endpoint]
                    data["clarityVersion"] = version if pinned else None
                    data["clarityVersionEndpoint"] = version_endpoint if pinned else None
                    data["clarityVersionDiagnostics"] = version_diagnostics
                    return data
            except Exception as e:
                errors.append(f"{endpoint}: {e}")

    raise RuntimeError("No usable Clarity JSON/XML contests; " + " | ".join(errors[-12:]))


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
                "adapter": "clarity-version-pinned-v2" if data.get("clarityVersion") else "clarity-direct",
                "dataEndpoints": data.get("dataEndpoints", []),
                "clarityVersion": data.get("clarityVersion"),
                "clarityVersionEndpoint": data.get("clarityVersionEndpoint"),
            }
            recovered += 1
            print(f"CLARITY DIRECT OK {county}: {len(data.get('races', []))} races; version={data.get('clarityVersion')}")
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
