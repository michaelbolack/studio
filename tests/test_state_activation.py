import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core.activation import state_activation_readiness


def test_florida_meets_activation_preflight():
    result = state_activation_readiness("FL")
    assert result["state"] == "FL"
    assert result["ready"] is True
    assert result["enabled"] is True
    assert result["adapterRegistered"] is True
    assert result["problems"] == []


def test_disabled_state_is_not_ready_even_if_registered_in_national_registry():
    result = state_activation_readiness("GA")
    assert result["state"] == "GA"
    assert result["ready"] is False
    assert result["enabled"] is False
    assert "jurisdiction is disabled" in result["problems"]
    assert "no registered state adapter" in result["problems"]


def test_disabled_state_without_paths_or_policy_reports_configuration_gaps():
    result = state_activation_readiness("TX")
    assert result["ready"] is False
    assert "manifest path is not configured" in result["problems"]
    assert "scope paths are not configured" in result["problems"]
    assert "local jurisdiction type is not configured" in result["problems"]
    assert "source policy is not configured" in result["problems"]
