import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.georgia_scope_coverage import audit_georgia_scope_coverage,REQUIRED_SCOPES

def contest(title="Race",reported=159,total=159):
    return {"title":title,"reporting":{"reported":reported,"total":total},"candidates":[{"name":"A","votes":1}]}

def test_all_four_complete_scopes_pass():
    grouped={scope:[contest(scope)] for scope in REQUIRED_SCOPES}
    r=audit_georgia_scope_coverage(grouped)
    assert r["coverageComplete"] is True and r["failures"]==[]

def test_missing_local_scope_blocks_release_coverage():
    grouped={scope:[contest(scope)] for scope in REQUIRED_SCOPES}
    grouped["local"]=[]
    r=audit_georgia_scope_coverage(grouped)
    assert r["coverageComplete"] is False
    assert r["scopes"]["local"]["complete"] is False

def test_partially_reporting_contest_blocks_scope():
    grouped={scope:[contest(scope)] for scope in REQUIRED_SCOPES}
    grouped["congressional"]=[contest("US House District 1",158,159)]
    r=audit_georgia_scope_coverage(grouped)
    assert r["coverageComplete"] is False
    assert r["scopes"]["congressional"]["incomplete"]==["US House District 1"]
