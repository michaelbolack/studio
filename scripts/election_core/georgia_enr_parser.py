"""Parse Georgia Secretary of State ENR rendered text into raw contest records.

The official ENR site exposes stable human-readable contest blocks. This parser is
transport-agnostic: callers fetch the official page and pass its rendered text here.
It fails closed rather than guessing when reporting/candidate structure is absent.
"""
from __future__ import annotations
import re
from typing import Any

REPORTING_RE = re.compile(r"(?:Localities|Precincts) reporting\s+(\d+)\s*/\s*(\d+)", re.I)
PERCENT_VOTES_RE = re.compile(r"^(\d+(?:\.\d+)?)%\s+([\d,]+)$")
DISTRICT_RE = re.compile(r"District\s+(\d+)", re.I)


def infer_scope(title: str) -> str:
    lowered = title.lower()
    if "us house of representatives" in lowered:
        return "congressional"
    if "state senate" in lowered or "state house of representatives" in lowered:
        return "legislative"
    return "statewide"


def parse_contest_block(title: str, lines: list[str]) -> dict[str, Any]:
    reporting = None
    candidates = []
    pending_name = None
    pending_party = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        match = REPORTING_RE.search(line)
        if match:
            reporting = {"reported": int(match.group(1)), "total": int(match.group(2))}
            continue
        pv = PERCENT_VOTES_RE.match(line)
        if pv and pending_name:
            candidates.append({"name": pending_name, "party": pending_party, "votes": int(pv.group(2).replace(",", ""))})
            pending_name = pending_party = None
            continue
        if line.upper() in {"REP", "DEM", "LIB", "IND"} and pending_name:
            pending_party = line.upper()
            continue
        if line in {"Vote for 1", "Vote Method", "Candidate", "Percentage", "Votes", "Follow"}:
            continue
        if line.startswith(("Localities reporting", "Precincts reporting", "View results", "As of")):
            continue
        # Candidate names immediately precede party/percentage-vote lines in ENR text.
        pending_name = line
        pending_party = None

    if reporting is None:
        raise ValueError(f"missing reporting coverage for Georgia contest: {title}")
    if not candidates:
        raise ValueError(f"missing candidates for Georgia contest: {title}")
    district_match = DISTRICT_RE.search(title)
    return {
        "title": title.strip(),
        "district": district_match.group(1) if district_match else None,
        "reporting": reporting,
        "candidates": candidates,
    }


def parse_enr_contests(text: str) -> dict[str, list[dict[str, Any]]]:
    """Parse rendered ENR text where contest headings are prefixed with '## '."""
    sections: list[tuple[str, list[str]]] = []
    current_title = None
    current_lines: list[str] = []
    for raw in text.splitlines():
        if raw.startswith("## "):
            if current_title is not None:
                sections.append((current_title, current_lines))
            current_title = raw[3:].strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(raw)
    if current_title is not None:
        sections.append((current_title, current_lines))

    grouped = {"statewide": [], "congressional": [], "legislative": [], "local": []}
    for title, lines in sections:
        if not any(REPORTING_RE.search(line) for line in lines):
            continue
        contest = parse_contest_block(title, lines)
        grouped[infer_scope(title)].append(contest)
    if not any(grouped.values()):
        raise ValueError("no Georgia ENR contests found")
    return grouped
