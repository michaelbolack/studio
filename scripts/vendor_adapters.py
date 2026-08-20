import io
import json
import os
import re
import zipfile
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

import update_counties as core
import fix_enr_summary as enr_summary

OUT_DIR = "data"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; IRC-Media-Election-Center/1.0; +https://ircmedia.net)"
}


def fetch(url, timeout=35):
    r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    r.raise_for_status()
    return r


def valid_races(races):
    if not races:
        return False
    candidate_count = 0
    positive_votes = 0
    for race in races:
        for c in race.get("candidates", []) or []:
            if c.get("name"):
                candidate_count += 1
            if int(c.get("votes") or 0) > 0:
                positive_votes += 1
    return candidate_count >= 2 and positive_votes >= 1


def party_from_text(text):
    s = (text or "").lower()
    if re.search(r"\b(rep|republican)\b", s):
        return "REP"
    if re.search(r"\b(dem|democratic)\b", s):
        return "DEM"
    return "NON"


def clean_choice(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"\s*\((REP|DEM|NPA|NON)\)\s*$", "", text, flags=re.I).strip()
    return text


def make_data(county, source, source_url, races, stats=None):
    stats = stats or {}
    return {
        "county": county,
        "election": "2026 Primary Election",
        "electionDate": core.ELECTION_DATE,
        "source": source,
        "sourceUrl": source_url,
        "registeredVoters": int(stats.get("registeredVoters") or 0),
        "ballotsCast": int(stats.get("ballotsCast") or 0),
        "precinctsReporting": int(stats.get("precinctsReporting") or 0),
        "precinctsTotal": int(stats.get("precinctsTotal") or 0),
        "lastUpdated": stats.get("lastUpdated") or datetime.now(timezone.utc).isoformat(),
        "races": races,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


def normalize_races(races):
    out = []
    for race in races:
        cands = []
        seen = set()
        for c in race.get("candidates", []) or []:
            name = clean_choice(c.get("name", ""))
            if not name or core.is_stats_choice(name):
                continue
            key = core.candidate_key(name)
            if not key or key in seen:
                continue
            seen.add(key)
            cands.append({
                "name": name,
                "party": (c.get("party") or party_from_text(race.get("name", "")) or "NON").upper(),
                "votes": core.clean_num(c.get("votes")),
                "percent": core.pct(c.get("percent")),
            })
        total = sum(c["votes"] for c in cands)
        if total:
            for c in cands:
                c["percent"] = round(c["votes"] / total * 100, 2)
        if cands:
            out.append({"name": race.get("name") or "Contest", "candidates": cands})
    return out


def clarity_candidates(summary_url):
    clean = summary_url.split("#", 1)[0]
    p = urlparse(clean)
    parts = [x for x in p.path.split("/") if x]
    candidates = []

    # Current Clarity URLs generally look like /FL/County/ELECTION/web.BUILD/.
    # Older installs add a results-set id before /reports/detailxml.zip. Probe
    # both direct election roots and any result-set ids exposed in page source.
    election_root = clean
    m = re.search(r"/(web\.[^/]+)/?$", clean, re.I)
    if m:
        election_root = clean[:m.start()] + "/"

    for base in {election_root, clean}:
        candidates.extend([
            urljoin(base, "reports/detailxml.zip"),
            urljoin(base, "Reports/DetailXML.zip"),
            urljoin(base, "reports/DetailXML.zip"),
            urljoin(base, "Reports/detailxml.zip"),
        ])

    try:
        page = fetch(clean).text
        for match in re.findall(r"(?:https?:)?//[^\"'<>\s]+detailxml\.zip|[^\"'<>\s]+detailxml\.zip", page, re.I):
            if match.startswith("//"):
                match = p.scheme + ":" + match
            candidates.append(urljoin(clean, match))
        # Look for numeric result-set ids referenced by config/assets.
        for rid in set(re.findall(r"/(\d{3,9})/(?:reports|web\.)", page, re.I)):
            root = f"{p.scheme}://{p.netloc}/" + "/".join(parts[:3]) + f"/{rid}/"
            candidates.extend([
                urljoin(root, "reports/detailxml.zip"),
                urljoin(root, "Reports/DetailXML.zip"),
            ])
    except Exception:
        pass

    seen = set()
    return [x for x in candidates if not (x in seen or seen.add(x))]


def parse_clarity_xml(xml_bytes):
    root = ET.fromstring(xml_bytes)

    def local(tag):
        return tag.rsplit("}", 1)[-1].lower()

    races = []
    for contest in root.iter():
        if local(contest.tag) not in {"contest", "race"}:
            continue
        race_name = contest.attrib.get("text") or contest.attrib.get("name") or contest.attrib.get("title")
        if not race_name:
            for ch in list(contest):
                if local(ch.tag) in {"name", "text", "contestname"} and (ch.text or "").strip():
                    race_name = (ch.text or "").strip()
                    break
        candidates = []
        for node in contest.iter():
            if local(node.tag) not in {"choice", "candidate", "selection"}:
                continue
            name = node.attrib.get("text") or node.attrib.get("name") or node.attrib.get("candidate")
            if not name:
                for ch in list(node):
                    if local(ch.tag) in {"name", "text", "choicename", "candidatename"} and (ch.text or "").strip():
                        name = (ch.text or "").strip()
                        break
            if not name or core.is_stats_choice(name):
                continue
            votes = 0
            for key, value in node.attrib.items():
                if "vote" in key.lower() and "percent" not in key.lower():
                    votes = max(votes, core.clean_num(value))
            for ch in node.iter():
                tag = local(ch.tag)
                if tag in {"totalvotes", "votes", "votecount", "total"}:
                    votes = max(votes, core.clean_num(ch.text))
            candidates.append({
                "name": name,
                "party": party_from_text(race_name or ""),
                "votes": votes,
                "percent": 0,
            })
        if race_name and candidates:
            races.append({"name": race_name, "candidates": candidates})
    return normalize_races(races)


def recover_clarity(county, url):
    errors = []
    for detail_url in clarity_candidates(url):
        try:
            r = fetch(detail_url, 45)
            if not zipfile.is_zipfile(io.BytesIO(r.content)):
                raise RuntimeError("not a ZIP")
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                xmls = [n for n in z.namelist() if n.lower().endswith(".xml")]
                if not xmls:
                    raise RuntimeError("ZIP contains no XML")
                # Try largest XML first; fall back through all members.
                xmls.sort(key=lambda n: z.getinfo(n).file_size, reverse=True)
                for name in xmls:
                    try:
                        races = parse_clarity_xml(z.read(name))
                        if valid_races(races):
                            data = make_data(county, "Clarity/Scytl official election results", url, races)
                            data["xmlUrl"] = detail_url
                            return data
                    except Exception:
                        continue
            raise RuntimeError("no usable contests in DetailXML")
        except Exception as e:
            errors.append(f"{detail_url}: {e}")
    raise RuntimeError("Clarity recovery failed: " + " | ".join(errors[-6:]))


def race_objects_from_json(obj, path=""):
    races = []
    if isinstance(obj, dict):
        lower = {str(k).lower(): k for k in obj}
        name_key = next((lower[k] for k in ("contestname", "racename", "contest", "race", "office", "title", "name") if k in lower), None)
        candidate_key = next((lower[k] for k in ("candidates", "choices", "selections", "options") if k in lower), None)
        if name_key is not None and candidate_key is not None and isinstance(obj.get(candidate_key), list):
            cands = []
            for c in obj[candidate_key]:
                if not isinstance(c, dict):
                    continue
                cl = {str(k).lower(): k for k in c}
                nk = next((cl[k] for k in ("candidatename", "choicename", "name", "text", "label") if k in cl), None)
                vk = next((cl[k] for k in ("totalvotes", "votes", "votecount", "total", "count") if k in cl), None)
                pk = next((cl[k] for k in ("party", "partyname", "politicalparty") if k in cl), None)
                if nk is not None and vk is not None:
                    cands.append({"name": c[nk], "party": c.get(pk) if pk else "NON", "votes": c[vk], "percent": 0})
            if cands:
                races.append({"name": obj[name_key], "candidates": cands})
        for k, v in obj.items():
            races.extend(race_objects_from_json(v, path + "/" + str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            races.extend(race_objects_from_json(v, path + f"/{i}"))
    return races


def embedded_json_candidates(html):
    soup = BeautifulSoup(html, "html.parser")
    payloads = []
    for script in soup.find_all("script"):
        text = script.string or script.get_text("", strip=False)
        if not text or len(text) < 20:
            continue
        stype = (script.get("type") or "").lower()
        sid = (script.get("id") or "").lower()
        if "json" in stype or sid in {"__next_data__", "__nuxt_data__"}:
            try:
                payloads.append(json.loads(text))
            except Exception:
                pass
        # Also accept obvious JSON object assignments used by vendor apps.
        for m in re.finditer(r"(?:window\.[A-Za-z0-9_$]+|[A-Za-z0-9_$]+)\s*=\s*(\{.*?\})\s*;", text, re.S):
            try:
                payloads.append(json.loads(m.group(1)))
            except Exception:
                continue
    return payloads


def recover_embedded_json(county, url, source):
    r = fetch(url, 45)
    races = []
    for payload in embedded_json_candidates(r.text):
        races.extend(race_objects_from_json(payload))
    races = normalize_races(races)
    if valid_races(races):
        return make_data(county, source, url, races, core.extract_stats(r.text))
    raise RuntimeError("No usable election-result JSON embedded in vendor page")


def recover_html(county, url, source):
    r = fetch(url, 45)
    races = enr_summary.parse_summary_any(r.text)
    races = normalize_races(races)
    if valid_races(races):
        return make_data(county, source, url, races, core.extract_stats(r.text))
    # Some vendors render a complete HTML table without Florida ENR's labels.
    soup = BeautifulSoup(r.text, "html.parser")
    generic = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        headers = [re.sub(r"\s+", " ", x.get_text(" ", strip=True)).lower() for x in rows[0].find_all(["th", "td"])]
        if not headers:
            continue
        name_i = next((i for i, h in enumerate(headers) if any(x in h for x in ("candidate", "choice", "name"))), None)
        vote_i = next((i for i, h in enumerate(headers) if "vote" in h and "percent" not in h), None)
        if name_i is None or vote_i is None:
            continue
        heading = None
        for prev in table.find_all_previous(["h1", "h2", "h3", "h4", "legend"], limit=10):
            txt = prev.get_text(" ", strip=True)
            if txt:
                heading = txt
                break
        cands = []
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) <= max(name_i, vote_i):
                continue
            name = cells[name_i].get_text(" ", strip=True)
            if not name or core.is_stats_choice(name):
                continue
            cands.append({"name": name, "party": party_from_text(heading or ""), "votes": core.clean_num(cells[vote_i].get_text(" ", strip=True)), "percent": 0})
        if cands:
            generic.append({"name": heading or "Contest", "candidates": cands})
    generic = normalize_races(generic)
    if valid_races(generic):
        return make_data(county, source, url, generic, core.extract_stats(r.text))
    raise RuntimeError("No usable candidate tables found in vendor HTML")


def recover_one(county, entry):
    url = entry.get("sourceUrl") or ""
    low = url.lower()

    if "clarityelections.com" in low or "votepinellas.gov" in low:
        return recover_clarity(county, url), "clarity-direct"

    if "enhancedvoting.com" in low:
        # Enhanced Voting pages are app-driven; first consume embedded state,
        # then try rendered/static table content if the public page exposes it.
        try:
            return recover_embedded_json(county, url, "Enhanced Voting official results"), "enhanced-json"
        except Exception:
            return recover_html(county, url, "Enhanced Voting official results"), "enhanced-html"

    if "browardvotes.gov" in low or "livevoterturnout.com" in low:
        try:
            return recover_embedded_json(county, url, "Official county election-night reporting"), "vendor-json"
        except Exception:
            return recover_html(county, url, "Official county election-night reporting"), "vendor-html"

    if "enr.electionsfl.org" in low:
        # Last-resort direct summary parser for Florida ENR counties whose
        # reports directory/CSV is unavailable.
        return recover_html(county, url, "Florida Election Night Reporting — direct summary"), "florida-enr-direct"

    return recover_embedded_json(county, url, "Official county election results"), "generic-json"


def write_county(county, data):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, core.slugify(county) + ".json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def main():
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    recovered = 0
    attempted = 0
    failures = []
    for county, entry in list(manifest.get("counties", {}).items()):
        if entry.get("connected"):
            continue
        attempted += 1
        try:
            data, adapter = recover_one(county, entry)
            races = normalize_races(data.get("races", []))
            data["races"] = races
            if not valid_races(races):
                raise RuntimeError("recovery returned no validated candidate vote totals")
            path = write_county(county, data)
            manifest["counties"][county] = {
                "connected": True,
                "file": path,
                "sourceUrl": entry.get("sourceUrl"),
                "races": len(races),
                "adapter": adapter,
            }
            recovered += 1
            print(f"VENDOR OK {county}: {len(races)} races via {adapter}")
        except Exception as e:
            failures.append((county, str(e)))
            print(f"VENDOR FAIL {county}: {e}")

    # Rebuild county-derived aggregates; the later official_state_results.py
    # workflow step will replace statewide/multicounty totals with Florida DOS
    # compiled figures whenever DOS is available.
    enr_summary.rebuild_aggregates(manifest)
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    manifest["vendorRecovery"] = {
        "attempted": attempted,
        "recovered": recovered,
        "failed": len(failures),
        "failures": [{"county": c, "error": e} for c, e in failures],
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    connected = sum(1 for e in manifest.get("counties", {}).values() if e.get("connected"))
    print(f"Vendor recovery: +{recovered}; connected {connected}/{len(manifest.get('counties', {}))}")


if __name__ == "__main__":
    main()
