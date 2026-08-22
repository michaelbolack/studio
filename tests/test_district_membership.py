import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core import RegistryError
from election_core.district_membership import require_county_aggregate_safe, validate_district_membership
from election_core.georgia_research import load_georgia_research_counties


def valid_counties():
    return {item["name"] for item in load_georgia_research_counties()}


def test_whole_county_district_can_use_county_aggregation():
    result = validate_district_membership(
        state="GA",
        district_type="congressional",
        district=1,
        members=[
            {"county": "Chatham", "relation": "whole"},
            {"county": "Bryan", "relation": "whole"},
        ],
        valid_counties=valid_counties(),
    )
    assert result["countyAggregateSafe"] is True
    assert result["partialCount"] == 0
    require_county_aggregate_safe(result)


def test_split_county_marks_whole_county_aggregation_unsafe():
    result = validate_district_membership(
        state="GA",
        district_type="congressional",
        district=2,
        members=[
            {"county": "Fulton", "relation": "partial"},
            {"county": "Clayton", "relation": "whole"},
        ],
        valid_counties=valid_counties(),
    )
    assert result["countyAggregateSafe"] is False
    assert result["partialCounties"] == ["Fulton"]
    with pytest.raises(RegistryError, match="split counties: Fulton"):
        require_county_aggregate_safe(result)


def test_unknown_county_fails_closed():
    with pytest.raises(RegistryError, match="unknown county"):
        validate_district_membership(
            state="GA",
            district_type="congressional",
            district=3,
            members=[{"county": "Not A Georgia County", "relation": "whole"}],
            valid_counties=valid_counties(),
        )


def test_duplicate_county_fails_closed():
    with pytest.raises(RegistryError, match="duplicate county"):
        validate_district_membership(
            state="GA",
            district_type="congressional",
            district=4,
            members=[
                {"county": "Cobb", "relation": "whole"},
                {"county": "Cobb", "relation": "partial"},
            ],
            valid_counties=valid_counties(),
        )


def test_invalid_relation_fails_closed():
    with pytest.raises(RegistryError, match="whole or partial"):
        validate_district_membership(
            state="GA",
            district_type="congressional",
            district=5,
            members=[{"county": "Gwinnett", "relation": "mostly"}],
            valid_counties=valid_counties(),
        )
