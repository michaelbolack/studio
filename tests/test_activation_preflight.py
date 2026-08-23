import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core.activation_preflight import preflight_state_activation


def write_registry_state(tmp_path, state="GA"):
    # Preflight reads the real registry for state metadata; tests only override repo root
    # so generated feed files remain isolated.
    base = tmp_path / "data" / "states" / state.lower()
    base.mkdir(parents=True)
    return base


def _proof():
    return {
        "authoritativeSource": True,
        "coverageComplete": True,
        "totalsReconciled": True,
        "districtSafetyPassed": True,
        "statePolicyPassed": True,
    }


def test_disabled_state_is_not_ready_without_registered_adapter_or_paths():
    result = preflight_state_activation("GA", registered_adapters=("FL",), repo_root=tmp_path_placeholder())
    assert result["activationReady"] is False
    assert result["currentlyEnabled"] is False


def tmp_path_placeholder():
    return ROOT


def test_preflight_reports_missing_scope_files_for_configured_state():
    result = preflight_state_activation("GA", registered_adapters=("FL", "GA"), repo_root=ROOT)
    assert result["activationReady"] is False
    assert any("generated feed is missing" in item for item in result["failures"])


def test_preflight_accepts_valid_configured_payloads_via_temp_registry_shape(monkeypatch, tmp_path):
    import election_core.activation_preflight as module

    scopes = {
        "statewide": "data/states/ga/statewide.json",
        "congressional": "data/states/ga/congressional.json",
        "legislative": "data/states/ga/legislative.json",
        "local": "data/states/ga/local.json",
    }
    monkeypatch.setattr(module, "get_jurisdiction", lambda code, require_enabled=False: {"id": "GA", "enabled": False, "scopes": scopes})
    for scope, rel in scopes.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"state": "GA", "scope": scope, "publishable": True, "releaseEvidence": _proof()}))

    result = module.preflight_state_activation("GA", registered_adapters=("FL", "GA"), repo_root=tmp_path)
    assert result["activationReady"] is True
    assert all(item["ready"] is True for item in result["scopes"].values())


def test_not_publishable_scope_blocks_activation(monkeypatch, tmp_path):
    import election_core.activation_preflight as module

    scopes = {scope: f"data/states/ga/{scope}.json" for scope in ("statewide", "congressional", "legislative", "local")}
    monkeypatch.setattr(module, "get_jurisdiction", lambda code, require_enabled=False: {"id": "GA", "enabled": False, "scopes": scopes})
    for scope, rel in scopes.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"state": "GA", "scope": scope, "publishable": scope != "local", "releaseEvidence": _proof()}))

    result = module.preflight_state_activation("GA", registered_adapters=("GA",), repo_root=tmp_path)
    assert result["activationReady"] is False
    assert result["scopes"]["local"]["reason"] == "not-publishable"


def test_publishable_scope_without_complete_release_evidence_is_still_blocked(monkeypatch, tmp_path):
    import election_core.activation_preflight as module

    scopes = {scope: f"data/states/ga/{scope}.json" for scope in ("statewide", "congressional", "legislative", "local")}
    monkeypatch.setattr(module, "get_jurisdiction", lambda code, require_enabled=False: {"id": "GA", "enabled": False, "scopes": scopes})
    for scope, rel in scopes.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        proof = _proof()
        if scope == "congressional":
            proof["districtSafetyPassed"] = False
        path.write_text(json.dumps({"state": "GA", "scope": scope, "publishable": True, "releaseEvidence": proof}))

    result = module.preflight_state_activation("GA", registered_adapters=("GA",), repo_root=tmp_path)
    assert result["activationReady"] is False
    assert result["scopes"]["congressional"]["reason"] == "release-evidence-incomplete"
