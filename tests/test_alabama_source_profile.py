import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from election_core.alabama_source_profile import ALABAMA_SOURCE_PROFILE
from election_core.adapter_factory import registered_adapter_codes


def test_alabama_starts_disabled_with_67_counties():
    p = ALABAMA_SOURCE_PROFILE
    assert p["state"] == "AL"
    assert p["enabled"] is False
    assert p["status"] == "research-only"
    assert p["expectedLocalJurisdictions"] == 67
    assert p["localJurisdictionType"] == "county"


def test_alabama_pins_official_https_sources_and_fail_closed_policy():
    p = ALABAMA_SOURCE_PROFILE
    assert p["electionNight"]["scheme"] == "https"
    assert p["electionNight"]["host"] == "www2.alabamavotes.gov"
    assert p["officialData"]["precinctResultsAvailable"] is True
    assert p["sourcePolicy"]["publishIncompleteAggregateLeaders"] is False
    assert p["sourcePolicy"]["requireExactCoverageBeforeComplete"] is True


def test_source_profile_does_not_register_alabama_adapter():
    assert "AL" not in registered_adapter_codes()
