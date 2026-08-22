import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from election_core.local import LocalJurisdiction, index_local_jurisdictions


def test_florida_county():
    item = LocalJurisdiction("FL", "Indian River", "county", "12061")
    assert item.id == "FL-12061"
    assert item.as_json()["slug"] == "indian-river"


def test_louisiana_parish():
    item = LocalJurisdiction("LA", "Orleans", "parish", "22071")
    assert item.as_json()["type"] == "parish"


def test_alaska_borough_and_census_area_are_supported():
    assert LocalJurisdiction("AK", "Anchorage", "borough", "02020").local_type == "borough"
    assert LocalJurisdiction("AK", "Bethel", "census-area", "02050").local_type == "census-area"


def test_virginia_independent_city_is_supported():
    item = LocalJurisdiction("VA", "Richmond", "independent-city", "51760")
    assert item.as_json()["type"] == "independent-city"


def test_dc_ward_can_exist_without_county_fips():
    item = LocalJurisdiction("DC", "Ward 1", "ward")
    assert item.id == "DC-ward-1"


def test_duplicate_fips_is_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        index_local_jurisdictions([
            LocalJurisdiction("FL", "Alpha", "county", "12001"),
            LocalJurisdiction("FL", "Beta", "county", "12001"),
        ])


def test_invalid_fips_is_rejected():
    with pytest.raises(ValueError, match="five digits"):
        LocalJurisdiction("FL", "Indian River", "county", "061")
