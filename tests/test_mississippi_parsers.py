import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.mississippi_parsers import parse_certified_rows,parse_provisional_county_rows

ROWS=[{"scope":"congressional","title":"US House District 1","district":"1","complete":True,"candidates":[{"name":"A","votes":10},{"name":"B","votes":8}]}]

def test_certified_parser_pins_secretary_of_state_provenance():
    r=parse_certified_rows(ROWS)[0]
    assert r["sourceTier"]=="certified-state"
    assert r["sourceAuthority"]=="Mississippi Secretary of State"

def test_provisional_parser_pins_county_identity_and_provenance():
    r=parse_provisional_county_rows(ROWS,county_name="Hinds",county_fips="28049")[0]
    assert r["sourceTier"]=="provisional-county"
    assert r["jurisdictionId"]=="MS-28049"
    assert "Hinds County" in r["sourceAuthority"]

def test_bad_scope_or_county_identity_fails_closed():
    bad=[dict(ROWS[0],scope="unknown")]
    with pytest.raises(ValueError): parse_certified_rows(bad)
    with pytest.raises(ValueError): parse_provisional_county_rows(ROWS,county_name="Hinds",county_fips="12061")
