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
        if getattr(node, "name", None) == "input" and race_title_for_input(node, soup):
            break
        if isinstance(node, NavigableString):
            text = re.sub(r"\s+", " ", str(node)).strip()
            if text:
                tokens.append(text)
    return tokens


def parse_candidate_tokens(tokens):
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


def inspect_html(html):
    soup = BeautifulSoup(html, "html.parser")
    strings = [re.sub(r"\s+", " ", x).strip() for x in soup.stripped_strings]
    controls = []
    for inp in soup.find_all("input"):
        title = race_title_for_input(inp, soup)
        if title:
            controls.append(title)
    return {
        "bytes": len(html.encode("utf-8", errors="ignore")),
        "inputCount": len(soup.find_all("input")),
        "raceControlCount": len(controls),
        "candidateTokenCount": sum(1 for x in strings if candidate_line(x)),
        "percentTokenCount": sum(1 for x in strings if re.match(r"^-?[0-9]+(?:\.[0-9]+)?%$", x)),
        "sampleRaceControls": controls[:5],
        "sampleCandidateTokens": [x for x in strings if candidate_line(x)][:5],
    }


def parse_visible_text(html):
    soup = BeautifulSoup(html, "html.parser")
    races = {}
    for inp in soup.find_all("input"):
        title = race_title_for_input(inp, soup)
        if not title:
            continue
        candidates = parse_candidate_tokens(tokens_for_race(inp, soup))
        if candidates and sum(c["votes"] for c in candidates) > 0:
            old = races.get(title)
            if old is None or len(candidates) > len(old):
                races[title] = candidates
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
            candidates = parse_candidate_tokens(block)
            if candidates and sum(c["votes"] for c in candidates) > 0:
                races[title] = candidates
            i = max(j, i + 1)
    return [{"name": title, "candidates": candidates} for title, candidates in races.items()]


def recover(county, entry):
    url = entry.get("sourceUrl", "")
    if "enr.electionsfl.org" not in url:
        raise RuntimeError("not a Florida ENR summary URL")
    sep = "&" if "?" in url else "?"
    requested_url = url + sep + "_=" + str(int(datetime.now(timezone.utc).timestamp()))
    r = requests.get(requested_url, headers=HEADERS, timeout=12)
    diagnostics = {
        "requestedUrl": requested_url,
        "finalUrl": r.url,
        "httpStatus": r.status_code,
        "contentType": r.headers.get("content-type"),
        **inspect_html(r.text),
    }
    r.raise_for_status()
    races = parse_visible_text(r.text)
    vote_total = sum(c.get("votes", 0) for race in races for c in race.get("candidates", []))
    diagnostics.update({
        "parsedRaceCount": len(races),
        "parsedCandidateCount": sum(len(x.get("candidates", [])) for x in races),
        "parsedVoteTotal": vote_total,
    })
    if not races or vote_total <= 0:
        err = RuntimeError("official summary control parser produced no nonzero candidate totals")
        err.diagnostics = diagnostics
        raise err
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
    return data, diagnostics


def should_force_recovery(entry):
    error = (entry.get("error") or "").lower()
    return bool(
        entry.get("validationFailed")
        or "zero" in error
        or "candidate vote totals" in error
        or "integrity gate" in error
    )


def main():
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)
    recovered = []
    attempted = []
    errors = {}
    diagnostics = {}
    for county in sorted(TARGETS):
        entry = manifest.get("counties", {}).get(county, {})
        # A validation-failed feed must be retried even if an earlier stage still
        # carries connected=true. Final integrity may quarantine it later, so
        # connected alone is not evidence the feed is safe.
        if entry.get("connected") and not should_force_recovery(entry):
            continue
        attempted.append(county)
        try:
            data, diag = recover(county, entry)
            diagnostics[county] = diag
            manifest["counties"][county] = {
                "connected": True,
                "file": f"data/{core.slugify(county)}.json",
                "sourceUrl": entry.get("sourceUrl"),
                "races": len(data["races"]),
                "adapter": "florida-enr-summary-controls",
            }
            recovered.append(county)
            print(f"CONTROL SUMMARY OK {county}: {len(data['races'])} races; {diag}")
        except Exception as e:
            errors[county] = str(e)
            diagnostics[county] = getattr(e, "diagnostics", {"exception": repr(e)})
            print(f"CONTROL SUMMARY FAIL {county}: {e}; diagnostics={diagnostics[county]}")
    manifest["directTextSummaryRecovery"] = {
        "attempted": attempted,
        "recovered": recovered,
        "errors": errors,
        "diagnostics": diagnostics,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()
