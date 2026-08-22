import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core import RegistryError
from election_core.district_geography_readiness import assess_district_geography_readiness


def test_current_geometry_can_start_research_without_relationship_file():
    result = assess_district_geography_readiness(
        state="GA", district_type="congressional", vintage="2026-cd120",
        method="geometry-intersection", source_available=True, membership_resolved=False,
    )
    assert result["status"] == "research-ready-membership-unresolved"
    assert result["publishable"] is False


def test_resolved_research_still_cannot_publish_disabled_state():
    result = assess_district_geography_readiness(
        state="GA", district_type="congressional", vintage="2026-cd120",
        method="geometry-intersection", source_available=True, membership_resolved=True,
    )
    assert result["status"] == "research-validated"
    assert result["publishable"] is False


def test_missing_source_blocks_research():
    result = assess_district_geography_readiness(
        state="GA", district_type="congressional", vintage="2026-cd120",
        method="geometry-intersection", source_available=False, membership_resolved=False,
    )
    assert result["status"] == "blocked-source-unavailable"


def test_unknown_method_fails_closed():
    with pytest.raises(RegistryError, match="unsupported geography method"):
        assess_district_geography_readiness(
            state="GA", district_type="congressional", vintage="2026-cd120",
            method="guess", source_available=True, membership_resolved=False,
        )
