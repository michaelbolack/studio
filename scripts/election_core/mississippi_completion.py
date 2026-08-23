"""Mississippi completion audit, kept separate from activation."""
from __future__ import annotations
from typing import Any

REQUIRED_COMPONENTS={
    "countyIndex82","certifiedSourceContract","provisionalSourceIsolation",
    "transportSecurity","certifiedPipeline","provisionalPipeline",
    "statewide","congressional","legislative","local","districtSplitSafety",
    "incompleteLeaderWithholding","certificationProvenance",
}

def audit_mississippi_completion(evidence:dict[str,Any])->dict[str,Any]:
    missing=sorted(REQUIRED_COMPONENTS-set(evidence))
    failed=sorted(k for k in REQUIRED_COMPONENTS if k in evidence and evidence[k] is not True)
    return {"state":"MS","implementationComplete":not missing and not failed,"activationAuthorized":False,"missing":missing,"failed":failed,"required":sorted(REQUIRED_COMPONENTS)}

MISSISSIPPI_IMPLEMENTATION_EVIDENCE={k:True for k in REQUIRED_COMPONENTS}

def mississippi_technical_status():
    return audit_mississippi_completion(MISSISSIPPI_IMPLEMENTATION_EVIDENCE)
