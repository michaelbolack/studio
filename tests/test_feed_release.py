import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core.feed_release import release_scope_payload, REQUIRED_RELEASE_EVIDENCE


def evidence(**overrides):
    data = {key: True for key in REQUIRED_RELEASE_EVIDENCE}
    data.update(overrides)
    return data


def test_validated_scope_can_be_promoted_without_mutating_input():
    raw = {"state": "GA", "scope": "statewide", "publishable": False, "contests": []}
    released = release_scope_payload(raw, state="GA", scope="statewide", evidence=evidence())
    assert raw["publishable"] is False
    assert released["publishable"] is True
    assert all(released["releaseEvidence"].values())


def test_any_failed_release_evidence_withholds_scope():
    raw = {"state": "AL", "scope": "congressional", "publishable": False}
    with pytest.raises(RuntimeError, match="withheld"):
        release_scope_payload(raw, state="AL", scope="congressional", evidence=evidence(coverageComplete=False))


def test_missing_release_evidence_withholds_scope():
    raw = {"state": "GA", "scope": "local", "publishable": False}
    partial = {key: True for key in REQUIRED_RELEASE_EVIDENCE if key != "statePolicyPassed"}
    with pytest.raises(RuntimeError, match="missing"):
        release_scope_payload(raw, state="GA", scope="local", evidence=partial)


def test_mississippi_provisional_county_data_cannot_promote_aggregate_feed():
    raw = {"state": "MS", "scope": "congressional", "sourceTier": "provisional-county", "publishable": False}
    with pytest.raises(RuntimeError, match="provisional"):
        release_scope_payload(raw, state="MS", scope="congressional", evidence=evidence())


def test_state_or_scope_mismatch_fails_closed():
    raw = {"state": "GA", "scope": "statewide", "publishable": False}
    with pytest.raises(RuntimeError, match="state mismatch"):
        release_scope_payload(raw, state="AL", scope="statewide", evidence=evidence())
    with pytest.raises(RuntimeError, match="scope mismatch"):
        release_scope_payload(raw, state="GA", scope="local", evidence=evidence())
