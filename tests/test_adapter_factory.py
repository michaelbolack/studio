import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core import RegistryError
from election_core.adapter_factory import create_state_adapter, registered_adapter_codes
from election_core.florida_adapter import FloridaElectionAdapter
from election_core.state_adapter import ElectionContext


def test_only_florida_adapter_is_registered_today():
    assert registered_adapter_codes() == ("FL",)


def test_factory_returns_florida_adapter_for_enabled_florida():
    context = ElectionContext("FL", "2026-primary", "2026 Florida Primary Election", "2026-08-18")
    assert isinstance(create_state_adapter(context), FloridaElectionAdapter)


def test_disabled_registered_jurisdiction_cannot_reach_factory():
    with pytest.raises(RegistryError, match="not enabled"):
        ElectionContext("GA", "2026-general", "2026 Georgia General Election", "2026-11-03")


def test_unknown_jurisdiction_cannot_reach_factory():
    with pytest.raises(RegistryError, match="unknown jurisdiction"):
        ElectionContext("ZZ", "2026-general", "Unknown General Election", "2026-11-03")
