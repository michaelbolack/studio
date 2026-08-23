import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from election_core.alabama_counties import ALABAMA_COUNTIES, validate_alabama_counties


def test_alabama_has_exactly_67_counties():
    assert validate_alabama_counties() is True
    assert len(ALABAMA_COUNTIES) == 67


def test_known_alabama_counties_have_stable_fips():
    assert ALABAMA_COUNTIES["01073"] == "Jefferson"
    assert ALABAMA_COUNTIES["01097"] == "Mobile"
    assert ALABAMA_COUNTIES["01125"] == "Tuscaloosa"


def test_all_alabama_fips_are_unique_state_01_codes():
    assert len(set(ALABAMA_COUNTIES)) == 67
    assert all(code.startswith("01") and len(code) == 5 for code in ALABAMA_COUNTIES)
