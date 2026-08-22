#!/usr/bin/env python3
"""State-agnostic district/result primitives for the Election Center.

No state names, county counts, election vendors, or source URLs belong here.
Adapters translate official source data into these structures.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping, Sequence

VALID_DISTRICT_TYPES = {
    "congressional-district",
    "state-senate-district",
    "state-house-district",
    "county-commission-district",
    "school-board-district",
    "municipal-district",
    "other-district",
}


@dataclass(frozen=True)
class DistrictScope:
    state: str
    district_type: str
    district: str

    def __post_init__(self) -> None:
        state = self.state.strip().upper()
        if len(state) != 2:
            raise ValueError("state must be a two-character postal code")
        if self.district_type not in VALID_DISTRICT_TYPES:
            raise ValueError(f"unsupported district type: {self.district_type}")
        if not str(self.district).strip():
            raise ValueError("district identifier is required")
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "district", str(self.district).strip())

    def as_json(self) -> dict:
        return {
            "type": self.district_type,
            "state": self.state,
            "district": self.district,
        }


@dataclass(frozen=True)
class ValidationResult:
    coverage_complete: bool
    checksum_passed: bool
    geography_count: int
    calculated_totals: tuple[int, ...]
    official_totals: tuple[int, ...]

    @property
    def publishable(self) -> bool:
        return self.coverage_complete and self.checksum_passed

    def as_json(self) -> dict:
        return {
            "coverageComplete": self.coverage_complete,
            "checksum": "passed" if self.checksum_passed else "failed",
            "geographiesIncluded": self.geography_count,
            "calculatedTotals": list(self.calculated_totals),
            "officialTotals": list(self.official_totals),
        }


def checksum_geographies(
    geography_votes: Mapping[str, Sequence[int]],
    official_totals: Sequence[int],
    *,
    expected_geographies: Sequence[str] | None = None,
) -> ValidationResult:
    """Validate component geography totals against an authoritative aggregate.

    When expected_geographies is supplied, every expected geography must be present
    and no unexpected geography may silently substitute for it. This is the core
    fail-closed rule used by state adapters.
    """
    if not geography_votes:
        raise ValueError("no component geography results supplied")
    official = tuple(int(v) for v in official_totals)
    if not official:
        raise ValueError("authoritative aggregate totals are required")

    width = len(official)
    normalized = {str(k): tuple(int(v) for v in values) for k, values in geography_votes.items()}
    for geography, values in normalized.items():
        if len(values) != width:
            raise ValueError(f"candidate-width mismatch for {geography}")
        if any(v < 0 for v in values):
            raise ValueError(f"negative vote total for {geography}")

    coverage_complete = True
    if expected_geographies is not None:
        expected = {str(x) for x in expected_geographies}
        actual = set(normalized)
        coverage_complete = actual == expected

    calculated = tuple(sum(values[i] for values in normalized.values()) for i in range(width))
    return ValidationResult(
        coverage_complete=coverage_complete,
        checksum_passed=calculated == official,
        geography_count=len(normalized),
        calculated_totals=calculated,
        official_totals=official,
    )


def make_race_id(state: str, office: str, scope: DistrictScope | None, party: str | None, election_key: str) -> str:
    """Build stable IDs without encoding any particular state's election system."""
    parts = [state.upper(), office]
    if scope is not None:
        parts.extend([scope.district_type, scope.district])
    if party:
        parts.append(party.upper())
    parts.append(election_key)
    cleaned = [re.sub(r"[^A-Z0-9]+", "-", str(p).upper()).strip("-") for p in parts]
    return "-".join(p for p in cleaned if p)
