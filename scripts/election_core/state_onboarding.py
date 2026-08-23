"""Reusable contract for onboarding additional states without touching live adapters."""
from __future__ import annotations
from typing import Any

REQUIRED_CAPABILITIES={"jurisdictionIndex","officialResultsSource","transportSecurity","resultNormalization","statewide","congressional","legislative","local","districtSplitSafety","incompleteLeaderWithholding","completionAudit"}

def audit_state_onboarding(state:str,evidence:dict[str,Any])->dict[str,Any]:
    code=state.strip().upper()
    if len(code)!=2: raise ValueError("two-letter state code required")
    missing=sorted(REQUIRED_CAPABILITIES-set(evidence))
    failed=sorted(k for k in REQUIRED_CAPABILITIES if k in evidence and evidence[k] is not True)
    return {"state":code,"foundationReady":not missing and not failed,"activationAuthorized":False,"missing":missing,"failed":failed}
