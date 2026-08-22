import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core import RegistryError
from election_core.geography_extraction import build_geometry_membership, classify_intersection


def test_whole_county_is_safe_for_whole_county_aggregation():
    result = build_geometry_membership(
        state="GA", district_type="congressional", district=1, source_vintage="2026-cd120",
        intersections=[{"county":"Chatham","fips":"13051","countyArea":100.0,"intersectionArea":100.0}],
    )
    assert result["members"][0]["membership"] == "whole"
    assert result["wholeCountyAggregationSafe"] is True
    assert result["publishable"] is False


def test_partial_county_blocks_whole_county_aggregation():
    result = build_geometry_membership(
        state="GA", district_type="congressional", district=1, source_vintage="2026-cd120",
        intersections=[
            {"county":"Chatham","fips":"13051","countyArea":100.0,"intersectionArea":100.0},
            {"county":"Bryan","fips":"13029","countyArea":100.0,"intersectionArea":42.5},
        ],
    )
    assert result["containsSplitCounties"] is True
    assert result["partialCounties"] == ["Bryan"]
    assert result["wholeCountyAggregationSafe"] is False


def test_intersection_cannot_exceed_county_area():
    with pytest.raises(RegistryError, match="cannot exceed"):
        classify_intersection(county_area=100, intersection_area=101)


def test_duplicate_fips_fails_closed():
    with pytest.raises(RegistryError, match="duplicate county"):
        build_geometry_membership(
            state="GA", district_type="congressional", district=1, source_vintage="2026-cd120",
            intersections=[
                {"county":"Chatham","fips":"13051","countyArea":100,"intersectionArea":100},
                {"county":"Chatham","fips":"13051","countyArea":100,"intersectionArea":50},
            ],
        )


def test_missing_source_vintage_fails_closed():
    with pytest.raises(RegistryError, match="source vintage"):
        build_geometry_membership(
            state="GA", district_type="congressional", district=1, source_vintage="",
            intersections=[{"county":"Chatham","fips":"13051","countyArea":100,"intersectionArea":100}],
        )
