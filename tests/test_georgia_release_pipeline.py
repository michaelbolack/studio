import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core.ingestion_context import IngestionContext
from election_core.georgia_release_pipeline import collect_georgia_payloads, prepare_georgia_release

URL = "https://results.sos.ga.gov/results/public/Georgia/elections/test"
TEXT = """
## Governor
Localities | Precincts reporting 159/159
Jane Doe (REP) 100
John Doe (DEM) 90
## U.S. House District 1
Localities | Precincts reporting 10/10
A Candidate (REP) 50
B Candidate (DEM) 40
## State Senate District 1
Localities | Precincts reporting 5/5
C Candidate (REP) 30
D Candidate (DEM) 20
## Fulton County Sheriff
Localities | Precincts reporting 1/1
E Candidate (REP) 10
F Candidate (DEM) 9
"""


def _context():
    return IngestionContext(state="GA", election_key="test", name="Test Election", date="2026-11-03")


def _evidence():
    proof = {
        "authoritativeSource": True,
        "coverageComplete": True,
        "totalsReconciled": True,
        "districtSafetyPassed": True,
        "statePolicyPassed": True,
    }
    return {scope: dict(proof) for scope in ("statewide", "congressional", "legislative", "local")}


def test_georgia_can_collect_while_registry_remains_disabled():
    payloads = collect_georgia_payloads(election_url=URL, get_text=lambda _: TEXT, context=_context())
    assert set(payloads) == {"statewide", "congressional", "legislative", "local"}
    assert all(payload["state"] == "GA" for payload in payloads.values())
    assert all(payload["publishable"] is False for payload in payloads.values())


def test_georgia_release_requires_explicit_evidence():
    evidence = _evidence()
    evidence["congressional"]["districtSafetyPassed"] = False
    with pytest.raises(RuntimeError, match="scope release withheld"):
        prepare_georgia_release(election_url=URL, get_text=lambda _: TEXT, context=_context(), evidence=evidence)


def test_georgia_release_marks_all_scopes_only_after_gate():
    released = prepare_georgia_release(election_url=URL, get_text=lambda _: TEXT, context=_context(), evidence=_evidence())
    assert set(released) == {"statewide", "congressional", "legislative", "local"}
    assert all(payload["publishable"] is True for payload in released.values())
