import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core import RegistryError
from election_core.adapter_factory import registered_adapter_codes
from election_core.georgia_district_research import validate_georgia_district_breakout
from election_core.registry import get_jurisdiction


def fixture():
    return {
        "contest": "Research Congressional Contest",
        "candidates": ["Candidate A", "Candidate B"],
        "counties": {
            "Fulton": [100, 80],
            "Cobb": [50, 70],
        },
        "officialTotals": [150, 150],
    }


def validate(payload=None, expected=None):
    return validate_georgia_district_breakout(
        district_type="congressional",
        district=99,
        expected_counties=expected or ["Fulton", "Cobb"],
        payload=payload or fixture(),
    )


def test_exact_district_coverage_research_validates_but_cannot_publish():
    result = validate()
    assert result["coverageComplete"] is True
    assert result["checksum"] == "passed"
    assert result["countyCoverage"] == "2/2"
    assert result["publishable"] is False
    assert get_jurisdiction("GA")["enabled"] is False
    assert "GA" not in registered_adapter_codes()


def test_missing_expected_district_county_fails_closed():
    payload = fixture()
    payload["counties"].pop("Cobb")
    with pytest.raises(RegistryError, match="district coverage mismatch"):
        validate(payload)


def test_unexpected_county_cannot_replace_expected_district_county():
    payload = fixture()
    payload["counties"].pop("Cobb")
    payload["counties"]["Gwinnett"] = [50, 70]
    with pytest.raises(RegistryError, match="district coverage mismatch"):
        validate(payload)


def test_unknown_county_cannot_enter_expected_district_definition():
    with pytest.raises(RegistryError, match="unknown counties"):
        validate(expected=["Fulton", "Not A Georgia County"])


def test_duplicate_expected_county_fails_closed():
    with pytest.raises(RegistryError, match="must be unique"):
        validate(expected=["Fulton", "Fulton"])


def test_bad_district_checksum_fails_closed():
    payload = fixture()
    payload["officialTotals"] = [151, 150]
    with pytest.raises(RegistryError, match="checksum failed"):
        validate(payload)


def test_bad_district_candidate_width_fails_closed():
    payload = fixture()
    payload["counties"]["Fulton"] = [100]
    with pytest.raises(RegistryError, match="candidate-width mismatch"):
        validate(payload)


def test_negative_district_votes_fail_closed():
    payload = fixture()
    payload["counties"]["Fulton"] = [-1, 80]
    with pytest.raises(RegistryError, match="nonnegative integer"):
        validate(payload)


def test_unsupported_district_type_fails_closed():
    with pytest.raises(RegistryError, match="unsupported"):
        validate_georgia_district_breakout(
            district_type="school-board",
            district=1,
            expected_counties=["Fulton"],
            payload={"contest": "x", "candidates": ["A"], "counties": {"Fulton": [1]}, "officialTotals": [1]},
        )
