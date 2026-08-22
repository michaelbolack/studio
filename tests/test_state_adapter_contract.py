import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from election_core import RegistryError
from election_core.state_adapter import ElectionContext, StateElectionAdapter


class FloridaStub(StateElectionAdapter):
    def source_metadata(self):
        return {"authority":"Official Florida source","url":"https://example.invalid"}
    def collect_statewide(self):
        return {"state":self.state,"scope":"statewide"}
    def collect_congressional(self):
        return {"state":self.state,"scope":"congressional"}


def test_enabled_state_can_use_adapter_contract():
    adapter = FloridaStub(ElectionContext("fl","2026-primary","2026 Florida Primary","2026-08-18"))
    assert adapter.state == "FL"
    assert adapter.collect_statewide()["state"] == "FL"


def test_disabled_state_cannot_instantiate_adapter():
    with pytest.raises(RegistryError, match="not enabled"):
        ElectionContext("GA","2026-general","2026 Georgia General","2026-11-03")


def test_optional_scopes_fail_explicitly_when_not_implemented():
    adapter = FloridaStub(ElectionContext("FL","2026-primary","2026 Florida Primary","2026-08-18"))
    with pytest.raises(NotImplementedError, match="legislative"):
        adapter.collect_legislative()
    with pytest.raises(NotImplementedError, match="local"):
        adapter.collect_local()
