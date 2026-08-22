import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# ElectionContext currently enforces registry activation, so use an equivalent
# immutable fixture object to prove the disabled loader boundary in isolation.
from dataclasses import dataclass
from election_core.georgia_loader import GeorgiaENRLoader


@dataclass(frozen=True)
class ContextFixture:
    state: str = "GA"
    election_key: str = "2026-primary"
    name: str = "2026 Georgia Primary"
    date: str = "2026-05-19"


def raw(scope):
    totals = {"statewide": 159, "congressional": 15, "legislative": 4, "local": 1}
    return [{
        "title": f"Fixture {scope}",
        "district": "1" if scope in {"congressional", "legislative"} else None,
        "reporting": {"reported": totals[scope], "total": totals[scope]},
        "candidates": [
            {"name": "Candidate A", "party": "REP", "votes": 10},
            {"name": "Candidate B", "party": "REP", "votes": 8},
        ],
    }]


def test_loader_normalizes_all_four_scopes():
    seen = []
    def fetcher(scope, context):
        seen.append(scope)
        return raw(scope)

    loader = GeorgiaENRLoader(fetcher)
    ctx = ContextFixture()
    for scope in ("statewide", "congressional", "legislative", "local"):
        result = loader(scope, ctx)
        assert result["state"] == "GA"
        assert result["scope"] == scope
        assert result["publishable"] is False
        assert result["contests"][0]["reporting"]["complete"] is True
        assert result["election"]["key"] == "2026-primary"
    assert seen == ["statewide", "congressional", "legislative", "local"]


def test_incomplete_fixture_withholds_leader_through_loader():
    def fetcher(scope, context):
        rows = raw(scope)
        rows[0]["reporting"] = {"reported": 14, "total": 15}
        return rows
    result = GeorgiaENRLoader(fetcher)("congressional", ContextFixture())
    assert result["contests"][0]["leader"] is None
    assert result["contests"][0]["aggregateLeaderPublishable"] is False
