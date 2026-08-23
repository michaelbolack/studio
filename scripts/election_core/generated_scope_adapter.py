"""File-backed adapter base for nationally onboarded states.

Production ingestion jobs write validated normalized scope payloads to configured
registry paths. This adapter only reads those generated files and fails closed if
a scope is missing, malformed, or belongs to another state.
"""
from __future__ import annotations
import json
from pathlib import Path, PurePosixPath
from typing import Any
from .state_adapter import ElectionContext, StateElectionAdapter

REPO_ROOT = Path(__file__).resolve().parents[2]


class GeneratedScopeStateAdapter(StateElectionAdapter):
    expected_state: str = ""
    authority: str = ""
    system: str = ""

    def __init__(self, context: ElectionContext) -> None:
        if context.state.upper() != self.expected_state:
            raise ValueError(f"{self.__class__.__name__} only supports {self.expected_state}")
        super().__init__(context)

    def source_metadata(self) -> dict[str, str]:
        return {"authority": self.authority, "system": self.system}

    def _scope_path(self, scope: str) -> Path:
        scopes = self.jurisdiction.get("scopes") or {}
        value = scopes.get(scope)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"{self.state} has no configured {scope} generated feed")
        rel = PurePosixPath(value)
        if rel.is_absolute() or ".." in rel.parts:
            raise RuntimeError(f"unsafe {self.state} {scope} feed path")
        return REPO_ROOT / rel.as_posix()

    def _load_scope(self, scope: str) -> dict[str, Any]:
        path = self._scope_path(scope)
        if not path.exists():
            raise RuntimeError(f"{self.state} {scope} generated feed is missing")
        payload = json.loads(path.read_text())
        if not isinstance(payload, dict):
            raise RuntimeError(f"{self.state} {scope} generated feed is not an object")
        if payload.get("state") != self.state:
            raise RuntimeError(f"{self.state} {scope} generated feed state mismatch")
        if payload.get("scope") != scope:
            raise RuntimeError(f"{self.state} {scope} generated feed scope mismatch")
        if payload.get("publishable") is not True:
            raise RuntimeError(f"{self.state} {scope} generated feed is not publishable")
        return payload

    def collect_statewide(self) -> dict[str, Any]:
        return self._load_scope("statewide")

    def collect_congressional(self) -> dict[str, Any]:
        return self._load_scope("congressional")

    def collect_legislative(self) -> dict[str, Any]:
        return self._load_scope("legislative")

    def collect_local(self) -> dict[str, Any]:
        return self._load_scope("local")
