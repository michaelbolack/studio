import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from election_core.georgia_evidence import georgia_technical_status
from election_core.adapter_factory import registered_adapter_codes
from election_core.registry import get_jurisdiction


def test_georgia_is_technically_complete_but_not_activated():
    status = georgia_technical_status()
    assert status["implementationComplete"] is True
    assert status["missing"] == []
    assert status["failed"] == []
    assert status["activationAuthorized"] is False
    assert "GA" in registered_adapter_codes()
    assert get_jurisdiction("GA")["enabled"] is False
