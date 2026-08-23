import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.alabama_transport import AlabamaVotesTransport
from election_core.alabama_release_pipeline import collect_alabama_release,prepare_alabama_release

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

def evidence(ok=True):
    proof={
        "authoritativeSource":ok,
        "coverageComplete":ok,
        "totalsReconciled":ok,
        "districtSafetyPassed":ok,
        "statePolicyPassed":ok,
    }
    return {s:dict(proof) for s in ("statewide","congressional","legislative","local")}

def test_alabama_collector_produces_all_four_scopes():
    t=AlabamaVotesTransport("https://www2.alabamavotes.gov/results",lambda u:PAGE)
    assert set(collect_alabama_release(t))=={"statewide","congressional","legislative","local"}

def test_alabama_can_prepare_release_only_with_complete_evidence():
    t=AlabamaVotesTransport("https://www2.alabamavotes.gov/results",lambda u:PAGE)
    released=prepare_alabama_release(t,evidence=evidence())
    assert all(p["publishable"] is True for p in released.values())
    t=AlabamaVotesTransport("https://www2.alabamavotes.gov/results",lambda u:PAGE)
    bad=evidence(); bad["congressional"]["districtSafetyPassed"]=False
    with pytest.raises(RuntimeError): prepare_alabama_release(t,evidence=bad)
