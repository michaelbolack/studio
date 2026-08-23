"""Promote validated state scope payloads into publishable generated feeds.

Nothing becomes publishable merely because parsing succeeded. Callers must provide
explicit release evidence for source authority, coverage, reconciliation, and the
state-specific safety policy.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any

REQUIRED_RELEASE_EVIDENCE = (
    "authoritativeSource",
    "coverageComplete",
    "totalsReconciled",
    "districtSafetyPassed",
    "statePolicyPassed",
)


def release_scope_payload(
    payload: dict[str, Any],
    *,
    state: str,
    scope: str,
    evidence: dict[str, bool],
) -> dict[str, Any]:
    code = state.strip().upper()
    if not isinstance(payload, dict):
        raise RuntimeError("scope payload must be an object")
    if payload.get("state") != code:
        raise RuntimeError("scope payload state mismatch")
    if payload.get("scope") != scope:
        raise RuntimeError("scope payload scope mismatch")

    missing = [key for key in REQUIRED_RELEASE_EVIDENCE if key not in evidence]
    failed = [key for key in REQUIRED_RELEASE_EVIDENCE if evidence.get(key) is not True]
    if missing or failed:
        raise RuntimeError(f"scope release withheld: missing={missing}; failed={failed}")

    # Mississippi provisional county data can be displayed as provisional in a
    # future UI, but must never be promoted as a certified statewide/district feed.
    if code == "MS" and payload.get("sourceTier") == "provisional-county" and scope != "local":
        raise RuntimeError("Mississippi provisional county data cannot become a publishable aggregate feed")

    released = deepcopy(payload)
    released["publishable"] = True
    released["releaseEvidence"] = {key: True for key in REQUIRED_RELEASE_EVIDENCE}
    return released
