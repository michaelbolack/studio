import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from election_core import DistrictScope, build_district_race, checksum_geographies, make_race_id


def test_complete_geographies_and_checksum_are_publishable():
    result = checksum_geographies(
        {"Alpha": [10, 20], "Beta": [5, 15]},
        [15, 35],
        expected_geographies=["Alpha", "Beta"],
    )
    assert result.coverage_complete is True
    assert result.checksum_passed is True
    assert result.publishable is True


def test_missing_geography_fails_closed_even_when_numbers_match_partial_sum():
    result = checksum_geographies(
        {"Alpha": [10, 20]},
        [10, 20],
        expected_geographies=["Alpha", "Beta"],
    )
    assert result.coverage_complete is False
    assert result.publishable is False


def test_unexpected_geography_does_not_substitute_for_expected_geography():
    result = checksum_geographies(
        {"Alpha": [10, 20], "Gamma": [5, 15]},
        [15, 35],
        expected_geographies=["Alpha", "Beta"],
    )
    assert result.coverage_complete is False
    assert result.checksum_passed is True
    assert result.publishable is False


def test_bad_checksum_fails_closed():
    result = checksum_geographies(
        {"Alpha": [10, 20], "Beta": [5, 15]},
        [16, 34],
        expected_geographies=["Alpha", "Beta"],
    )
    assert result.coverage_complete is True
    assert result.checksum_passed is False
    assert result.publishable is False


def test_candidate_width_mismatch_is_rejected():
    with pytest.raises(ValueError):
        checksum_geographies({"Alpha": [10]}, [10, 20])


def test_negative_votes_are_rejected():
    with pytest.raises(ValueError):
        checksum_geographies({"Alpha": [10, -1]}, [10, -1])


def test_district_scope_is_state_agnostic():
    scope = DistrictScope("ga", "state-senate-district", "12")
    assert scope.as_json() == {
        "type": "state-senate-district",
        "state": "GA",
        "district": "12",
    }


def test_invalid_district_type_is_rejected():
    with pytest.raises(ValueError):
        DistrictScope("FL", "florida-special-district", "9")


def test_race_id_is_stable_and_not_florida_specific():
    scope = DistrictScope("TX", "congressional-district", "7")
    assert make_race_id("TX", "US House", scope, "REP", "2026-primary") == (
        "TX-US-HOUSE-CONGRESSIONAL-DISTRICT-7-REP-2026-PRIMARY"
    )


def test_district_builder_refuses_incomplete_coverage():
    with pytest.raises(RuntimeError, match="withheld"):
        build_district_race(
            state="FL",
            district_type="state-house-district",
            district="34",
            office="State Representative",
            party="REP",
            election_key="2026-primary",
            candidate_names=["Candidate A", "Candidate B"],
            geography_votes={"Indian River": [100, 80]},
            official_totals=[100, 80],
            source_authority="Official source",
            source_url="https://example.invalid/results",
            expected_geographies=["Indian River", "Osceola"],
        )


def test_district_builder_calculates_percentages_after_validation():
    race = build_district_race(
        state="PR",
        district_type="other-district",
        district="1",
        office="Example Office",
        party=None,
        election_key="2028-general",
        candidate_names=["Candidate A", "Candidate B"],
        geography_votes={"Area One": [60, 40]},
        official_totals=[60, 40],
        source_authority="Official source",
        source_url="https://example.invalid/results",
        expected_geographies=["Area One"],
    )
    assert race["scope"]["state"] == "PR"
    assert race["candidates"][0]["percent"] == 60.0
    assert race["validation"]["checksum"] == "passed"
