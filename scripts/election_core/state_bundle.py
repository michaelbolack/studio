"""Normalized boundary between state adapters and future national consumers.

This module does not fetch election data itself. It calls an already-configured
StateElectionAdapter and returns the four supported scopes in one predictable
container while preserving each collector's existing payload unchanged.
"""
from __future__ import annotations
from typing import Any
from .state_adapter import StateElectionAdapter

SCOPE_KEYS = ("statewide", "congressional", "legislative", "local")


def _require_mapping(scope: str, payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise RuntimeError(f"{scope} adapter returned non-object payload")
    return payload


def build_state_bundle(adapter: StateElectionAdapter) -> dict[str, Any]:
    """Collect all implemented scopes behind one stable state-level contract."""
    scopes = {
        "statewide": _require_mapping("statewide", adapter.collect_statewide()),
        "congressional": _require_mapping("congressional", adapter.collect_congressional()),
        "legislative": _require_mapping("legislative", adapter.collect_legislative()),
        "local": _require_mapping("local", adapter.collect_local()),
    }
    return {
        "schemaVersion": 1,
        "state": adapter.state,
        "election": {
            "key": adapter.context.election_key,
            "name": adapter.context.name,
            "date": adapter.context.date,
        },
        "source": adapter.source_metadata(),
        "scopes": scopes,
    }
