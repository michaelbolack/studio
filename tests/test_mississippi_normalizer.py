import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.mississippi_normalizer import normalize_mississippi_contest

def race(complete=True):
    return {"title":"US House District 1","district":"1","complete":complete,"sourceAuthority":"County Election Commission","candidates":[{"name":"A","votes":100},{"name":"B","votes":90}]}

def test_certified_state_result_is_marked_certified():
    r=normalize_mississippi_contest(race(),scope="congressional",source_tier="certified-state")
    assert r["certified"] is True and r["publishableAsCertified"] is True

def test_county_election_night_result_never_becomes_certified():
    r=normalize_mississippi_contest(race(),scope="congressional",source_tier="provisional-county")
    assert r["certified"] is False and r["status"]=="provisional" and r["publishableAsCertified"] is False

def test_incomplete_result_withholds_leader_for_both_tiers():
    for tier in ("certified-state","provisional-county"):
        r=normalize_mississippi_contest(race(False),scope="congressional",source_tier=tier)
        assert r["leader"] is None and r["aggregateLeaderPublishable"] is False
