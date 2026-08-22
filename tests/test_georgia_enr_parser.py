import sys
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from election_core.georgia_enr_parser import parse_enr_contests


def test_parses_statewide_and_district_scoped_reporting():
    text = '''## Governor - Rep
Vote for 1
Candidate
Rick Jackson
REP
52.64% 373,543
Burt Jones
REP
47.36% 336,011
Localities reporting 159/159
View results by County
## US House of Representatives - District 1 - Dem
Vote for 1
Candidate
Joyce Marie Griggs
DEM
47.04% 11,206
Amanda Hollowell
DEM
52.96% 12,618
Localities reporting 15/15
View results by County
## State Senate - District 46 - Rep
Vote for 1
Candidate
Doug McKillip
REP
35.45% 6,637
Marc McMain
REP
64.55% 12,084
Localities reporting 5/5
'''
    result = parse_enr_contests(text)
    assert result["statewide"][0]["reporting"] == {"reported":159,"total":159}
    assert result["congressional"][0]["district"] == "1"
    assert result["congressional"][0]["reporting"]["total"] == 15
    assert result["legislative"][0]["district"] == "46"
    assert result["legislative"][0]["candidates"][1]["votes"] == 12084


def test_no_contests_fails_closed():
    with pytest.raises(ValueError, match="no Georgia ENR contests"):
        parse_enr_contests("Georgia Election Night Reporting")
