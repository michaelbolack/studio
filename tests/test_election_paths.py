import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core import RegistryError, resolve_data_path, resolve_manifest_path


def test_florida_existing_paths_resolve_unchanged():
    assert resolve_manifest_path("FL") == "data/manifest.json"
    assert resolve_data_path("FL", "statewide") == "data/statewide.json"
    assert resolve_data_path("FL", "congressional") == "data/congressional.json"
    assert resolve_data_path("FL", "legislative") == "data/legislative.json"


def test_disabled_state_cannot_resolve_live_data():
    with pytest.raises(RegistryError, match="not enabled"):
        resolve_data_path("TX", "statewide")


def test_unconfigured_local_scope_fails_closed():
    with pytest.raises(RegistryError, match="not configured"):
        resolve_data_path("FL", "local")


def test_unknown_scope_is_rejected():
    with pytest.raises(RegistryError, match="unsupported election scope"):
        resolve_data_path("FL", "precinct-secret")


def test_disabled_territory_cannot_resolve_manifest():
    with pytest.raises(RegistryError, match="not enabled"):
        resolve_manifest_path("PR")
