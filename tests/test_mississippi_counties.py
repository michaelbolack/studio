import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.mississippi_counties import MISSISSIPPI_COUNTIES,validate_mississippi_counties

def test_mississippi_has_exactly_82_counties():
    assert validate_mississippi_counties() is True
    assert len(MISSISSIPPI_COUNTIES)==82

def test_known_county_fips_are_stable():
    assert MISSISSIPPI_COUNTIES["28033"]=="DeSoto"
    assert MISSISSIPPI_COUNTIES["28049"]=="Hinds"
    assert MISSISSIPPI_COUNTIES["28047"]=="Harrison"

def test_all_fips_are_unique_mississippi_codes():
    assert len(set(MISSISSIPPI_COUNTIES))==82
    assert all(x.startswith("28") and len(x)==5 for x in MISSISSIPPI_COUNTIES)
