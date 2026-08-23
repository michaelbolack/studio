"""Georgia implementation completion audit.

Completion is deliberately separate from activation: Georgia may be technically
complete while remaining disabled until an explicit release decision.
"""
from __future__ import annotations
from typing import Any

REQUIRED_COMPONENTS = {
    "countyIndex159",
    "officialSourceContract",
    "geographyProvenance2026",
    "districtSplitSafety",
    "statewidePipeline",
    "congressionalPipeline",
    "legislativePipeline",
    "localPipeline",
    "officialHostHttpsOnly",
    "incompleteLeaderWithholding",
}


def audit_georgia_completion(evidence: dict[str, Any]) -> dict[str, Any]:
    supplied = set(evidence)
    missing = sorted(REQUIRED_COMPONENTS - supplied)
    failed = sorted(k for k in REQUIRED_COMPONENTS if k in evidence and evidence[k] is not True)
    complete = not missing and not failed
    return {
        "state": "GA",
        "implementationComplete": complete,
        "activationAuthorized": False,
        "missing": missing,
        "failed": failed,
        "required": sorted(REQUIRED_COMPONENTS),
    }
