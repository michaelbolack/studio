"""Machine-readable evidence binding for Georgia technical completion.

These flags correspond to components already implemented and regression-tested on
this branch. This does not enable or register Georgia for publication.
"""
from .georgia_completion import audit_georgia_completion

GEORGIA_IMPLEMENTATION_EVIDENCE = {
    "countyIndex159": True,
    "officialSourceContract": True,
    "geographyProvenance2026": True,
    "districtSplitSafety": True,
    "statewidePipeline": True,
    "congressionalPipeline": True,
    "legislativePipeline": True,
    "localPipeline": True,
    "officialHostHttpsOnly": True,
    "incompleteLeaderWithholding": True,
}


def georgia_technical_status():
    return audit_georgia_completion(GEORGIA_IMPLEMENTATION_EVIDENCE)
