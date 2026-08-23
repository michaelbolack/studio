import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.alabama_parser import parse_alabama_county_text

PAGE='''2026 PRIMARY RUNOFF ELECTION Shelby County Results
Total Ballots Cast: 20,697 Total Registered Voters: 181,088 Voter Turnout: 11.43% Boxes Reported: 100.00% Last Updated: 06/16/2026 09:51:43 PM
LIEUTENANT GOVERNOR (REP)
Percent Votes
Wes Allen (REP) Image: progressBar 44.51% 8,042
John Wahl (REP) Image: progressBar 55.49% 10,025
18,067
DISTRICT COURT JUDGE, SHELBY COUNTY, PLACE NO. 3
Percent Votes
Ben Fuller (REP) Image: progressBar 52.19% 9,167
Jarred "Jay" Welborn (REP) Image: progressBar 47.81% 8,398
17,565'''

CD='''SPECIAL PRIMARY ELECTION - CONGRESSIONAL DISTRICTS 1, 2, 6 AND 7 Jefferson County Results
Total Ballots Cast: 16,983 Total Registered Voters: 493,436 Voter Turnout: 3.44% Boxes Reported: 100.00% Last Updated: 08/11/2026 10:37:35 PM
UNITED STATES REPRESENTATIVE, 6TH CONGRESSIONAL DISTRICT (REP)
Percent Votes
Case Dixon (REP) Image: progressBar 11.78% 1,150
Gary Palmer (REP) Image: progressBar 88.22% 8,611
9,761'''

def test_parses_real_alabamavotes_county_shape():
    r=parse_alabama_county_text(PAGE)
    assert r["complete"] is True
    assert r["contests"][0]["candidates"][1]["votes"]==10025
    assert r["contests"][1]["scope"]=="local"

def test_parses_congressional_district_id():
    r=parse_alabama_county_text(CD)
    c=r["contests"][0]
    assert c["scope"]=="congressional" and c["district"]=="6"

def test_incomplete_boxes_are_preserved():
    r=parse_alabama_county_text(PAGE.replace("100.00%","75.00%",1))
    assert r["complete"] is False and r["boxesReportedPercent"]==75.0

def test_missing_reporting_fails_closed():
    with pytest.raises(ValueError,match="Boxes Reported"):
        parse_alabama_county_text("LIEUTENANT GOVERNOR (REP)\nA (REP) 50.00% 1")
