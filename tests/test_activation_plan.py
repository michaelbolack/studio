import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.activation_plan import plan_state_activations
from election_core.registry import get_jurisdiction

SCOPES=("statewide","congressional","legislative","local")

def write_feeds(root,state):
    j=get_jurisdiction(state,require_enabled=False)
    for scope in SCOPES:
        p=root/j["scopes"][scope]; p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps({"state":state,"scope":scope,"publishable":True,"contests":[]}))

def test_all_requested_states_must_pass_before_registry_mutation(tmp_path):
    write_feeds(tmp_path,"GA"); write_feeds(tmp_path,"AL")
    result=plan_state_activations(["GA","AL","MS"],repo_root=tmp_path)
    assert set(result["ready"])=={"GA","AL"}
    assert result["blocked"]==["MS"]
    assert result["allReady"] is False
    assert result["registryMutationAuthorized"] is False

def test_three_states_authorize_activation_only_after_all_feeds_validate(tmp_path):
    for state in ("GA","AL","MS"): write_feeds(tmp_path,state)
    result=plan_state_activations(["GA","AL","MS"],repo_root=tmp_path)
    assert result["allReady"] is True
    assert result["registryMutationAuthorized"] is True
    assert set(result["ready"])=={"GA","AL","MS"}
