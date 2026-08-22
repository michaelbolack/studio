"""Pinned research plan for Georgia 120th Congressional District geography.

Georgia did not redraw congressional boundaries for the 2026 cycle, but this plan
still requires the authoritative 2026 Census TIGER/Line cd120 vintage. It describes
the inputs and invariants an offline GIS extraction job must satisfy before its
output can become a research coverage manifest.
"""
from __future__ import annotations
from typing import Any
from .registry import RegistryError, get_jurisdiction

EXPECTED_DISTRICTS = {str(i) for i in range(1, 15)}
EXPECTED_STATE_FIPS = "13"
EXPECTED_VINTAGE = "2026-cd120"


def validate_georgia_cd120_extraction(payload: dict[str, Any]) -> dict[str, Any]:
    if get_jurisdiction("GA").get("enabled"):
        raise RegistryError("Georgia cd120 extraction validator is research-only")
    if not isinstance(payload, dict):
        raise RegistryError("Georgia cd120 extraction payload must be an object")
    if payload.get("state") != "GA" or payload.get("stateFips") != EXPECTED_STATE_FIPS:
        raise RegistryError("Georgia cd120 extraction state identity mismatch")
    if payload.get("sourceVintage") != EXPECTED_VINTAGE:
        raise RegistryError("Georgia cd120 extraction must use 2026 cd120 geography")

    districts = payload.get("districts")
    if not isinstance(districts, dict):
        raise RegistryError("Georgia cd120 extraction districts are required")
    actual = set(districts)
    if actual != EXPECTED_DISTRICTS:
        raise RegistryError(
            f"Georgia cd120 district coverage mismatch: missing={sorted(EXPECTED_DISTRICTS-actual)}; "
            f"unexpected={sorted(actual-EXPECTED_DISTRICTS)}"
        )

    for district, record in districts.items():
        if not isinstance(record, dict):
            raise RegistryError(f"Georgia cd120 district record must be an object: {district}")
        if record.get("district") != district:
            raise RegistryError(f"Georgia cd120 district identifier mismatch: {district}")
        members = record.get("members")
        if not isinstance(members, list) or not members:
            raise RegistryError(f"Georgia cd120 district has no county intersections: {district}")
        for member in members:
            fips = str(member.get("fips", ""))
            if len(fips) != 5 or not fips.startswith(EXPECTED_STATE_FIPS):
                raise RegistryError(f"Georgia cd120 member has invalid county FIPS: {district}")
            if member.get("membership") not in {"whole", "partial"}:
                raise RegistryError(f"Georgia cd120 member has invalid membership: {district}")
            ratio = member.get("coverageRatio")
            if not isinstance(ratio, (int, float)) or isinstance(ratio, bool) or not (0 < ratio <= 1.000001):
                raise RegistryError(f"Georgia cd120 member has invalid coverage ratio: {district}")

    return {
        "state": "GA",
        "stateFips": EXPECTED_STATE_FIPS,
        "sourceVintage": EXPECTED_VINTAGE,
        "districtCount": 14,
        "status": "research-validated",
        "publishable": False,
        "districts": districts,
    }
