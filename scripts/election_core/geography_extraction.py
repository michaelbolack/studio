"""Geometry-derived district membership normalization for state onboarding.

This module does not download or publish election data. It accepts intersection
measurements produced from authoritative boundary geometry and converts them into
fail-closed whole/partial county membership records.
"""
from __future__ import annotations
from typing import Any
from .registry import RegistryError


def classify_intersection(*, county_area: float, intersection_area: float, tolerance: float = 1e-6) -> str:
    if county_area <= 0 or intersection_area <= 0:
        raise RegistryError("district geography areas must be positive")
    if intersection_area > county_area * (1 + tolerance):
        raise RegistryError("district intersection cannot exceed county area")
    ratio = intersection_area / county_area
    return "whole" if ratio >= 1 - tolerance else "partial"


def build_geometry_membership(
    *, state: str,
    district_type: str,
    district: str | int,
    intersections: list[dict[str, Any]],
    source_vintage: str,
) -> dict[str, Any]:
    if not source_vintage.strip():
        raise RegistryError("authoritative geography source vintage is required")
    if not intersections:
        raise RegistryError("district has no geometry intersections")

    seen: set[str] = set()
    members = []
    for row in intersections:
        county = str(row.get("county", "")).strip()
        fips = str(row.get("fips", "")).strip()
        if not county or len(fips) != 5 or not fips.isdigit():
            raise RegistryError("district intersection requires county name and five-digit FIPS")
        if fips in seen:
            raise RegistryError(f"duplicate county intersection: {fips}")
        seen.add(fips)
        county_area = float(row.get("countyArea", 0))
        intersection_area = float(row.get("intersectionArea", 0))
        membership = classify_intersection(county_area=county_area, intersection_area=intersection_area)
        members.append({
            "county": county,
            "fips": fips,
            "membership": membership,
            "coverageRatio": intersection_area / county_area,
        })

    partial = [x["county"] for x in members if x["membership"] == "partial"]
    return {
        "state": state.strip().upper(),
        "districtType": district_type,
        "district": str(district).strip(),
        "sourceVintage": source_vintage.strip(),
        "status": "research-only",
        "publishable": False,
        "members": members,
        "containsSplitCounties": bool(partial),
        "partialCounties": partial,
        "wholeCountyAggregationSafe": not partial,
    }
