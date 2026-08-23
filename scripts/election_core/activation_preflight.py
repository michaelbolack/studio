"""Fail-closed activation preflight for nationally onboarded states.

A state is not safe to enable until its live adapter exists and every configured
scope file is present, state/scope matched, explicitly publishable, and carries the
complete release evidence required by the national publication gate.
"""
from __future__ import annotations
import json
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from .feed_release import REQUIRED_RELEASE_EVIDENCE
from .registry import get_jurisdiction

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_SCOPES = ("statewide", "congressional", "legislative", "local")


def _safe_path(value: str) -> Path:
    rel = PurePosixPath(value)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise RuntimeError(f"unsafe generated feed path: {value}")
    return REPO_ROOT / rel.as_posix()


def _release_evidence_complete(payload: dict[str, Any]) -> bool:
    evidence = payload.get("releaseEvidence")
    if not isinstance(evidence, dict):
        return False
    return all(evidence.get(key) is True for key in REQUIRED_RELEASE_EVIDENCE)


def preflight_state_activation(
    state: str,
    *,
    registered_adapters: Iterable[str],
    repo_root: Path | None = None,
) -> dict[str, Any]:
    code = state.strip().upper()
    jurisdiction = get_jurisdiction(code, require_enabled=False)
    adapter_codes = {x.strip().upper() for x in registered_adapters}
    failures: list[str] = []

    if code not in adapter_codes:
        failures.append("live adapter is not registered")

    scopes = jurisdiction.get("scopes") or {}
    root = repo_root or REPO_ROOT
    scope_status: dict[str, Any] = {}
    for scope in REQUIRED_SCOPES:
        value = scopes.get(scope)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{scope} generated feed path is not configured")
            scope_status[scope] = {"ready": False, "reason": "path-not-configured"}
            continue
        try:
            configured = _safe_path(value)
        except RuntimeError:
            failures.append(f"{scope} generated feed path is unsafe")
            scope_status[scope] = {"ready": False, "reason": "unsafe-path"}
            continue
        path = root / configured.relative_to(REPO_ROOT) if repo_root is not None else configured
        if not path.exists():
            failures.append(f"{scope} generated feed is missing")
            scope_status[scope] = {"ready": False, "reason": "missing"}
            continue
        try:
            payload = json.loads(path.read_text())
        except Exception:
            failures.append(f"{scope} generated feed is malformed")
            scope_status[scope] = {"ready": False, "reason": "malformed"}
            continue
        reason = None
        if not isinstance(payload, dict):
            reason = "not-object"
        elif payload.get("state") != code:
            reason = "state-mismatch"
        elif payload.get("scope") != scope:
            reason = "scope-mismatch"
        elif payload.get("publishable") is not True:
            reason = "not-publishable"
        elif not _release_evidence_complete(payload):
            reason = "release-evidence-incomplete"
        if reason:
            failures.append(f"{scope} generated feed failed validation: {reason}")
            scope_status[scope] = {"ready": False, "reason": reason}
        else:
            scope_status[scope] = {"ready": True}

    return {
        "state": code,
        "activationReady": not failures,
        "currentlyEnabled": bool(jurisdiction.get("enabled")),
        "failures": failures,
        "scopes": scope_status,
    }
