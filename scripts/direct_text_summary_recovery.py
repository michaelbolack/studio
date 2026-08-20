import json
import os
import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

import update_counties as core

OUT_DIR = "data"
HEADERS = {"User-Agent": "IRC-Media-Election-Center/1.0"}
TARGETS = {"Flagler", "Nassau"}


def race_line(text):
    s = re.sub(r"\s+", " ", (text or "")).strip()
    low = s.lower()
    if not s or len(s) > 180:
        return False
    keywords = (
        "senator", "governor", "representative", "commissioner", "school board",
        "sheriff", "judge", "tax collector", "property appraiser", "supervisor of elections",
        "city council", "council member", "mayor", "referendum", "amendment",
        "county commission", "board of county commissioners", "state attorney",
        "public defender", "agriculture", "financial officer"
    )
    return any(k in low for k in keywords)


def candidate_line(text):
    return re.search(r"\((REP|DEM|NPA|NON)\)\s*$", text or "", re.I) is not None


def clean_candidate(text):
    s = re.sub(r"\s+", " ", text or "").strip()
    m = re.search(r"\((REP|DEM|NPA|NON)\)\s*$", s, re.I)
    if not m:
        return s, "NON"
    party = m.group(1).upper().replace("NPA", "NON")
    return s[:m.start()].strip(), party


def parse_visible_text(html):
    soup = BeautifulSoup(html, "html.parser")
    lines = [re.sub(r"\s+", " ", x).strip() for x in soup.stripped_strings]
    pct_re = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?%$")
    num_re = re.compile(r"^[0-9][0-9,]*$")
    races = []
    i = 0
    while i < len(lines):
        title = lines[i]
        if not race_line(title):
            i += 1
            continue
        j = i + 1
        candidates = []
        while j < len(lines) and not race_line(lines[j]):
            if candidate_line(lines[j]):
                name, party = clean_candidate(lines[j])
                pct_val = None
                votes_val = None
                k = j + 1
                while k < min(len(lines), j + 12) and not race_line(lines[k]) and not candidate_line(lines[k]):
                    if pct_val is None and pct_re.match(lines[k]):
                        pct_val = core.pct(lines[k])
                    elif pct_val is not None and num_re.match(lines[k]):
                        votes_val = core.clean_num(lines[k])
                        break
                    k += 1
                if votes_val is not None and name and not core.is_stats_choice(name):
                    candidates.append({"name": name, "party": party, "votes": votes_val, "percent": pct_val or 0.0})
            j += 1
        if candidates:
            dedup = {}
            for c in candidates:
                key = (core.candidate_key(c["name"]), c["party"])
                if key and (key not in dedup or c["votes"] > dedup[key]["votes"]):
                    dedup[key] = c
            cands = list(dedup.values())
            total = sum(c["votes"] for c in cands)
            if total > 0:
                for c in cands:
                    c["percent"] = round(c["votes"] * 100 / total, 2)
                races.append({"name": title, "candidates": cands})
        i = max(j, i + 1)
    return races


def recover(county, entry):
    url = entry.get("sourceUrl", "")
    if "enr.electionsfl.org" not in url:
        return None
    sep = "&" if "?" in url else "?"
    r = requests.get(url + sep + "_=" + str(int(datetime.now(timezone.utc).timestamp())), headers=HEADERS, timeout=12)
    r.raise_for_status()
    races = parse_visible_text(r.text)
    vote_total = sum(c.get("votes", 0) for race in races for c in race.get("candidates", []))
    if not races or vote_total <= 0:
        raise RuntimeError("official summary text parser produced no nonzero candidate totals")
    stats = core.extract_stats(r.text)
    if (stats.get("ballotsCast") or stats.get("precinctsReporting")) and vote_total <= 0:
        raise RuntimeError("reporting present but parsed candidate votes are zero")
    data = {
        "county": county,
        "election": "2026 Primary Election",
        "electionDate": core.ELECTION_DATE,
        "source": "Florida Election Night Reporting — Official Summary Text",
        "sourceUrl": url,
        **stats,
        "races": races,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    path = os.path.join(OUT_DIR, core.slugify(county) + ".json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return data


def main():
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)
    recovered = []
    for county in TARGETS:
        entry = manifest.get("counties", {}).get(county, {})
        if entry.get("connected"):
            continue
        try:
            data = recover(county, entry)
            manifest["counties"][county] = {
                "connected": True,
                "file": f"data/{core.slugify(county)}.json",
                "sourceUrl": entry.get("sourceUrl"),
                "races": len(data["races"]),
                "adapter": "florida-enr-summary-text",
            }
            recovered.append(county)
            print(f"TEXT SUMMARY OK {county}: {len(data['races'])} races")
        except Exception as e:
            print(f"TEXT SUMMARY FAIL {county}: {e}")
    manifest["directTextSummaryRecovery"] = {
        "recovered": recovered,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()
