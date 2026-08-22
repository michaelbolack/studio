import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core.state_adapter import ElectionContext, StateElectionAdapter
from election_core.state_bundle import build_state_bundle


class StubAdapter(StateElectionAdapter):
    def source_metadata(self):
        return {"authority": "Official source", "system": "Stub"}
    def collect_statewide(self):
        return {"status": "publishable", "scope": "statewide"}
    def collect_congressional(self):
        return {"status": "publishable", "scope": "congressional"}
    def collect_legislative(self):
        return {"status": "publishable", "scope": "legislative"}
    def collect_local(self):
        return {"coverageComplete": True, "scope": "local"}


def adapter():
    return StubAdapter(ElectionContext("FL", "2026-primary", "2026 Florida Primary Election", "2026-08-18"))


def test_bundle_exposes_all_four_scopes_without_rewriting_payloads():
    result = build_state_bundle(adapter())
    assert result["schemaVersion"] == 1
    assert result["state"] == "FL"
    assert result["election"]["key"] == "2026-primary"
    assert set(result["scopes"]) == {"statewide", "congressional", "legislative", "local"}
    assert result["scopes"]["local"]["coverageComplete"] is True


def test_bundle_keeps_source_metadata():
    result = build_state_bundle(adapter())
    assert result["source"]["authority"] == "Official source"


def test_bundle_rejects_invalid_scope_payload():
    a = adapter()
    a.collect_local = lambda: []
    with pytest.raises(RuntimeError, match="local adapter returned non-object payload"):
        build_state_bundle(a)
