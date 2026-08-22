import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core import RegistryError
from election_core.georgia_cd120_plan import validate_georgia_cd120_extraction


def valid_payload():
    return {
        "state":"GA", "stateFips":"13", "sourceVintage":"2026-cd120",
        "districts": {
            str(i): {
                "district": str(i),
                "members": [{"county":f"Fixture {i}","fips":f"13{i:03d}","membership":"whole","coverageRatio":1.0}],
            }
            for i in range(1,15)
        },
    }


def test_requires_all_fourteen_georgia_congressional_districts():
    result = validate_georgia_cd120_extraction(valid_payload())
    assert result["districtCount"] == 14
    assert result["publishable"] is False


def test_missing_district_fails_closed():
    payload = valid_payload()
    del payload["districts"]["14"]
    with pytest.raises(RegistryError, match="district coverage mismatch"):
        validate_georgia_cd120_extraction(payload)


def test_wrong_vintage_fails_closed():
    payload = valid_payload()
    payload["sourceVintage"] = "2025-cd119"
    with pytest.raises(RegistryError, match="2026 cd120"):
        validate_georgia_cd120_extraction(payload)


def test_non_georgia_county_fips_fails_closed():
    payload = valid_payload()
    payload["districts"]["1"]["members"][0]["fips"] = "12061"
    with pytest.raises(RegistryError, match="invalid county FIPS"):
        validate_georgia_cd120_extraction(payload)


def test_invalid_membership_fails_closed():
    payload = valid_payload()
    payload["districts"]["1"]["members"][0]["membership"] = "unknown"
    with pytest.raises(RegistryError, match="invalid membership"):
        validate_georgia_cd120_extraction(payload)
