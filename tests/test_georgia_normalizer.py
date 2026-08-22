import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from election_core.georgia_normalizer import normalize_georgia_contest, normalize_georgia_scope


def contest(reported=159, total=159):
    return {
        "title": "Secretary of State - Dem",
        "reporting": {"reported": reported, "total": total},
        "candidates": [
            {"name": "Candidate A", "party": "DEM", "votes": 100},
            {"name": "Candidate B", "party": "DEM", "votes": 90},
        ],
    }


def test_complete_contest_may_expose_aggregate_leader():
    result = normalize_georgia_contest(contest(), scope="statewide")
    assert result["reporting"]["complete"] is True
    assert result["leader"] == "Candidate A"
    assert result["aggregateLeaderPublishable"] is True


def test_incomplete_contest_withholds_aggregate_leader():
    result = normalize_georgia_contest(contest(158, 159), scope="statewide")
    assert result["leader"] is None
    assert result["aggregateLeaderPublishable"] is False


def test_scope_remains_research_only_before_activation():
    result = normalize_georgia_scope([contest()], scope="statewide")
    assert result["publishable"] is False
    assert result["status"] == "research-only"


def test_bad_reporting_fails_closed():
    with pytest.raises(ValueError):
        normalize_georgia_contest(contest(160, 159), scope="statewide")


def test_negative_votes_fail_closed():
    raw = contest()
    raw["candidates"][0]["votes"] = -1
    with pytest.raises(ValueError):
        normalize_georgia_contest(raw, scope="statewide")


def test_missing_candidate_name_fails_closed():
    raw = contest()
    raw["candidates"][0]["name"] = ""
    with pytest.raises(ValueError):
        normalize_georgia_contest(raw, scope="statewide")
