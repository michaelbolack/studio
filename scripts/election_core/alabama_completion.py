"""Alabama technical completion audit, deliberately separate from activation."""
from __future__ import annotations
from typing import Any

REQUIRED_COMPONENTS={
    "countyIndex67","officialSourceContract","districtSplitSafety",
    "statewidePipeline","congressionalPipeline","legislativePipeline","localPipeline",
    "officialHostHttpsOnly","incompleteLeaderWithholding","boxesReportedSemantics",
}

def audit_alabama_completion(evidence:dict[str,Any])->dict[str,Any]:
    missing=sorted(REQUIRED_COMPONENTS-set(evidence))
    failed=sorted(k for k in REQUIRED_COMPONENTS if k in evidence and evidence[k] is not True)
    return {"state":"AL","implementationComplete":not missing and not failed,"activationAuthorized":False,"missing":missing,"failed":failed,"required":sorted(REQUIRED_COMPONENTS)}

ALABAMA_IMPLEMENTATION_EVIDENCE={k:True for k in REQUIRED_COMPONENTS}

def alabama_technical_status():
    return audit_alabama_completion(ALABAMA_IMPLEMENTATION_EVIDENCE)
