import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.georgia_release_evidence import derive_georgia_release_evidence
SCOPES=("statewide","congressional","legislative","local")

def c(reported=1,total=1): return {"title":"Race","reporting":{"reported":reported,"total":total},"candidates":[{"name":"A","votes":1}]}
def flags(value=True): return {s:value for s in SCOPES}

def test_complete_coverage_is_derived_from_results():
    grouped={s:[c()] for s in SCOPES}
    e=derive_georgia_release_evidence(grouped,authoritative_source=True,totals_reconciled=flags(),district_safety=flags(),state_policy=flags())
    assert all(e[s]["coverageComplete"] for s in SCOPES)

def test_incomplete_congressional_reporting_cannot_be_overridden_manually():
    grouped={s:[c()] for s in SCOPES}; grouped["congressional"]=[c(9,10)]
    e=derive_georgia_release_evidence(grouped,authoritative_source=True,totals_reconciled=flags(),district_safety=flags(),state_policy=flags())
    assert e["congressional"]["coverageComplete"] is False
    assert e["statewide"]["coverageComplete"] is True

def test_other_safety_evidence_remains_explicit_and_fail_closed():
    grouped={s:[c()] for s in SCOPES}; totals=flags(); totals["local"]=False
    e=derive_georgia_release_evidence(grouped,authoritative_source=True,totals_reconciled=totals,district_safety=flags(),state_policy=flags())
    assert e["local"]["totalsReconciled"] is False
