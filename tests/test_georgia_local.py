import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from election_core.georgia_local import normalize_georgia_county, validate_georgia_local_collection


def race(reported=10, total=10):
    return {"title":"County Commission District 1","reporting":{"reported":reported,"total":total},"candidates":[{"name":"A","votes":20},{"name":"B","votes":10}]}


def test_county_gets_stable_georgia_jurisdiction_id():
    result = normalize_georgia_county("Fulton", "13121", [race()])
    assert result["jurisdictionId"] == "GA-13121"
    assert result["contests"][0]["leader"] == "A"
    assert result["publishable"] is False


def test_incomplete_precinct_reporting_withholds_local_leader():
    result = normalize_georgia_county("Fulton", "13121", [race(9, 10)])
    assert result["contests"][0]["leader"] is None


def test_non_georgia_fips_is_rejected():
    with pytest.raises(ValueError):
        normalize_georgia_county("Wrong", "12061", [race()])


def test_local_collection_requires_exact_expected_counties():
    counties = [{"fips":"13121"}, {"fips":"13051"}]
    ok = validate_georgia_local_collection(counties, {"13121", "13051"})
    assert ok["complete"] is True
    bad = validate_georgia_local_collection(counties, {"13121", "13051", "13029"})
    assert bad["complete"] is False
    assert bad["missing"] == ["13029"]


def test_duplicate_county_payload_fails_closed():
    with pytest.raises(ValueError, match="duplicate"):
        validate_georgia_local_collection([{"fips":"13121"},{"fips":"13121"}], {"13121"})
