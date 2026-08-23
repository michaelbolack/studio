import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.alabama_completion import alabama_technical_status,audit_alabama_completion,REQUIRED_COMPONENTS
from election_core.adapter_factory import registered_adapter_codes


def test_alabama_is_technically_complete_but_not_activated():
    status=alabama_technical_status()
    assert status["implementationComplete"] is True
    assert status["missing"]==[] and status["failed"]==[]
    assert status["activationAuthorized"] is False
    assert "AL" not in registered_adapter_codes()


def test_missing_or_failed_component_blocks_completion():
    evidence={k:True for k in REQUIRED_COMPONENTS}; evidence.pop("localPipeline")
    assert audit_alabama_completion(evidence)["implementationComplete"] is False
    evidence={k:True for k in REQUIRED_COMPONENTS}; evidence["incompleteLeaderWithholding"]=False
    assert audit_alabama_completion(evidence)["implementationComplete"] is False
