"""Normalize Georgia Secretary of State ENR contests into national-core records."""
from __future__ import annotations
from typing import Any


def _int(value: Any, field: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {field}") from exc
    if result < 0:
        raise ValueError(f"negative {field}")
    return result


def normalize_georgia_contest(raw: dict[str, Any], *, scope: str) -> dict[str, Any]:
    title = str(raw.get("title", "")).strip()
    if not title:
        raise ValueError("contest title is required")

    reporting = raw.get("reporting") or {}
    reported = _int(reporting.get("reported"), "reported localities")
    total = _int(reporting.get("total"), "total localities")
    if total == 0 or reported > total:
        raise ValueError("invalid locality reporting coverage")

    candidates = []
    for candidate in raw.get("candidates") or []:
        name = str(candidate.get("name", "")).strip()
        if not name:
            raise ValueError("candidate name is required")
        candidates.append({
            "name": name,
            "party": str(candidate.get("party", "")).strip() or None,
            "votes": _int(candidate.get("votes"), "candidate votes"),
        })
    if not candidates:
        raise ValueError("contest candidates are required")

    complete = reported == total
    # ENR's district-scoped totals are authoritative; do not manufacture totals
    # from whole counties when a district can split counties.
    leader = max(candidates, key=lambda x: x["votes"])["name"] if complete else None
    return {
        "state": "GA",
        "scope": scope,
        "contest": title,
        "district": raw.get("district"),
        "reporting": {"reported": reported, "total": total, "complete": complete},
        "candidates": candidates,
        "leader": leader,
        "aggregateLeaderPublishable": complete,
        "sourceAuthority": "Georgia Secretary of State",
    }


def normalize_georgia_scope(raw_contests: list[dict[str, Any]], *, scope: str) -> dict[str, Any]:
    allowed = {"statewide", "congressional", "legislative", "local"}
    if scope not in allowed:
        raise ValueError(f"unsupported Georgia scope: {scope}")
    contests = [normalize_georgia_contest(item, scope=scope) for item in raw_contests]
    return {
        "state": "GA",
        "scope": scope,
        "status": "research-only",
        "publishable": False,
        "contests": contests,
    }
