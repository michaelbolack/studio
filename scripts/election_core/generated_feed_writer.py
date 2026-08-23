"""Write released state-scope payloads only to configured generated-feed paths."""
from __future__ import annotations
import json
from pathlib import Path, PurePosixPath
from typing import Any
from .registry import get_jurisdiction

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_SCOPES = {"statewide", "congressional", "legislative", "local"}


def configured_scope_path(state: str, scope: str) -> Path:
    code = state.strip().upper()
    if scope not in ALLOWED_SCOPES:
        raise RuntimeError(f"unsupported scope: {scope}")
    jurisdiction = get_jurisdiction(code, require_enabled=False)
    scopes = jurisdiction.get("scopes") or {}
    value = scopes.get(scope)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{code} has no configured {scope} generated feed")
    rel = PurePosixPath(value)
    if rel.is_absolute() or ".." in rel.parts:
        raise RuntimeError(f"unsafe {code} {scope} generated feed path")
    path = (REPO_ROOT / rel.as_posix()).resolve()
    root = REPO_ROOT.resolve()
    if root not in path.parents:
        raise RuntimeError("generated feed path escapes repository")
    return path


def write_released_scope(payload: dict[str, Any], *, state: str, scope: str) -> Path:
    code = state.strip().upper()
    if not isinstance(payload, dict):
        raise RuntimeError("released scope must be an object")
    if payload.get("state") != code or payload.get("scope") != scope:
        raise RuntimeError("released scope identity mismatch")
    if payload.get("publishable") is not True:
        raise RuntimeError("refusing to write non-publishable generated feed")
    evidence = payload.get("releaseEvidence")
    if not isinstance(evidence, dict) or not evidence or not all(value is True for value in evidence.values()):
        raise RuntimeError("refusing to write feed without complete release evidence")

    path = configured_scope_path(code, scope)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)
    return path
