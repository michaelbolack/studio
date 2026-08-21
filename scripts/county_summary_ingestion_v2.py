#!/usr/bin/env python3
"""Clean county/local ENR Summary-page adapter for Election Center v2.

This adapter intentionally does not call the legacy county recovery chain. It targets
counties currently configured as official fallback in data/manifest.json and attempts
to normalize their official Election Night Reporting Summary pages directly.

For this completed 2026 primary validation pass, a county is accepted only when:
- the page identifies the 2026 Primary Election dated 8/18/2026;
- ballots cast are nonzero;
- overall precinct reporting is complete;
- Election Day, Early Vote, and Vote By Mail are completely reported;
- every candidate vote cell is valid; and
- each race candidate sum equals the race total printed by the official page.

Some official ENR templates omit per-race participating-precinct labels after the
county is fully reported. In that template only, a race inherits the already-proven
county-complete reporting status; vote checksums remain mandatory.

A county that fails any rule remains official-fallback; no partial output is promoted.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; IRC-Media-Election-Center/2.0; +https://www.ircmedia.net/)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
ELECTION_DATE_DISPLAY = "8/18/2026"
ELECTION_DATE = "2026-08-18"
INPUT_PREFIX = "__ENR_INPUT__:"
NAV_LABELS = {
    "select", "summary results", "precinct results", "maps", "home", "reports",
    "reporting status", "election results", "results", "choice", "percent", "votes",
    "show detailed view", "completely reported", "election day", "early votes",
    "vote by mail", "change view", "vote type view:", "refresh", "search",
}


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def input_value(token: str) -> str | None:
    return token[len(INPUT_PREFIX):] if token.startswith(INPUT_PREFIX) else None


def visible(token: str) -> str:
    return input_value(token) if input_value(token) is not None else token


def document_tokens(soup: BeautifulSoup) -> list[str]:
    """Return DOM text plus marked input values in document order.

    Florida ENR stores race titles in input[value]. Marking those attribute-derived
    tokens lets race discovery distinguish actual contests from navigation text.
    """
    tokens: list[str] = []
    for node in soup.descendants:
        if isinstance(node, NavigableString):
            value = clean(node)
            if value:
                tokens.append(value)
        elif isinstance(node, Tag) and node.name == "input":
            value = clean(node.get("value") or "")
            if value:
                tokens.append(INPUT_PREFIX + value)
    return tokens


def integer(value: str) -> int:
    text = clean(visible(value))
    if not re.fullmatch(r"[0-9][0-9,]*", text):
        raise ValueError(f"invalid integer cell: {value!r}")
    return int(text.replace(",", ""))


def percent(value: str) -> float:
    text = clean(visible(value))
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?%", text):
        raise ValueError(f"invalid percent cell: {value!r}")
    return float(text[:-1])


def ratio(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"([0-9,]+)\s*/\s*([0-9,]+)", clean(visible(value)))
    if not match:
        raise ValueError(f"invalid reporting ratio: {value!r}")
    return int(match.group(1).replace(",", "")), int(match.group(2).replace(",", ""))


def token_after(tokens: list[str], label: str) -> str:
    target = label.lower()
    for i, token in enumerate(tokens[:-1]):
        if visible(token).lower() == target:
            return tokens[i + 1]
    raise RuntimeError(f"required summary label missing: {label}")


def parse_last_updated(tokens: list[str]) -> str:
    for token in tokens:
        match = re.search(r"Website last updated at:\s*(.*?)\)?$", visible(token), re.I)
        if match:
            return clean(match.group(1))
    raise RuntimeError("Website last updated timestamp missing")


def is_race_start(tokens: list[str], index: int) -> bool:
    if index < 0 or index >= len(tokens):
        return False
    raw = input_value(tokens[index])
    if raw is None:
        return False
    title = clean(raw)
    low = title.lower()
    if not title or low in NAV_LABELS:
        return False
    if low.endswith(("results", "results:")):
        return False
    nearby = [visible(tokens[j]).lower() for j in range(index + 1, min(len(tokens), index + 9))]
    return "participating precincts reporting:" in nearby or "choice" in nearby


def race_party(title: str) -> str:
    title = clean(title)
    match = re.search(r"\((REP|DEM)\b[^)]*\)\s*$", title, re.I)
    if match:
        return match.group(1).upper()
    match = re.match(r"^(REP|DEM)\b", title, re.I)
    return match.group(1).upper() if match else ""


def normalize_race_title(title: str) -> str:
    title = clean(title)
    party = race_party(title)
    base = re.sub(r"\s*\((REP|DEM)\b[^)]*\)\s*$", "", title, flags=re.I).strip()
    if party and re.match(rf"^{party}\b", base, re.I):
        return base
    return f"{party} {base}" if party else base


def normalize_candidate(name: str) -> tuple[str, str]:
    name = clean(name)
    match = re.search(r"\s*\((REP|DEM|NON|NPA|WRI)\)\s*$", name, re.I)
    party = match.group(1).upper() if match else ""
    clean_name = re.sub(r"\s*\((REP|DEM|NON|NPA|WRI)\)\s*$", "", name, flags=re.I).strip()
    return clean_name, party


def parse_race(
    tokens: list[str],
    start: int,
    end: int,
    county_reported: int,
    county_total: int,
) -> dict:
    title = input_value(tokens[start]) or visible(tokens[start])
    reporting_label = next(
        (
            i for i in range(start + 1, min(end, start + 10))
            if visible(tokens[i]).lower() == "participating precincts reporting:"
        ),
        None,
    )
    if reporting_label is not None and reporting_label + 1 < end:
        reported, total_precincts = ratio(tokens[reporting_label + 1])
        if total_precincts <= 0 or reported != total_precincts:
            raise RuntimeError(f"{title}: incomplete participating precincts {reported}/{total_precincts}")
        reporting_basis = "participating-precincts"
        header_search_start = reporting_label + 1
    else:
        reported, total_precincts = county_reported, county_total
        reporting_basis = "county-complete-template"
        header_search_start = start + 1

    try:
        choice_i = next(i for i in range(header_search_start, end) if visible(tokens[i]) == "Choice")
        pct_header_i = next(i for i in range(choice_i + 1, end) if visible(tokens[i]) == "Percent")
        votes_header_i = next(i for i in range(pct_header_i + 1, end) if visible(tokens[i]) == "Votes")
    except StopIteration as exc:
        raise RuntimeError(f"{title}: candidate table headers missing") from exc

    block = tokens[votes_header_i + 1:end]
    candidates = []
    used_vote_indexes: set[int] = set()
    i = 0
    while i + 2 < len(block):
        name = visible(block[i])
        pct_cell = visible(block[i + 1])
        vote_cell = visible(block[i + 2])
        if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?%", pct_cell) and re.fullmatch(r"[0-9][0-9,]*", vote_cell):
            page_pct = percent(pct_cell)
            votes = integer(vote_cell)
            candidate_name, candidate_party = normalize_candidate(name)
            if not candidate_name:
                raise RuntimeError(f"{title}: blank candidate name")
            candidates.append({
                "name": candidate_name,
                "party": candidate_party or race_party(title),
                "votes": votes,
                "pagePercent": page_pct,
            })
            used_vote_indexes.add(i + 2)
            i += 3
            continue
        i += 1

    if not candidates:
        raise RuntimeError(f"{title}: no valid candidate rows parsed")

    standalone_numbers = [
        integer(visible(value))
        for idx, value in enumerate(block)
        if idx not in used_vote_indexes and re.fullmatch(r"[0-9][0-9,]*", visible(value))
    ]
    if not standalone_numbers:
        raise RuntimeError(f"{title}: official race total missing")
    official_total = standalone_numbers[-1]
    calculated_total = sum(c["votes"] for c in candidates)
    if calculated_total != official_total:
        raise RuntimeError(f"{title}: checksum failed candidates={calculated_total}, total={official_total}")

    for candidate in candidates:
        computed = round(candidate["votes"] / official_total * 100 if official_total else 0, 2)
        if abs(computed - candidate["pagePercent"]) > 0.02:
            raise RuntimeError(
                f"{title}: percent disagreement for {candidate['name']}: "
                f"computed={computed}, official={candidate['pagePercent']}"
            )
        candidate["percent"] = computed
        candidate.pop("pagePercent", None)

    return {
        "name": normalize_race_title(title),
        "precinctsReporting": reported,
        "precinctsTotal": total_precincts,
        "reportingBasis": reporting_basis,
        "candidates": candidates,
        "validation": {
            "coverageComplete": True,
            "checksum": "passed",
            "calculatedTotal": calculated_total,
            "officialTotal": official_total,
        },
    }


def parse_county(county: str, source_url: str) -> dict:
    response = requests.get(source_url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    tokens = document_tokens(soup)
    joined = " | ".join(visible(token) for token in tokens)

    if "2026 Primary Election" not in joined:
        raise RuntimeError("wrong/missing election name")
    if f"Election Date: {ELECTION_DATE_DISPLAY}" not in joined:
        raise RuntimeError("wrong/missing election date")

    registered = integer(token_after(tokens, "Registered Voters:"))
    ballots = integer(token_after(tokens, "Ballots Cast:"))
    if registered <= 0 or ballots <= 0:
        raise RuntimeError(f"stale/empty summary metadata registered={registered}, ballots={ballots}")

    overall_reported, overall_total = ratio(token_after(tokens, "Precincts Reporting:"))
    if overall_total <= 0 or overall_reported != overall_total:
        raise RuntimeError(f"overall precinct reporting incomplete: {overall_reported}/{overall_total}")
    if sum(1 for token in tokens if visible(token).lower() == "completely reported") < 3:
        raise RuntimeError("Election Day/Early/Vote By Mail complete-report markers missing")

    starts = [i for i in range(len(tokens)) if is_race_start(tokens, i)]
    if not starts:
        raise RuntimeError("no race input sections found")

    races = []
    for pos, start in enumerate(starts):
        end = starts[pos + 1] if pos + 1 < len(starts) else len(tokens)
        races.append(parse_race(tokens, start, end, overall_reported, overall_total))

    if len({race["name"] for race in races}) != len(races):
        raise RuntimeError("duplicate normalized race names detected")

    return {
        "schemaVersion": 2,
        "county": county,
        "election": "2026 Primary Election",
        "electionDate": ELECTION_DATE,
        "source": "Florida Election Night Reporting - official county summary",
        "sourceUrl": response.url,
        "adapter": "county-summary-v2",
        "registeredVoters": registered,
        "ballotsCast": ballots,
        "precinctsReporting": overall_reported,
        "precinctsTotal": overall_total,
        "lastUpdated": parse_last_updated(tokens),
        "coverageComplete": True,
        "races": races,
    }


def slug(county: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", county.lower()).strip("-")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("build/county-summary-v2"))
    parser.add_argument("--report", type=Path, default=Path("build/county-summary-v2-report.json"))
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    fallbacks = [
        (county, entry)
        for county, entry in (manifest.get("counties") or {}).items()
        if not (entry.get("connected") and entry.get("file"))
    ]
    if not fallbacks:
        raise RuntimeError("manifest has no official-fallback counties to test")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    successes = []
    failures = []
    for county, entry in sorted(fallbacks):
        source_url = str(entry.get("sourceUrl") or "").strip()
        if not source_url:
            failures.append({"county": county, "reason": "sourceUrl missing"})
            continue
        try:
            data = parse_county(county, source_url)
            output_path = args.output_dir / f"{slug(county)}.json"
            output_path.write_text(json.dumps(data, indent=2) + "\n")
            successes.append({
                "county": county,
                "sourceUrl": source_url,
                "output": str(output_path),
                "races": len(data["races"]),
                "ballotsCast": data["ballotsCast"],
                "precinctsReporting": data["precinctsReporting"],
                "precinctsTotal": data["precinctsTotal"],
            })
            print(f"PASS {county}: {len(data['races'])} races; {data['precinctsReporting']}/{data['precinctsTotal']} precincts")
        except Exception as exc:
            failures.append({"county": county, "sourceUrl": source_url, "reason": str(exc)})
            print(f"WITHHELD {county}: {exc}", file=sys.stderr)

    report = {
        "schemaVersion": 2,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "tested",
        "fallbackCountiesTested": len(fallbacks),
        "safeToNormalize": len(successes),
        "remainOfficialFallback": len(failures),
        "successes": successes,
        "failures": failures,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(f"SUMMARY: {len(successes)}/{len(fallbacks)} safe to normalize; {len(failures)} remain fallback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
