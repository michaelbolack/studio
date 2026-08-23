import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.alabama_normalizer import normalize_alabama_contest, normalize_alabama_scope


def race(reported=67,total=67):
    return {"title":"Governor - Republican","reporting":{"reported":reported,"total":total},"candidates":[{"name":"Candidate A","party":"REP","votes":100},{"name":"Candidate B","party":"REP","votes":90}]}


def test_complete_statewide_contest_can_expose_leader():
    result=normalize_alabama_contest(race(),scope="statewide")
    assert result["reporting"]["complete"] is True
    assert result["leader"]=="Candidate A"


def test_incomplete_statewide_contest_withholds_leader():
    result=normalize_alabama_contest(race(66,67),scope="statewide")
    assert result["leader"] is None
    assert result["aggregateLeaderPublishable"] is False


def test_scope_stays_research_only():
    result=normalize_alabama_scope([race()],scope="statewide")
    assert result["publishable"] is False


def test_invalid_reporting_fails_closed():
    with pytest.raises(ValueError): normalize_alabama_contest(race(68,67),scope="statewide")


def test_negative_votes_fail_closed():
    raw=race(); raw["candidates"][0]["votes"]=-1
    with pytest.raises(ValueError): normalize_alabama_contest(raw,scope="statewide")
