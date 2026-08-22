"""Reusable helpers for state-specific district adapters.

Source-specific collectors are responsible for discovery/parsing. These helpers
normalize a parsed contest and enforce fail-closed validation before publication.
"""
from __future__ import annotations
from typing import Mapping, Sequence
from .districts import DistrictScope, checksum_geographies, make_race_id


def build_district_race(*, state: str, district_type: str, district: str, office: str,
                        party: str | None, election_key: str, candidate_names: Sequence[str],
                        geography_votes: Mapping[str, Sequence[int]], official_totals: Sequence[int],
                        source_authority: str, source_url: str,
                        expected_geographies: Sequence[str] | None = None) -> dict:
    if not candidate_names:
        raise ValueError("candidate names are required")
    if len(candidate_names) != len(official_totals):
        raise ValueError("candidate names do not match authoritative totals")
    scope = DistrictScope(state, district_type, str(district))
    validation = checksum_geographies(
        geography_votes,
        official_totals,
        expected_geographies=expected_geographies,
    )
    if not validation.publishable:
        raise RuntimeError(
            f"withheld {state} {office} {district}: coverageComplete="
            f"{validation.coverage_complete}, checksum={validation.checksum_passed}"
        )
    total = sum(validation.official_totals)
    candidates = [
        {
            "name": name,
            "party": party,
            "votes": votes,
            "percent": round((votes / total * 100) if total else 0, 2),
        }
        for name, votes in zip(candidate_names, validation.official_totals)
    ]
    return {
        "id": make_race_id(state, office, scope, party, election_key),
        "office": office,
        "district": str(district),
        "party": party,
        "scope": scope.as_json(),
        "candidates": candidates,
        "geographyNames": list(geography_votes),
        "geographiesIncluded": len(geography_votes),
        "source": {"authority": source_authority, "url": source_url},
        "validation": validation.as_json(),
    }
