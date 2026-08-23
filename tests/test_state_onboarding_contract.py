import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.state_onboarding import audit_state_onboarding,REQUIRED_CAPABILITIES

def test_complete_state_foundation_never_auto_activates():
    r=audit_state_onboarding("MS",{k:True for k in REQUIRED_CAPABILITIES})
    assert r["foundationReady"] is True
    assert r["activationAuthorized"] is False

def test_missing_or_failed_capability_blocks_readiness():
    evidence={k:True for k in REQUIRED_CAPABILITIES}; evidence.pop("local")
    assert audit_state_onboarding("MS",evidence)["foundationReady"] is False
    evidence={k:True for k in REQUIRED_CAPABILITIES}; evidence["districtSplitSafety"]=False
    assert audit_state_onboarding("MS",evidence)["foundationReady"] is False
