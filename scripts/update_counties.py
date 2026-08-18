import csv, io, json, os, re, sys, time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

INDEX_URL = "https://www.freshtake.vote/2026P/enr.php"
ELECTION_DATE = "2026-08-18"
OUT_DIR = "data"
HEADERS = {"User-Agent": "IRC-Media-Election-Center/1.0"}


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def clean_num(v):
    if v is None:
        return 0
    s = str(v).strip().replace(",", "").replace("%", "")
    if s in {"", "-", "—", "N/A"}:
        return 0
    try:
        return int(float(s))
    except Exception:
        return 0


def pct(v):
    if v is None:
        return 0.0
    s = str(v).strip().replace("%", "")
    if s in {"", "-", "—", "N/A"}:
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0


def discover_counties():
    r = requests.get(INDEX_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    found = {}
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 3:
            continue
        county = cells[0].get_text(" ", strip=True)
        date = cells[1].get_text(" ", strip=True)
        a = cells[2].find("a", href=True)
        if county and date == ELECTION_DATE and a:
            found[county] = urljoin(INDEX_URL, a["href"])
    return found


def extract_stats(html):
    text = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
    def after(label):
        m = re.search(re.escape(label) + r"\s*:?\s*([0-9,]+(?:\s*/\s*[0-9,]+)?|[0-9.]+%)", text, re.I)
        return m.group(1) if m else ""
    precincts = after("Precincts Reporting")
    pr, pt = 0, 0
    if "/" in precincts:
        a,b = precincts.split("/",1)
        pr, pt = clean_num(a), clean_num(b)
    updated = ""
    m = re.search(r"Website last updated at:\s*([^\n]+)", text, re.I)
    if m:
        updated = m.group(1).strip("() ")
    return {
        "registeredVoters": clean_num(after("Registered Voters")),
        "ballotsCast": clean_num(after("Ballots Cast")) or clean_num(after("Ballots Counted")),
        "precinctsReporting": pr,
        "precinctsTotal": pt,
        "lastUpdated": updated or datetime.now(timezone.utc).isoformat()
    }


def find_csv(summary_url):
    # Most Florida ENR sites use the same election id with a /Reports/ route.
    reports_url = re.sub(r"/Summary/?$", "/Reports/", summary_url)
    reports_url = re.sub(r"/Summary/([0-9]+)/?$", r"/Reports/\1/", reports_url)
    r = requests.get(reports_url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.find_all("a", href=True):
        label = a.get_text(" ", strip=True).lower()
        href = a["href"]
        if "candidate summary results by party" in label and "csv" in label:
            return urljoin(reports_url, href)
    for a in soup.find_all("a", href=True):
        if a["href"].lower().endswith(".csv"):
            return urljoin(reports_url, a["href"])
    raise RuntimeError("CSV report link not found")


def normalize_row(row):
    return {str(k).strip().lower(): (v or "").strip() for k,v in row.items() if k is not None}


def pick(row, keys):
    for k in keys:
        if k in row and row[k] != "":
            return row[k]
    # fuzzy fallback
    for rk, rv in row.items():
        for k in keys:
            if k in rk and rv != "":
                return rv
    return ""


def parse_csv(csv_text):
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    races = {}
    for raw in reader:
        row = normalize_row(raw)
        contest = pick(row, ["contest name", "contest", "office", "race"])
        choice = pick(row, ["candidate/issue", "candidate name", "candidate", "choice", "name"])
        party = pick(row, ["party", "party name", "political party"])
        votes = pick(row, ["total votes", "votes", "total"])
        percent = pick(row, ["percentage", "percent", "vote percent"])
        if not contest or not choice:
            continue
        if "undervote" in choice.lower() or "overvote" in choice.lower():
            continue
        key = contest.strip()
        races.setdefault(key, [])
        races[key].append({
            "name": choice.strip(),
            "party": party.strip() or "NON",
            "votes": clean_num(votes),
            "percent": pct(percent)
        })
    return [{"name": k, "candidates": v} for k,v in races.items()]


def update_one(county, summary_url):
    r = requests.get(summary_url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    stats = extract_stats(r.text)
    csv_url = find_csv(summary_url)
    c = requests.get(csv_url, headers=HEADERS, timeout=30)
    c.raise_for_status()
    races = parse_csv(c.text)
    data = {
        "county": county,
        "election": "2026 Primary Election",
        "electionDate": ELECTION_DATE,
        "source": "Florida Election Night Reporting",
        "sourceUrl": summary_url,
        "csvUrl": csv_url,
        **stats,
        "races": races,
        "generatedAt": datetime.now(timezone.utc).isoformat()
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, slugify(county)+".json"), "w") as f:
        json.dump(data, f, indent=2)
    return len(races)


def main():
    counties = discover_counties()
    os.makedirs(OUT_DIR, exist_ok=True)
    manifest = {"generatedAt": datetime.now(timezone.utc).isoformat(), "counties": {}}
    failures = []
    for county, url in counties.items():
        try:
            n = update_one(county, url)
            manifest["counties"][county] = {"connected": True, "file": f"data/{slugify(county)}.json", "sourceUrl": url, "races": n}
            print(f"OK {county}: {n} races")
        except Exception as e:
            manifest["counties"][county] = {"connected": False, "sourceUrl": url, "error": str(e)}
            failures.append((county, str(e)))
            print(f"FAIL {county}: {e}", file=sys.stderr)
    with open(os.path.join(OUT_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Connected {sum(1 for x in manifest['counties'].values() if x['connected'])}/{len(manifest['counties'])} counties")
    # Partial failures should not stop successful counties from publishing.

if __name__ == "__main__":
    main()
