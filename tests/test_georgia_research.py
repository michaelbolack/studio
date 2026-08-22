import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core import RegistryError
from election_core.georgia_research import load_georgia_research_counties, validate_georgia_county_breakout
from election_core.registry import get_jurisdiction
from election_core.adapter_factory import registered_adapter_codes


def complete_fixture():
    counties = load_georgia_research_counties()
    votes = {item["name"]: [0, 0] for item in counties}
    votes["Fulton"] = [100, 80]
    votes["Cobb"] = [50, 70]
    return {
        "contest": "Research Contest",
        "candidates": ["Candidate A", "Candidate B"],
        "counties": votes,
        "officialTotals": [150, 150],
    }


def test_georgia_research_index_has_159_counties_while_state_stays_disabled():
    counties = load_georgia_research_counties()
    assert len(counties) == 159
    assert get_jurisdiction("GA")["enabled"] is False
    assert "GA" not in registered_adapter_codes()


def test_complete_county_breakout_can_be_research_validated_but_not_published():
    result = validate_georgia_county_breakout(complete_fixture())
    assert result["coverageComplete"] is True
    assert result["checksum"] == "passed"
    assert result["countyCoverage"] == "159/159"
    assert result["publishable"] is False


def test_missing_county_fails_closed():
    payload = complete_fixture()
    payload["counties"].pop("Fulton")
    with pytest.raises(RegistryError, match="county coverage mismatch"):
        validate_georgia_county_breakout(payload)


def test_unexpected_county_cannot_replace_missing_county():
    payload = complete_fixture()
    payload["counties"].pop("Fulton")
    payload["counties"]["Not A Georgia County"] = [100, 80]
    with pytest.raises(RegistryError, match="county coverage mismatch"):
        validate_georgia_county_breakout(payload)


def test_bad_official_checksum_fails_closed():
    payload = complete_fixture()
    payload["officialTotals"] = [151, 150]
    with pytest.raises(RegistryError, match="checksum failed"):
        validate_georgia_county_breakout(payload)


def test_negative_votes_fail_closed():
    payload = complete_fixture()
    payload["counties"]["Fulton"] = [-1, 80]
    with pytest.raises(RegistryError, match="nonnegative integer"):
        validate_georgia_county_breakout(payload)


def test_candidate_width_mismatch_fails_closed():
    payload = complete_fixture()
    payload["counties"]["Fulton"] = [100]
    with pytest.raises(RegistryError, match="candidate-width mismatch"):
        validate_georgia_county_breakout(payload)
