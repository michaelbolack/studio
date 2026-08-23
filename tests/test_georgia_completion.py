import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from election_core.georgia_completion import audit_georgia_completion, REQUIRED_COMPONENTS


def test_all_technical_evidence_can_complete_without_activation():
    result = audit_georgia_completion({key: True for key in REQUIRED_COMPONENTS})
    assert result["implementationComplete"] is True
    assert result["activationAuthorized"] is False
    assert result["missing"] == []
    assert result["failed"] == []


def test_missing_component_blocks_completion():
    evidence = {key: True for key in REQUIRED_COMPONENTS if key != "localPipeline"}
    result = audit_georgia_completion(evidence)
    assert result["implementationComplete"] is False
    assert result["missing"] == ["localPipeline"]


def test_failed_safety_component_blocks_completion():
    evidence = {key: True for key in REQUIRED_COMPONENTS}
    evidence["incompleteLeaderWithholding"] = False
    result = audit_georgia_completion(evidence)
    assert result["implementationComplete"] is False
    assert result["failed"] == ["incompleteLeaderWithholding"]
