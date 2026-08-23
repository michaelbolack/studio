import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.mississippi_release_pipeline import collect_mississippi_certified_release,prepare_mississippi_release

ROWS=[]
for scope,title in (("statewide","US Senate"),("congressional","US House District 1"),("legislative","State Senate District 1"),("local","County Office")):
    ROWS.append({"scope":scope,"title":title,"district":"1" if scope!="statewide" else None,"complete":True,"candidates":[{"name":"A","votes":10},{"name":"B","votes":8}]})

def evidence(ok=True):
    return {s:{"authoritativeSource":ok,"coverageComplete":ok,"totalsReconciled":ok,"districtSafety":ok,"statePolicySatisfied":ok} for s in ("statewide","congressional","legislative","local")}

def test_mississippi_certified_release_requires_all_four_scopes():
    payloads=collect_mississippi_certified_release(ROWS)
    assert set(payloads)=={"statewide","congressional","legislative","local"}
    assert all(p["sourceTier"]=="certified-state" for p in payloads.values())

def test_mississippi_certified_release_can_prepare_with_full_evidence():
    released=prepare_mississippi_release(ROWS,evidence=evidence())
    assert all(p["publishable"] is True for p in released.values())

def test_missing_certified_scope_blocks_activation_release():
    with pytest.raises(RuntimeError,match="all four scopes"):
        collect_mississippi_certified_release(ROWS[:-1])

def test_failed_state_policy_blocks_release():
    bad=evidence(); bad["local"]["statePolicySatisfied"]=False
    with pytest.raises(RuntimeError): prepare_mississippi_release(ROWS,evidence=bad)
