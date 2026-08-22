"""Load authoritative district-to-local-jurisdiction coverage manifests.

A district collector must not claim complete geographic coverage unless an explicit
coverage manifest exists for that state, district type, election cycle and district.
"""
from __future__ import annotations
import json
from pathlib import Path
from .registry import RegistryError, get_jurisdiction

DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "data" / "jurisdictions"
VALID_DISTRICT_TYPES = {"congressional", "state-senate", "state-house"}


def coverage_path(state: str, district_type: str, election_key: str, root: Path | str = DEFAULT_ROOT) -> Path:
    code = state.strip().upper()
    get_jurisdiction(code, require_enabled=True)
    kind = district_type.strip().lower()
    if kind not in VALID_DISTRICT_TYPES:
        raise RegistryError(f"unsupported district coverage type: {kind}")
    key = election_key.strip().lower()
    if not key or "/" in key or ".." in key:
        raise RegistryError("unsafe election key")
    return Path(root) / code.lower() / "districts" / key / f"{kind}.json"


def load_district_coverage(state: str, district_type: str, election_key: str, district: str | int, root: Path | str = DEFAULT_ROOT) -> list[str]:
    code = state.strip().upper()
    path = coverage_path(code, district_type, election_key, root)
    if not path.exists():
        raise RegistryError(f"district coverage manifest is not configured: {code} {district_type} {election_key}")
    payload = json.loads(path.read_text())
    if payload.get("state") != code:
        raise RegistryError(f"district coverage state mismatch: {code}")
    if payload.get("districtType") != district_type.strip().lower():
        raise RegistryError(f"district coverage type mismatch: {district_type}")
    if payload.get("electionKey") != election_key.strip().lower():
        raise RegistryError(f"district coverage election mismatch: {election_key}")
    entry = payload.get("districts", {}).get(str(district))
    if not entry:
        raise RegistryError(f"district coverage is not configured: {code} {district_type} {district}")
    jurisdictions = entry.get("jurisdictions")
    if not isinstance(jurisdictions, list) or not jurisdictions or len(jurisdictions) != len(set(jurisdictions)):
        raise RegistryError(f"invalid district jurisdiction coverage: {code} {district_type} {district}")
    return jurisdictions
