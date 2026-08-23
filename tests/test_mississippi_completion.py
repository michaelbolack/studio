import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.mississippi_completion import mississippi_technical_status,audit_mississippi_completion,REQUIRED_COMPONENTS
from election_core.adapter_factory import registered_adapter_codes

def test_mississippi_complete_but_not_activated():
    r=mississippi_technical_status()
    assert r["implementationComplete"] is True
    assert r["missing"]==[] and r["failed"]==[]
    assert r["activationAuthorized"] is False
    assert "MS" not in registered_adapter_codes()

def test_missing_or_failed_source_safety_blocks_completion():
    e={k:True for k in REQUIRED_COMPONENTS}; e.pop("provisionalSourceIsolation")
    assert audit_mississippi_completion(e)["implementationComplete"] is False
    e={k:True for k in REQUIRED_COMPONENTS}; e["certificationProvenance"]=False
    assert audit_mississippi_completion(e)["implementationComplete"] is False
