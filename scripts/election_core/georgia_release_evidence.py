"""Derive non-manual Georgia release evidence from collected official results."""
from __future__ import annotations
from typing import Any
from .georgia_scope_coverage import audit_georgia_scope_coverage,REQUIRED_SCOPES


def derive_georgia_release_evidence(grouped:dict[str,list[dict[str,Any]]],*,authoritative_source:bool,totals_reconciled:dict[str,bool],district_safety:dict[str,bool],state_policy:dict[str,bool])->dict[str,dict[str,bool]]:
    audit=audit_georgia_scope_coverage(grouped)
    evidence={}
    for scope in REQUIRED_SCOPES:
        evidence[scope]={
            "authoritativeSource": authoritative_source is True,
            "coverageComplete": audit["scopes"][scope]["complete"] is True,
            "totalsReconciled": totals_reconciled.get(scope) is True,
            "districtSafetyPassed": district_safety.get(scope) is True,
            "statePolicyPassed": state_policy.get(scope) is True,
        }
    return evidence
