import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core.state_adapter import ElectionContext
from election_core.florida_adapter import FloridaElectionAdapter


def context():
    return ElectionContext("FL", "2026-primary", "2026 Florida Primary Election", "2026-08-18")


def test_florida_adapter_identifies_official_source():
    adapter = FloridaElectionAdapter(context())
    source = adapter.source_metadata()
    assert "Florida Department of State" in source["authority"]
    assert source["system"] == "Florida Election Watch"


def test_florida_adapter_delegates_statewide_without_rewriting_collector(monkeypatch):
    expected = {"status": "publishable", "scope": {"type": "statewide", "state": "FL"}}
    monkeypatch.setattr(FloridaElectionAdapter, "_build", staticmethod(lambda name: expected if name == "statewide_ingestion_v2" else None))
    assert FloridaElectionAdapter(context()).collect_statewide() is expected


def test_florida_adapter_delegates_congressional_without_rewriting_collector(monkeypatch):
    expected = {"status": "publishable", "scope": {"type": "congressional", "state": "FL"}}
    monkeypatch.setattr(FloridaElectionAdapter, "_build", staticmethod(lambda name: expected if name == "congressional_ingestion_v2" else None))
    assert FloridaElectionAdapter(context()).collect_congressional() is expected


def test_florida_adapter_delegates_verified_legislative_collector(monkeypatch):
    expected = {"status": "publishable", "scope": {"type": "state-legislative", "state": "FL"}}
    monkeypatch.setattr(FloridaElectionAdapter, "_build", staticmethod(lambda name: expected if name == "florida_legislative_ingestion_v2" else None))
    assert FloridaElectionAdapter(context()).collect_legislative() is expected


def test_florida_adapter_still_does_not_guess_local_scope():
    with pytest.raises(NotImplementedError):
        FloridaElectionAdapter(context()).collect_local()


def test_florida_adapter_rejects_non_florida_context():
    with pytest.raises(Exception):
        FloridaElectionAdapter(ElectionContext("GA", "2026-general", "Georgia General", "2026-11-03"))
