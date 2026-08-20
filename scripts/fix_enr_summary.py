import json, os, re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup, NavigableString

import update_counties as core

HEADERS = {"User-Agent": "IRC-Media-Election-Center/1.0"}
OUT_DIR = "data"


def plausible_race_name(text):
    s = (text or "").strip()
    if not s or len(s) > 180:
        return False
    low = s.lower()
    keywords = (
        "senator", "governor", "representative", "commissioner", "school board",
        "sheriff", "judge", "tax collector", "property appraiser", "supervisor of elections",
        "city council", "mayor", "referendum", "amendment", "county commission",
        "state attorney", "public defender", "agriculture", "financial officer"
    )
    return any(k in low for k in keywords)


def race_name_for_table(table):
    for node in table.find_all_previous(limit=120):
        if getattr(node, "name", None) == "input":
            for attr in ("value", "aria-label", "title"):
                value = node.get(attr)
                if plausible_race_name(value):
                    return value.strip()
        if getattr(node, "name", None) in {"h1", "h2", "h3", "h4", "h5", "legend", "label"}:
            text = node.get_text(" ", strip=True)
            if plausible_race_name(text):
                return text
    return None


def clean_candidate(text):
    text = re.sub(r"\s+", " ", (text or "")).strip()
    party = "NON"
    m = re.search(r"\((REP|DEM|NPA|NON)\)\s*$", text, re.I)
    if m:
        party = m.group(1).upper().replace("NPA", "NON")
        text = text[:m.start()].strip()
    return text, party


def infer_party(race_name, party):
    if party != "NON":
        return party
    low = (race_name or "").lower()
    if re.search(r"(^|\b)(rep|republican)(\b|$)", low): return "REP"
    if re.search(r"(^|\b)(dem|democratic)(\b|$)", low): return "DEM"
    return "NON"


def dedupe_candidates(candidates):
    dedup = {}
    for c in candidates:
        key = (core.candidate_key(c["name"]), c["party"])
        if not key:
            continue
        if key not in dedup or c["votes"] > dedup[key]["votes"]:
            dedup[key] = c
    candidates = list(dedup.values())
    total = sum(c["votes"] for c in candidates)
    if total:
        for c in candidates:
            c["percent"] = round(c["votes"] / total * 100, 2)
    return candidates


def parse_summary_tables(html):
    soup = BeautifulSoup(html, "html.parser")
    races = {}
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        header_cells = rows[0].find_all(["th", "td"])
        headers = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)).lower() for c in header_cells]
        if not headers or not any("choice" == h or h.startswith("choice") for h in headers):
            continue
        try:
            choice_i = next(i for i,h in enumerate(headers) if h == "choice" or h.startswith("choice"))
            votes_i = next(i for i,h in enumerate(headers) if "total votes" in h or h == "votes")
        except StopIteration:
            continue
        pct_i = next((i for i,h in enumerate(headers) if "percentage" in h or h == "percent"), None)
        race_name = race_name_for_table(table)
        if not race_name:
            continue
        candidates = []
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) <= max(choice_i, votes_i):
                continue
            raw_name = cells[choice_i].get_text(" ", strip=True)
            name, party = clean_candidate(raw_name)
            if not name or core.is_stats_choice(name):
                continue
            votes = core.clean_num(cells[votes_i].get_text(" ", strip=True))
            percent = core.pct(cells[pct_i].get_text(" ", strip=True)) if pct_i is not None and len(cells) > pct_i else 0.0
            candidates.append({"name": name, "party": infer_party(race_name, party), "votes": votes, "percent": percent})
        candidates = dedupe_candidates(candidates)
        if candidates:
            old = races.get(race_name)
            if old is None or len(candidates) > len(old):
                races[race_name] = candidates
    return [{"name": name, "candidates": cands} for name, cands in races.items()]


def tokens_after_input(inp):
    out = []
    for node in inp.next_elements:
        if node is inp:
            continue
        if getattr(node, "name", None) == "input":
            value = node.get("value") or node.get("aria-label") or node.get("title")
            if plausible_race_name(value):
                break
        if isinstance(node, NavigableString):
            text = re.sub(r"\s+", " ", str(node)).strip()
            if text:
                out.append(text)
    return out


def parse_candidate_tokens(tokens, race_name):
    candidates = []
    headers = {"choice", "percent", "percentage", "votes", "total votes", "election day", "early votes", "vote by mail", "provisional"}
    pct_re = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?%$")
    num_re = re.compile(r"^-?[0-9][0-9,]*(?:\.0+)?$")
    for i, tok in enumerate(tokens):
        if not pct_re.match(tok):
            continue
        j = i - 1
        while j >= 0:
            prev = tokens[j].strip()
            low = prev.lower().rstrip(":")
            if low in headers or num_re.match(prev) or pct_re.match(prev) or low.startswith("participating precinct"):
                j -= 1
                continue
            break
        if j < 0:
            continue
        k = i + 1
        while k < min(len(tokens), i + 6) and not num_re.match(tokens[k]):
            k += 1
        if k >= len(tokens) or k >= i + 6:
            continue
        name, party = clean_candidate(tokens[j])
        if not name or core.is_stats_choice(name) or plausible_race_name(name):
            continue
        low_name = name.lower()
        if low_name in {"not reported", "completely reported", "partially reported", "show detailed view", "change view", "test results", "unofficial preliminary results"}:
            continue
        candidates.append({
            "name": name,
            "party": infer_party(race_name, party),
            "votes": core.clean_num(tokens[k]),
            "percent": core.pct(tok),
        })
    return dedupe_candidates(candidates)


def parse_summary_inputs(html):
    soup = BeautifulSoup(html, "html.parser")
    races = {}
    for inp in soup.find_all("input"):
        race_name = inp.get("value") or inp.get("aria-label") or inp.get("title")
        if not plausible_race_name(race_name):
            continue
        candidates = parse_candidate_tokens(tokens_after_input(inp), race_name)
        if not candidates:
            continue
        old = races.get(race_name)
        if old is None or len(candidates) > len(old):
            races[race_name] = candidates
    return [{"name": name, "candidates": cands} for name, cands in races.items()]


def parse_summary_any(html):
    table_races = parse_summary_tables(html)
    input_races = parse_summary_inputs(html)
    merged = {}
    for race in table_races + input_races:
        name = race["name"]
        old = merged.get(name)
        if old is None or len(race["candidates"]) > len(old["candidates"]):
            merged[name] = race
    return list(merged.values())


def fix_county(county, entry):
    url = entry.get("sourceUrl", "")
    if "enr.electionsfl.org" not in url:
        return None
    sep = "&" if "?" in url else "?"
    r = requests.get(url + sep + "_=" + str(int(datetime.now(timezone.utc).timestamp())), headers=HEADERS, timeout=10)
    r.raise_for_status()
    races = parse_summary_any(r.text)
    if not races:
        raise RuntimeError("No candidate result blocks found on official ENR summary page")
    stats = core.extract_stats(r.text)
    data = {
        "county": county,
        "election": "2026 Primary Election",
        "electionDate": core.ELECTION_DATE,
        "source": "Florida Election Night Reporting — Summary",
        "sourceUrl": url,
        **stats,
        "races": races,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    path = os.path.join(OUT_DIR, core.slugify(county) + ".json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return data


def rebuild_aggregates(manifest):
    county_data = []
    for county, entry in manifest.get("counties", {}).items():
        if not entry.get("connected") or not entry.get("file"):
            continue
        try:
            with open(entry["file"]) as f:
                county_data.append(json.load(f))
        except Exception as e:
            print(f"AGG SKIP {county}: {e}")
    statewide = core.build_statewide(county_data, len(manifest.get("counties", {})))
    district9 = core.build_cd9(county_data)
    manifest["statewide"] = {"file": "data/statewide.json", "countiesIncluded": statewide["countiesIncluded"], "countiesDiscovered": statewide["countiesDiscovered"], "coverageComplete": statewide["coverageComplete"]}
    manifest["district9"] = {"file": "data/district-9.json", "countiesIncluded": district9["countiesIncluded"], "countiesExpected": district9["countiesExpected"], "coverageComplete": district9["coverageComplete"]}


def main():
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)
    fixed = 0
    for county, entry in list(manifest.get("counties", {}).items()):
        if entry.get("connected"):
            continue
        try:
            data = fix_county(county, entry)
            if not data:
                continue
            manifest["counties"][county] = {"connected": True, "file": f"data/{core.slugify(county)}.json", "sourceUrl": entry.get("sourceUrl"), "races": len(data["races"]), "adapter": "florida-enr-summary"}
            fixed += 1
            print(f"SUMMARY OK {county}: {len(data['races'])} races")
        except Exception as e:
            print(f"SUMMARY FAIL {county}: {e}")
    rebuild_aggregates(manifest)
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    connected = sum(1 for x in manifest.get("counties", {}).values() if x.get("connected"))
    print(f"Summary fallback fixed {fixed} counties; connected {connected}/{len(manifest.get('counties', {}))}")


if __name__ == "__main__":
    main()
