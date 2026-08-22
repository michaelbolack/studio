"""Research-only district coverage manifests for disabled state onboarding.

Production district coverage continues to require an enabled jurisdiction. This
loader exists only so a disabled onboarding state can build and test district
geography manifests before activation. It never makes results publishable.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .local import LocalJurisdiction, index_local_jurisdictions
from .registry import RegistryError, get_jurisdiction

VALID_DISTRICT_TYPES = {"congressional", "state-senate", "state-house"}


def load_research_local_names(state: str, local_index_path: Path | str) -> set[str]:
    code = state.strip().upper()
    jurisdiction = get_jurisdiction(code)
    if jurisdiction.get("enabled"):
        raise RegistryError(f"research district coverage is only for disabled jurisdictions: {code}")
    payload = json.loads(Path(local_index_path).read_text())
    if payload.get("state") != code:
        raise RegistryError(f"research local index state mismatch: expected {code}")
    raw = payload.get("jurisdictions")
    if not isinstance(raw, list) or not raw:
        raise RegistryError(f"research local index is empty: {code}")
    items = [
        LocalJurisdiction(
            code,
            item["name"],
            item.get("type", jurisdiction.get("localJurisdictionType", "county")),
            item.get("fips"),
            item.get("slug"),
        )
        for item in raw
    ]
    return {item["name"] for item in index_local_jurisdictions(items).values()}


def load_research_district_coverage(
    *,
    state: str,
    district_type: str,
    manifest_path: Path | str,
    local_index_path: Path | str,
) -> dict[str, Any]:
    """Validate one disabled state's research district coverage manifest.

    Manifest shape:
      {"schemaVersion": 1, "state": "GA", "districtType": "congressional",
       "status": "research-only", "districts": {"1": ["County", ...]}}
    """
    code = state.strip().upper()
    jurisdiction = get_jurisdiction(code)
    if jurisdiction.get("enabled"):
        raise RegistryError(f"research district coverage is only for disabled jurisdictions: {code}")
    if district_type not in VALID_DISTRICT_TYPES:
        raise RegistryError(f"unsupported research district type: {district_type}")

    payload = json.loads(Path(manifest_path).read_text())
    if payload.get("state") != code:
        raise RegistryError(f"research district coverage state mismatch: expected {code}")
    if payload.get("districtType") != district_type:
        raise RegistryError(f"research district coverage type mismatch: expected {district_type}")
    if payload.get("status") != "research-only":
        raise RegistryError("research district coverage manifest must remain research-only")

    districts = payload.get("districts")
    if not isinstance(districts, dict) or not districts:
        raise RegistryError("research district coverage manifest has no districts")

    valid_names = load_research_local_names(code, local_index_path)
    normalized: dict[str, list[str]] = {}
    for district, geographies in districts.items():
        key = str(district).strip()
        if not key:
            raise RegistryError("research district identifier cannot be empty")
        if not isinstance(geographies, list) or not geographies:
            raise RegistryError(f"research district has no geographies: {key}")
        if any(not isinstance(name, str) or not name.strip() for name in geographies):
            raise RegistryError(f"research district contains invalid geography: {key}")
        cleaned = [name.strip() for name in geographies]
        if len(set(cleaned)) != len(cleaned):
            raise RegistryError(f"research district contains duplicate geographies: {key}")
        unknown = sorted(set(cleaned) - valid_names)
        if unknown:
            raise RegistryError(
                f"research district contains unknown geographies: {key}: " + ", ".join(unknown)
            )
        normalized[key] = cleaned

    return {
        "schemaVersion": 1,
        "state": code,
        "districtType": district_type,
        "status": "research-only",
        "publishable": False,
        "districtCount": len(normalized),
        "districts": normalized,
    }
