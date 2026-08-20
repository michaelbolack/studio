import json
import os
import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup, NavigableString

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


def race_title_for_input(inp, soup):
    # Different Florida ENR counties expose the contest title differently.
    # Prefer explicit accessibility attributes, then the associated <label>.
    for attr in ("aria-label", "title", "value"):
        value = inp.get(attr)
        if value and race_line(value):
            return re.sub(r"\s+", " ", value).strip()

    input_id = inp.get("id")
    if input_id:
        label = soup.find("label", attrs={"for": input_id})
        if label:
            value = label.get_text(" ", strip=True)
            if race_line(value):
                return re.sub(r"\s+", " ", value).strip()

    parent_label = inp.find_parent("label")
    if parent_label:
        value = parent_label.get_text(" ", strip=True)
        if race_line(value):
            return re.sub(r"\s+", " ", value).strip()

    # Some ENR templates place the visible contest label immediately before
    # the input instead of linking it with a for/id pair.
    for node in inp.find_all_previous(["label", "legend", "h1", "h2", "h3", "h4", "h5", "span", "div"], limit=30):
        value = node.get_text(" ", strip=True)
        if race_line(value) and len(value) <= 180:
            return re.sub(r"\s+", " ", value).strip()
    return None


def tokens_for_race(inp, soup):
    tokens = []
    for node in inp.next_elements:
        if node is inp:
            continue
        if getattr(node, "name", None) == "input":
            next_title = race_title_for_input(node, soup)
            if next_title:
                break
        if isinstance(node, NavigableString):
            text = re.sub(r"\s+", " ", str(node)).strip()
            if text:
                tokens.append(text)
    return tokens


def parse_candidate_tokens(tokens, race_name):
    pct_re = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?%$")
    num_re = re.compile(r"^[0-9][0-9,]*$")
    candidates = []
    for i, token in enumerate(tokens):
        if not candidate_line(token):
            continue
        name, party = clean_candidate(token)
        if not name or core.is_stats_choice(name):
            continue
        pct_val = None
        votes_val = None
        for nxt in tokens[i + 1:min(len(tokens), i + 14)]:
            if candidate_line(nxt):
                break
            if pct_val is None and pct_re.match(nxt):
                pct_val = core.pct(nxt)
                continue
            if pct_val is not None and num_re.match(nxt):
                votes_val = core.clean_num(nxt)
                break
        if votes_val is not None:
            candidates.append({"name": name, "party": party, "votes": votes_val, "percent": pct_val or 0.0})

    dedup = {}
    for c in candidates:
        key = (core.candidate_key(c["name"]), c["party"])
        if key and (key not in dedup or c["votes"] > dedup[key]["votes"]):
            dedup[key] = c
    cands = list(dedup.values())
    total = sum(c["votes"] for c in cands)
    if total:
        for c in cands:
            c["percent"] = round(c["votes"] * 100 / total, 2)
    return cands


def parse_visible_text(html):
    soup = BeautifulSoup(html, "html.parser")
    races = {}

    # Primary path: contest controls define reliable race boundaries even when
    # their titles are not ordinary text nodes.
    for inp in soup.find_all("input"):
        title = race_title_for_input(inp, soup)
        if not title:
            continue
        candidates = parse_candidate_tokens(tokens_for_race(inp, soup), title)
        if not candidates or sum(c["votes"] for c in candidates) <= 0:
            continue
        old = races.get(title)
        if old is None or len(candidates) > len(old):
            races[title] = candidates

    # Secondary fallback for templates where race titles really are text nodes.
    if not races:
        lines = [re.sub(r"\s+", " ", x).strip() for x in soup.stripped_strings]
        i = 0
        while i < len(lines):
            title = lines[i]
            if not race_line(title):
                i += 1
                continue
            j = i + 1
            block = []
            while j < len(lines) and not race_line(lines[j]):
                block.append(lines[j])
                j += 1
            candidates = parse_candidate_tokens(block, title)
            if candidates and sum(c["votes"] for c in candidates) > 0:
                races[title] = candidates
            i = max(j, i + 1)

    return [{"name": title, "candidates": candidates} for title, candidates in races.items()]


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
        raise RuntimeError("official summary control parser produced no nonzero candidate totals")
    stats = core.extract_stats(r.text)
    data = {
        "county": county,
        "election": "2026 Primary Election",
        "electionDate": core.ELECTION_DATE,
        "source": "Florida Election Night Reporting — Official Summary",
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
    attempted = []
    errors = {}
    for county in sorted(TARGETS):
        entry = manifest.get("counties", {}).get(county, {})
        if entry.get("connected"):
            continue
        attempted.append(county)
        try:
            data = recover(county, entry)
            manifest["counties"][county] = {
                "connected": True,
                "file": f"data/{core.slugify(county)}.json",
                "sourceUrl": entry.get("sourceUrl"),
                "races": len(data["races"]),
                "adapter": "florida-enr-summary-controls",
            }
            recovered.append(county)
            print(f"CONTROL SUMMARY OK {county}: {len(data['races'])} races")
        except Exception as e:
            errors[county] = str(e)
            print(f"CONTROL SUMMARY FAIL {county}: {e}")
    manifest["directTextSummaryRecovery"] = {
        "attempted": attempted,
        "recovered": recovered,
        "errors": errors,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()
