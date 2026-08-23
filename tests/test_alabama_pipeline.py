import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.alabama_transport import AlabamaVotesTransport
from election_core.alabama_pipeline import normalize_transport

PAGE="""Boxes Reported: 100.00%
GOVERNOR - REPUBLICAN
Candidate A (REP) 55.00% 550
Candidate B (REP) 45.00% 450
UNITED STATES REPRESENTATIVE CONGRESSIONAL DISTRICT 1 - REPUBLICAN
Candidate C (REP) 60.00% 600
Candidate D (REP) 40.00% 400
STATE SENATE DISTRICT 2 - DEMOCRATIC
Candidate E (DEM) 52.00% 520
Candidate F (DEM) 48.00% 480
SHERIFF - REPUBLICAN
Candidate G (REP) 51.00% 510
Candidate H (REP) 49.00% 490
"""

def test_full_pipeline_groups_all_four_scopes():
    t=AlabamaVotesTransport("https://www2.alabamavotes.gov/results",lambda u:PAGE)
    out=normalize_transport(t)
    assert set(out)=={"statewide","congressional","legislative","local"}
    assert out["statewide"]["contests"][0]["leader"]=="Candidate A"
    assert out["congressional"]["contests"][0]["district"]=="1"
    assert out["legislative"]["contests"][0]["district"]=="2"
    assert out["local"]["contests"][0]["leader"]=="Candidate G"
    assert all(v["publishable"] is False for v in out.values())


def test_incomplete_boxes_withholds_every_aggregate_leader():
    page=PAGE.replace("100.00%","99.50%",1)
    t=AlabamaVotesTransport("https://www2.alabamavotes.gov/results",lambda u:page)
    out=normalize_transport(t)
    for payload in out.values():
        for contest in payload["contests"]:
            assert contest["leader"] is None
            assert contest["aggregateLeaderPublishable"] is False
