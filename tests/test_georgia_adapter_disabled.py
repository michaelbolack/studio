import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core.state_adapter import ElectionContext


def test_georgia_context_remains_blocked_until_registry_activation():
    with pytest.raises(Exception):
        ElectionContext("GA", "2026-primary", "2026 Georgia Primary", "2026-05-19")


def test_georgia_adapter_module_exists_without_registering_state():
    from election_core.georgia_adapter import GeorgiaElectionAdapter
    assert GeorgiaElectionAdapter.__name__ == "GeorgiaElectionAdapter"
