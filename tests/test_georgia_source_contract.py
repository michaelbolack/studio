import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from election_core import RegistryError
from election_core.georgia_source_contract import load_georgia_source_contract

SOURCE = ROOT / "config/elections/onboarding/GA/results-source-2026.json"


def test_pinned_georgia_source_contract_is_valid_but_not_publishable():
    payload = load_georgia_source_contract(SOURCE)
    assert payload["coverageRules"]["statewideExpectedLocalities"] == 159
    assert payload["publishable"] is False


def test_incomplete_coverage_rule_cannot_be_relaxed(tmp_path):
    payload = json.loads(SOURCE.read_text())
    payload["coverageRules"]["requireCompleteLocalitiesBeforeAggregateLeader"] = False
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(RegistryError, match="fail closed"):
        load_georgia_source_contract(path)


def test_split_district_whole_county_reconstruction_cannot_be_enabled(tmp_path):
    payload = json.loads(SOURCE.read_text())
    payload["coverageRules"]["allowWholeCountyReconstructionForSplitDistricts"] = True
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(RegistryError, match="split districts"):
        load_georgia_source_contract(path)
