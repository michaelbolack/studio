import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core.local import LocalJurisdiction, index_local_jurisdictions
from election_core.local_index import load_local_index
from election_core.registry import RegistryError, get_jurisdiction

GA_INDEX = ROOT / "data" / "jurisdictions" / "ga" / "local.json"


def _raw_index():
    return json.loads(GA_INDEX.read_text())


def test_georgia_research_index_has_all_159_counties():
    data = _raw_index()
    assert data["state"] == "GA"
    assert len(data["jurisdictions"]) == 159
    assert all(item["type"] == "county" for item in data["jurisdictions"])


def test_georgia_county_fips_are_unique_and_state_scoped():
    data = _raw_index()
    fips = [item["fips"] for item in data["jurisdictions"]]
    assert len(fips) == len(set(fips)) == 159
    assert all(len(code) == 5 and code.startswith("13") and code.isdigit() for code in fips)


def test_georgia_index_uses_common_local_identity_contract():
    data = _raw_index()
    items = [
        LocalJurisdiction("GA", item["name"], item["type"], item["fips"])
        for item in data["jurisdictions"]
    ]
    indexed = index_local_jurisdictions(items)
    assert indexed["GA-13001"]["name"] == "Appling"
    assert indexed["GA-13121"]["name"] == "Fulton"
    assert indexed["GA-13215"]["name"] == "Muscogee"
    assert indexed["GA-13321"]["name"] == "Worth"


def test_georgia_index_does_not_enable_georgia():
    assert get_jurisdiction("GA")["enabled"] is False
    with pytest.raises(RegistryError, match="not enabled"):
        load_local_index("GA")
