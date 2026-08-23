import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.state_feed_release import prepare_state_release,SCOPES

GOOD_EVIDENCE={
    "authoritativeSource":True,"coverageComplete":True,"totalsReconciled":True,
    "districtSafetyPassed":True,"statePolicyPassed":True,
}

def payloads(state="GA"):
    return {scope:{"state":state,"scope":scope,"publishable":False,"contests":[]} for scope in SCOPES}

def evidence():
    return {scope:dict(GOOD_EVIDENCE) for scope in SCOPES}

def test_all_four_scopes_prepare_together():
    released=prepare_state_release(state="GA",payloads=payloads(),evidence=evidence())
    assert tuple(released)==SCOPES
    assert all(released[s]["publishable"] is True for s in SCOPES)

def test_missing_scope_blocks_entire_release_before_writes():
    p=payloads(); p.pop("local")
    with pytest.raises(RuntimeError,match="state release incomplete"):
        prepare_state_release(state="GA",payloads=p,evidence=evidence())

def test_any_failed_scope_blocks_entire_release():
    ev=evidence(); ev["congressional"]["districtSafetyPassed"]=False
    with pytest.raises(RuntimeError,match="scope release withheld"):
        prepare_state_release(state="GA",payloads=payloads(),evidence=ev)

def test_cross_state_payload_blocks_release():
    p=payloads(); p["local"]["state"]="AL"
    with pytest.raises(RuntimeError,match="state mismatch"):
        prepare_state_release(state="GA",payloads=p,evidence=evidence())
