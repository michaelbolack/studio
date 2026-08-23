"""Normalize Alabama Secretary of State election-night contests."""
from __future__ import annotations
from typing import Any


def _nonnegative_int(value: Any, field: str) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {field}") from exc
    if n < 0:
        raise ValueError(f"negative {field}")
    return n


def normalize_alabama_contest(raw: dict[str, Any], *, scope: str) -> dict[str, Any]:
    if scope not in {"statewide", "congressional", "legislative", "local"}:
        raise ValueError("unsupported Alabama scope")
    title = str(raw.get("title", "")).strip()
    if not title:
        raise ValueError("contest title is required")
    reporting = raw.get("reporting") or {}
    reported = _nonnegative_int(reporting.get("reported"), "reported units")
    total = _nonnegative_int(reporting.get("total"), "total units")
    if total == 0 or reported > total:
        raise ValueError("invalid Alabama reporting coverage")
    candidates = []
    for row in raw.get("candidates") or []:
        name = str(row.get("name", "")).strip()
        if not name:
            raise ValueError("candidate name is required")
        candidates.append({"name": name, "party": str(row.get("party", "")).strip() or None, "votes": _nonnegative_int(row.get("votes"), "candidate votes")})
    if not candidates:
        raise ValueError("contest candidates are required")
    complete = reported == total
    return {
        "state": "AL", "scope": scope, "contest": title, "district": raw.get("district"),
        "reporting": {"reported": reported, "total": total, "complete": complete},
        "candidates": candidates,
        "leader": max(candidates, key=lambda x: x["votes"])["name"] if complete else None,
        "aggregateLeaderPublishable": complete,
        "sourceAuthority": "Alabama Secretary of State",
    }


def normalize_alabama_scope(rows: list[dict[str, Any]], *, scope: str) -> dict[str, Any]:
    return {"state":"AL","scope":scope,"status":"research-only","publishable":False,"contests":[normalize_alabama_contest(x, scope=scope) for x in rows]}
