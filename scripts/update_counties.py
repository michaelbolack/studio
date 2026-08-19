import csv, io, json, os, re, sys
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

INDEX_URL = "https://www.freshtake.vote/2026P/enr.php"
ELECTION_DATE = "2026-08-18"
OUT_DIR = "data"
HEADERS = {"User-Agent": "IRC-Media-Election-Center/1.0"}
STATEWIDE_OFFICES = {
    "united states senator": "United States Senator",
    "governor and lieutenant governor": "Governor and Lieutenant Governor",
    "chief financial officer": "Chief Financial Officer",
    "commissioner of agriculture": "Commissioner of Agriculture",
}
CD9_COUNTIES = {"Glades", "Highlands", "Indian River", "Okeechobee", "Orange", "Osceola", "Polk"}
CD9_CANDIDATES = {
    "benbutler", "marcuscarter", "thomasechalifouxjr", "dangreen",
    "jorgemartinez", "steverance", "justinstory"
}

def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

def clean_num(v):
    if v is None: return 0
    s = str(v).strip().replace(",", "").replace("%", "")
    if s in {"", "-", "—", "N/A"}: return 0
    try: return int(float(s))
    except Exception: return 0

def pct(v):
    if v is None: return 0.0
    s = str(v).strip().replace("%", "")
    if s in {"", "-", "—", "N/A"}: return 0.0
    try: return float(s)
    except Exception: return 0.0

def discover_counties():
    r = requests.get(INDEX_URL, headers=HEADERS, timeout=30); r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser"); found = {}
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 3: continue
        county = cells[0].get_text(" ", strip=True); date = cells[1].get_text(" ", strip=True)
        a = cells[2].find("a", href=True)
        if county and date == ELECTION_DATE and a: found[county] = urljoin(INDEX_URL, a["href"])
    return found

def extract_stats(html):
    text = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
    def after(label):
        m = re.search(re.escape(label) + r"\s*:?\s*([0-9,]+(?:\s*/\s*[0-9,]+)?|[0-9.]+%)", text, re.I)
        return m.group(1) if m else ""
    precincts = after("Precincts Reporting"); pr, pt = 0, 0
    if "/" in precincts:
        a,b = precincts.split("/",1); pr, pt = clean_num(a), clean_num(b)
    m = re.search(r"Website last updated at:\s*([^\n]+)", text, re.I)
    return {"registeredVoters": clean_num(after("Registered Voters")), "ballotsCast": clean_num(after("Ballots Cast")) or clean_num(after("Ballots Counted")), "precinctsReporting": pr, "precinctsTotal": pt, "lastUpdated": m.group(1).strip("() ") if m else datetime.now(timezone.utc).isoformat()}

def csv_sort_key(href):
    m = re.search(r"(20\d{2}-\d{2}-\d{2}T\d{2}[:_-]\d{2}[:_-]\d{2})", href)
    if m:
        raw = m.group(1).replace("_", ":")
        try: return (1, datetime.fromisoformat(raw).timestamp())
        except Exception: pass
    return (0, href)

def find_csv(summary_url):
    reports_url = re.sub(r"/Summary/?$", "/Reports/", summary_url)
    reports_url = re.sub(r"/Summary/([0-9]+)/?$", r"/Reports/\1/", reports_url)
    sep = "&" if "?" in reports_url else "?"
    r = requests.get(reports_url + sep + "_=" + str(int(datetime.now(timezone.utc).timestamp())), headers=HEADERS, timeout=30)
    r.raise_for_status(); soup = BeautifulSoup(r.text, "html.parser")
    preferred, fallback = [], []
    for a in soup.find_all("a", href=True):
        label = a.get_text(" ", strip=True).lower(); href = a["href"]; full = urljoin(reports_url, href)
        if href.lower().endswith(".csv"):
            fallback.append(full)
            if "candidate summary results by party" in label or "candidatesummaryresultsbyparty" in href.lower(): preferred.append(full)
    choices = preferred or fallback
    if not choices: raise RuntimeError("CSV report link not found")
    return max(choices, key=csv_sort_key)

def normalize_row(row): return {str(k).strip().lower(): (v or "").strip() for k,v in row.items() if k is not None}
def pick(row, keys):
    for k in keys:
        if k in row and row[k] != "": return row[k]
    for rk, rv in row.items():
        for k in keys:
            if k in rk and rv != "": return rv
    return ""

def parse_csv(csv_text):
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff"))); races = {}
    for raw in reader:
        row = normalize_row(raw)
        contest = pick(row, ["contest name", "contest", "office", "race"])
        choice = pick(row, ["candidate/issue", "candidate name", "candidate", "choice", "name"])
        party = pick(row, ["party", "party name", "political party"])
        votes = pick(row, ["total votes", "votes", "total"]); percent = pick(row, ["percentage", "percent", "vote percent"])
        if not contest or not choice: continue
        if "undervote" in choice.lower() or "overvote" in choice.lower(): continue
        races.setdefault(contest.strip(), []).append({"name": choice.strip(), "party": party.strip() or "NON", "votes": clean_num(votes), "percent": pct(percent)})
    return [{"name": k, "candidates": v} for k,v in races.items()]

def update_one(county, summary_url):
    sep = "&" if "?" in summary_url else "?"
    r = requests.get(summary_url + sep + "_=" + str(int(datetime.now(timezone.utc).timestamp())), headers=HEADERS, timeout=30); r.raise_for_status(); stats = extract_stats(r.text)
    csv_url = find_csv(summary_url); csep = "&" if "?" in csv_url else "?"
    c = requests.get(csv_url + csep + "_=" + str(int(datetime.now(timezone.utc).timestamp())), headers=HEADERS, timeout=30); c.raise_for_status(); races = parse_csv(c.text)
    data = {"county": county, "election": "2026 Primary Election", "electionDate": ELECTION_DATE, "source": "Florida Election Night Reporting", "sourceUrl": summary_url, "csvUrl": csv_url, **stats, "races": races, "generatedAt": datetime.now(timezone.utc).isoformat()}
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, slugify(county)+".json"), "w") as f: json.dump(data, f, indent=2)
    return data

def canonical_statewide_race(name):
    s = re.sub(r"\s+", " ", name.lower()).strip()
    party = "REP" if re.search(r"(^|\b)(rep|republican)(\b|$)", s) else "DEM" if re.search(r"(^|\b)(dem|democratic)(\b|$)", s) else ""
    for needle, title in STATEWIDE_OFFICES.items():
        if needle in s or (needle == "united states senator" and ("us senator" in s or "u.s. senator" in s)):
            return (title, party)
    return None

def candidate_key(name): return re.sub(r"[^a-z0-9]+", "", name.lower())

def build_statewide(county_data, total_discovered):
    agg = {}; county_names = []; precincts_reporting = precincts_total = ballots = 0; latest = ""
    for data in county_data:
        county_names.append(data.get("county", "")); ballots += int(data.get("ballotsCast") or 0)
        precincts_reporting += int(data.get("precinctsReporting") or 0); precincts_total += int(data.get("precinctsTotal") or 0); latest = max(latest, data.get("generatedAt", ""))
        for race in data.get("races", []):
            canon = canonical_statewide_race(race.get("name", ""))
            if not canon: continue
            office, race_party = canon; key = office + "|" + race_party
            bucket = agg.setdefault(key, {"name": (race_party + " " if race_party else "") + office, "type": "statewide", "candidates": {}})
            for c in race.get("candidates", []):
                cparty = (c.get("party") or race_party or "NON").upper()
                if race_party and cparty in {"REP","DEM"} and cparty != race_party: continue
                ck = candidate_key(c.get("name", ""))
                if not ck: continue
                item = bucket["candidates"].setdefault(ck, {"name": c.get("name", ""), "party": cparty, "votes": 0}); item["votes"] += int(c.get("votes") or 0)
    races = []
    for bucket in agg.values():
        candidates = list(bucket["candidates"].values()); total = sum(c["votes"] for c in candidates)
        for c in candidates: c["percent"] = round((c["votes"] / total * 100) if total else 0, 2)
        races.append({"name": bucket["name"], "type": "statewide", "candidates": candidates})
    races.sort(key=lambda r: r["name"])
    statewide = {"scope": "Florida", "election": "2026 Primary Election", "electionDate": ELECTION_DATE, "source": "Aggregated official Florida county Election Night Reporting feeds", "countiesIncluded": len(county_data), "countiesDiscovered": total_discovered, "coverageComplete": len(county_data) == total_discovered and total_discovered >= 67, "countyNames": sorted(x for x in county_names if x), "ballotsCast": ballots, "precinctsReporting": precincts_reporting, "precinctsTotal": precincts_total, "lastUpdated": latest or datetime.now(timezone.utc).isoformat(), "races": races, "generatedAt": datetime.now(timezone.utc).isoformat()}
    with open(os.path.join(OUT_DIR, "statewide.json"), "w") as f: json.dump(statewide, f, indent=2)
    return statewide

def build_cd9(county_data):
    totals = {k: None for k in CD9_CANDIDATES}; included = []; latest = ""
    for data in county_data:
        county = data.get("county", "")
        if county not in CD9_COUNTIES: continue
        matched_race = None
        for race in data.get("races", []):
            keys = {candidate_key(c.get("name", "")) for c in race.get("candidates", [])}
            if len(keys & CD9_CANDIDATES) >= 3:
                matched_race = race; break
        if not matched_race: continue
        included.append(county); latest = max(latest, data.get("generatedAt", ""))
        for c in matched_race.get("candidates", []):
            ck = candidate_key(c.get("name", ""))
            if ck not in CD9_CANDIDATES: continue
            if totals[ck] is None: totals[ck] = {"name": c.get("name", ""), "party": (c.get("party") or "REP").upper(), "votes": 0}
            totals[ck]["votes"] += int(c.get("votes") or 0)
    candidates = [v for v in totals.values() if v is not None]; total = sum(c["votes"] for c in candidates)
    for c in candidates: c["percent"] = round((c["votes"] / total * 100) if total else 0, 2)
    district = {"scope": "Florida Congressional District 9", "district": 9, "election": "2026 Primary Election", "electionDate": ELECTION_DATE, "source": "Aggregated official Florida county Election Night Reporting feeds for Congressional District 9", "countiesIncluded": len(included), "countiesExpected": len(CD9_COUNTIES), "countyNames": sorted(included), "coverageComplete": set(included) == CD9_COUNTIES, "lastUpdated": latest or datetime.now(timezone.utc).isoformat(), "races": [{"name": "REP Representative in Congress", "type": "congress", "district": 9, "candidates": candidates}], "generatedAt": datetime.now(timezone.utc).isoformat()}
    with open(os.path.join(OUT_DIR, "district-9.json"), "w") as f: json.dump(district, f, indent=2)
    return district

def main():
    counties = discover_counties(); os.makedirs(OUT_DIR, exist_ok=True)
    manifest = {"generatedAt": datetime.now(timezone.utc).isoformat(), "counties": {}}; successful = []
    for county, url in counties.items():
        try:
            data = update_one(county, url); successful.append(data)
            manifest["counties"][county] = {"connected": True, "file": f"data/{slugify(county)}.json", "sourceUrl": url, "races": len(data["races"])}
            print(f"OK {county}: {len(data['races'])} races")
        except Exception as e:
            manifest["counties"][county] = {"connected": False, "sourceUrl": url, "error": str(e)}; print(f"FAIL {county}: {e}", file=sys.stderr)
    statewide = build_statewide(successful, len(counties)); district9 = build_cd9(successful)
    manifest["statewide"] = {"file": "data/statewide.json", "countiesIncluded": statewide["countiesIncluded"], "countiesDiscovered": statewide["countiesDiscovered"], "coverageComplete": statewide["coverageComplete"]}
    manifest["district9"] = {"file": "data/district-9.json", "countiesIncluded": district9["countiesIncluded"], "countiesExpected": district9["countiesExpected"], "coverageComplete": district9["coverageComplete"]}
    with open(os.path.join(OUT_DIR, "manifest.json"), "w") as f: json.dump(manifest, f, indent=2)
    print(f"Connected {len(successful)}/{len(counties)} counties; statewide={len(statewide['races'])} race groups; CD9={district9['countiesIncluded']}/{district9['countiesExpected']} county feeds")

if __name__ == "__main__": main()
