import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core import RegistryError
from election_core.georgia_district_research import validate_georgia_district_from_membership


def payload():
    return {
        "contest": "Research District Contest",
        "candidates": ["Candidate A", "Candidate B"],
        "counties": {
            "Chatham": [100, 80],
            "Bryan": [50, 70],
        },
        "officialTotals": [150, 150],
    }


def test_whole_county_membership_can_reach_checksum_validator():
    result = validate_georgia_district_from_membership(
        district_type="congressional",
        district=1,
        members=[
            {"county": "Chatham", "relation": "whole"},
            {"county": "Bryan", "relation": "whole"},
        ],
        payload=payload(),
    )
    assert result["checksum"] == "passed"
    assert result["membership"]["countyAggregateSafe"] is True
    assert result["publishable"] is False


def test_partial_county_blocks_whole_county_vote_aggregation_before_checksum():
    with pytest.raises(RegistryError, match="cannot be aggregated from whole-county totals"):
        validate_georgia_district_from_membership(
            district_type="congressional",
            district=1,
            members=[
                {"county": "Chatham", "relation": "partial"},
                {"county": "Bryan", "relation": "whole"},
            ],
            payload=payload(),
        )
