import json, os, re
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

OUT_DIR = "data"
ELECTION_DATE = "8/18/2026"
BASE = "https://results.elections.myflorida.com/SummaryRpt.asp"
HEADERS = {"User-Agent": "IRC-Media-Election-Center/1.0"}
STATEWIDE = [
    "United States Senator",
    "Governor and Lieutenant Governor",
    "Chief Financial Officer",
    "Commissioner of Agriculture",
]
ALIASES = {
    "United States Senator": ["United States Senator"],
    "Governor and Lieutenant Governor": ["Governor and Lieutenant Governor", "Governor & Lieutenant Governor", "Governor and Lt. Governor", "Governor & Lt. Governor"],
    "Chief Financial Officer": ["Chief Financial Officer"],
    "Commissioner of Agriculture": ["Commissioner of Agriculture"],
}


def num(s):
    try:
        return int(re.sub(r"[^0-9]", "", str(s)))
    except Exception:
        return 0


def clean_lines(html):
    soup = BeautifulSoup(html, "html.parser")
    return [re.sub(r"\s+", " ", x).strip() for x in soup.stripped_strings if re.sub(r"\s+", " ", x).strip()]


def is_number(s):
    return bool(re.fullmatch(r"[0-9][0-9,]*", s or ""))


def is_percent(s):
    return bool(re.fullmatch(r"[0-9]+(?:\.[0-9]+)?%", s or ""))


def extract_candidate_block(lines, start, party, stop_at_district=False):
    total_i = None
    for i in range(start, min(len(lines), start + 250)):
        low = lines[i].lower()
        if stop_at_district and i > start and low.startswith("district:"):
            return None
        if low in {"total", "sub total", "subtotal"}:
            total_i = i
            break
    if total_i is None:
        return None

    pct_i = None
    for i in range(total_i + 1, min(len(lines), total_i + 80)):
        if lines[i].lower().replace(" ", "") in {"%votes", "%vote"}:
            pct_i = i
            break
    if pct_i is None:
        return None

    votes = [num(x) for x in lines[total_i + 1:pct_i] if is_number(x)]
    if not votes:
        return None

    raw_names = []
    junk = {
        "official results", "unofficial results", "unofficial preliminary results",
        "republican primary", "democratic primary", "total", "sub total", "subtotal",
        "county", "statewide", "district", "district:", "race"
    }
    for x in lines[start:total_i]:
        low = x.lower().strip()
        if not x or low in junk or is_number(x) or is_percent(x):
            continue
        if re.fullmatch(r"\([A-Z]{2,4}\)", x):
            continue
        if low.startswith("district:") or low.startswith("circuit:") or low.startswith("group:"):
            continue
        if any(low == a.lower() for aliases in ALIASES.values() for a in aliases):
            continue
        if low == "united states representative":
            continue
        raw_names.append(x)

    if len(raw_names) < len(votes):
        return None
    names = raw_names[-len(votes):]
    total_votes = sum(votes)
    candidates = []
    for name, v in zip(names, votes):
        candidates.append({
            "name": name,
            "party": party,
            "votes": v,
            "percent": round((v / total_votes * 100) if total_votes else 0, 2),
        })
    return candidates


def find_title(lines, aliases):
    lowered = [x.lower() for x in lines]
    for alias in aliases:
        a = alias.lower()
        for i, x in enumerate(lowered):
            if x == a:
                return i
    return None


def fetch_party(party):
    params = {"DATAMODE": "", "ElectionDate": ELECTION_DATE, "PARTY": party}
    r = requests.get(BASE, params=params, headers=HEADERS, timeout=40)
    r.raise_for_status()
    lines = clean_lines(r.text)
    if not any("2026" in x and "Primary" in x for x in lines):
        raise RuntimeError("Florida DOS 2026 primary results page not available")
    return lines, r.url


def statewide_from_party(lines, party):
    races = []
    for office in STATEWIDE:
        idx = find_title(lines, ALIASES[office])
        if idx is None:
            continue
        cands = extract_candidate_block(lines, idx + 1, party)
        if cands:
            races.append({"name": party + " " + office, "type": "statewide", "candidates": cands})
    return races


def district9_from_party(lines, party):
    idx = find_title(lines, ["United States Representative"])
    if idx is None:
        return None
    for i in range(idx + 1, min(len(lines), idx + 900)):
        if re.sub(r"\s+", "", lines[i].lower()) in {"district:9", "district:09", "district:009"}:
            cands = extract_candidate_block(lines, i + 1, party, stop_at_district=True)
            if cands:
                return {"name": party + " Representative in Congress", "type": "congress", "district": 9, "candidates": cands}
    return None


def main():
    party_data = {}
    urls = []
    for party in ("REP", "DEM"):
        try:
            lines, url = fetch_party(party)
            party_data[party] = lines
            urls.append(url)
            print(f"DOS OK {party}: {len(lines)} text cells")
        except Exception as e:
            print(f"DOS FAIL {party}: {e}")

    # This is deliberately non-fatal. If Florida DOS is temporarily unavailable,
    # preserve the last-known county-derived aggregates and let the live workflow publish.
    if not party_data:
        print("Florida DOS compiled results unavailable; keeping county aggregation")
        return

    state_races = []
    for party, lines in party_data.items():
        state_races.extend(statewide_from_party(lines, party))

    if state_races:
        statewide = {
            "scope": "Florida",
            "election": "2026 Primary Election",
            "electionDate": "2026-08-18",
            "source": "Florida Department of State, Division of Elections compiled results",
            "sourceUrl": BASE + "?" + urlencode({"ElectionDate": ELECTION_DATE}),
            "countiesIncluded": 67,
            "countiesDiscovered": 67,
            "coverageComplete": True,
            "precinctsReporting": 0,
            "precinctsTotal": 0,
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "races": state_races,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
        os.makedirs(OUT_DIR, exist_ok=True)
        with open(os.path.join(OUT_DIR, "statewide.json"), "w") as f:
            json.dump(statewide, f, indent=2)
        print(f"DOS statewide: {len(state_races)} race groups")

    d9_races = []
    for party, lines in party_data.items():
        race = district9_from_party(lines, party)
        if race:
            d9_races.append(race)
    if d9_races:
        district = {
            "scope": "Florida Congressional District 9",
            "district": 9,
            "election": "2026 Primary Election",
            "electionDate": "2026-08-18",
            "source": "Florida Department of State, Division of Elections compiled district results",
            "sourceUrl": "https://results.elections.myflorida.com/DetailRpt.Asp?DIST=009&ELECTIONDATE=8%2F18%2F2026&RACE=USR",
            "countiesIncluded": 7,
            "countiesExpected": 7,
            "countyNames": ["Glades", "Highlands", "Indian River", "Okeechobee", "Orange", "Osceola", "Polk"],
            "coverageComplete": True,
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "races": d9_races,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
        with open(os.path.join(OUT_DIR, "district-9.json"), "w") as f:
            json.dump(district, f, indent=2)
        print(f"DOS District 9: {len(d9_races)} race groups")

    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
        if state_races:
            manifest["statewide"] = {"file": "data/statewide.json", "countiesIncluded": 67, "countiesDiscovered": 67, "coverageComplete": True, "source": "Florida Department of State"}
        if d9_races:
            manifest["district9"] = {"file": "data/district-9.json", "countiesIncluded": 7, "countiesExpected": 7, "coverageComplete": True, "source": "Florida Department of State"}
        manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()
