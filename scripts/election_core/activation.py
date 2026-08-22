"""Preflight checks for safely activating a jurisdiction in the national Election Center.

This module never enables a state. It only reports whether registry configuration
and adapter registration satisfy the minimum national-core requirements.
"""
from __future__ import annotations
from typing import Any
from .adapter_factory import registered_adapter_codes
from .registry import get_jurisdiction

REQUIRED_SCOPE_KEYS = ("statewide", "congressional", "legislative")


def state_activation_readiness(code: str) -> dict[str, Any]:
    jurisdiction = get_jurisdiction(code, require_enabled=False)
    state = jurisdiction["id"]
    problems: list[str] = []

    if not jurisdiction.get("enabled"):
        problems.append("jurisdiction is disabled")
    if state not in registered_adapter_codes():
        problems.append("no registered state adapter")

    manifest = jurisdiction.get("manifest")
    if not isinstance(manifest, str) or not manifest.strip():
        problems.append("manifest path is not configured")

    scopes = jurisdiction.get("scopes")
    if not isinstance(scopes, dict):
        problems.append("scope paths are not configured")
    else:
        for scope in REQUIRED_SCOPE_KEYS:
            value = scopes.get(scope)
            if not isinstance(value, str) or not value.strip():
                problems.append(f"{scope} scope path is not configured")

    local_type = jurisdiction.get("localJurisdictionType")
    if not isinstance(local_type, str) or not local_type.strip():
        problems.append("local jurisdiction type is not configured")

    policy = jurisdiction.get("sourcePolicy")
    if not isinstance(policy, dict):
        problems.append("source policy is not configured")
    else:
        if not policy.get("authoritativeStateSource"):
            problems.append("authoritative state source is not configured")
        if policy.get("publishIncompleteAggregateLeaders") is not False:
            problems.append("incomplete aggregate leaders are not explicitly disabled")

    return {
        "state": state,
        "ready": not problems,
        "enabled": bool(jurisdiction.get("enabled")),
        "adapterRegistered": state in registered_adapter_codes(),
        "problems": problems,
    }
