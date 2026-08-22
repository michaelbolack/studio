import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "jurisdictions.json"
sys.path.insert(0, str(ROOT / "scripts"))

from election_core import RegistryError, default_jurisdiction, enabled_jurisdictions, get_jurisdiction

STATE_CODES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"
}
EXTRA_CODES = {"DC","AS","GU","MP","PR","VI"}


def load_registry():
    return json.loads(REGISTRY.read_text())


def test_registry_contains_all_states_dc_and_major_territories():
    data = load_registry()
    assert set(data["states"]) == STATE_CODES | EXTRA_CODES
    assert len(data["states"]) == 56


def test_only_florida_is_enabled_during_migration():
    data = load_registry()
    enabled = [code for code, item in data["states"].items() if item.get("enabled")]
    assert enabled == ["FL"]
    assert [item["id"] for item in enabled_jurisdictions()] == ["FL"]


def test_only_florida_is_default():
    data = load_registry()
    defaults = [code for code, item in data["states"].items() if item.get("default")]
    assert defaults == ["FL"]
    assert default_jurisdiction()["id"] == "FL"


def test_disabled_state_is_registered_but_cannot_be_requested_as_enabled():
    texas = get_jurisdiction("tx")
    assert texas["id"] == "TX"
    assert texas["enabled"] is False
    with pytest.raises(RegistryError, match="not enabled"):
        get_jurisdiction("TX", require_enabled=True)


def test_florida_can_be_requested_as_enabled():
    florida = get_jurisdiction("fl", require_enabled=True)
    assert florida["id"] == "FL"
    assert florida["enabled"] is True


def test_unknown_jurisdiction_is_rejected():
    with pytest.raises(RegistryError, match="unknown jurisdiction"):
        get_jurisdiction("ZZ")


def test_all_entries_have_unique_two_digit_fips_codes():
    data = load_registry()
    fips = [item["fips"] for item in data["states"].values()]
    assert all(len(code) == 2 and code.isdigit() for code in fips)
    assert len(fips) == len(set(fips))


def test_disabled_jurisdictions_cannot_define_live_data_scopes():
    data = load_registry()
    for code, item in data["states"].items():
        if not item.get("enabled"):
            assert "manifest" not in item, code
            assert "scopes" not in item, code


def test_florida_keeps_existing_compatibility_paths():
    florida = load_registry()["states"]["FL"]
    assert florida["manifest"] == "data/manifest.json"
    assert florida["scopes"]["statewide"] == "data/statewide.json"
    assert florida["scopes"]["congressional"] == "data/congressional.json"
    assert florida["scopes"]["legislative"] == "data/legislative.json"


def test_fail_closed_policy_is_global_default():
    data = load_registry()
    assert data["defaults"]["publishIncompleteAggregateLeaders"] is False
    assert data["states"]["FL"]["sourcePolicy"]["publishIncompleteAggregateLeaders"] is False


def test_special_local_jurisdiction_types_are_preserved():
    states = load_registry()["states"]
    assert states["AK"]["localJurisdictionType"] == "borough-or-census-area"
    assert states["LA"]["localJurisdictionType"] == "parish"
    assert states["DC"]["localJurisdictionType"] == "ward"
