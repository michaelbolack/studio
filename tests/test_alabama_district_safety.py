import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.alabama_district_safety import validate_alabama_district_source

MEMBERS=[{"fips":"01073","membership":"whole"},{"fips":"01117","membership":"partial"}]


def test_split_district_accepts_official_district_results():
    r=validate_alabama_district_source(district_type="congressional",district=6,members=MEMBERS,result_source="official-district")
    assert r["safe"] is True and r["publishable"] is False


def test_split_district_accepts_official_precinct_results():
    r=validate_alabama_district_source(district_type="state_house",district=1,members=MEMBERS,result_source="official-precinct")
    assert r["safe"] is True


def test_split_district_rejects_whole_county_aggregation():
    with pytest.raises(ValueError,match="split Alabama district"):
        validate_alabama_district_source(district_type="congressional",district=6,members=MEMBERS,result_source="whole-county")


def test_all_whole_members_can_use_whole_county_source():
    r=validate_alabama_district_source(district_type="state_senate",district=1,members=[{"fips":"01001","membership":"whole"}],result_source="whole-county")
    assert r["safe"] is True


def test_duplicate_and_foreign_fips_fail_closed():
    with pytest.raises(ValueError):
        validate_alabama_district_source(district_type="congressional",district=1,members=[{"fips":"12061","membership":"whole"}],result_source="official-district")
