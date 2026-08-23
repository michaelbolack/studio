import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.activation_report import national_activation_report


def test_onboarded_states_remain_blocked_until_generated_feeds_exist():
    report=national_activation_report()
    assert set(report["states"])=={"GA","AL","MS"}
    assert report["activationReady"]==[]
    assert set(report["blocked"])=={"GA","AL","MS"}
    for code,item in report["states"].items():
        assert item["currentlyEnabled"] is False
        assert item["activationReady"] is False
        assert all(item["scopes"][scope]["ready"] is False for scope in ("statewide","congressional","legislative","local"))
        assert all(item["scopes"][scope]["reason"]=="missing" for scope in ("statewide","congressional","legislative","local"))
