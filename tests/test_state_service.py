import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core import RegistryError
from election_core.state_adapter import ElectionContext, StateElectionAdapter
import election_core.state_service as service


class StubAdapter(StateElectionAdapter):
    def source_metadata(self):
        return {"authority": "Official source", "system": "Stub"}
    def collect_statewide(self):
        return {"scope": "statewide"}
    def collect_congressional(self):
        return {"scope": "congressional"}
    def collect_legislative(self):
        return {"scope": "legislative"}
    def collect_local(self):
        return {"scope": "local", "coverageComplete": True}


def fl_context():
    return ElectionContext("FL", "2026-primary", "2026 Florida Primary", "2026-08-18")


def test_supported_codes_only_reports_registered_adapters():
    assert service.supported_state_codes() == ("FL",)


def test_service_builds_bundle_through_factory(monkeypatch):
    stub = StubAdapter(fl_context())
    monkeypatch.setattr(service, "create_state_adapter", lambda context: stub)
    result = service.build_enabled_state_bundle(fl_context())
    assert result["state"] == "FL"
    assert set(result["scopes"]) == {"statewide", "congressional", "legislative", "local"}


def test_disabled_state_still_fails_before_service_can_build():
    with pytest.raises(RegistryError, match="not enabled"):
        ElectionContext("GA", "2026-general", "2026 Georgia General", "2026-11-03")
