import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from election_core.local_index import load_local_index


def test_florida_has_exactly_67_counties():
    index = load_local_index("FL")
    assert index["count"] == 67
    assert all(item["type"] == "county" for item in index["jurisdictions"])


def test_indian_river_county_identity_is_stable():
    index = load_local_index("FL")
    item = next(x for x in index["jurisdictions"] if x["name"] == "Indian River")
    assert item["id"] == "FL-12061"
    assert item["fips"] == "12061"
    assert item["slug"] == "indian-river"


def test_florida_county_fips_are_unique_and_state_scoped():
    index = load_local_index("FL")
    fips = [x["fips"] for x in index["jurisdictions"]]
    assert len(fips) == len(set(fips)) == 67
    assert all(code.startswith("12") for code in fips)


def test_known_counties_are_present():
    names = {x["name"] for x in load_local_index("FL")["jurisdictions"]}
    assert {"Brevard", "Indian River", "St. Lucie", "Miami-Dade", "Escambia", "Monroe"} <= names
