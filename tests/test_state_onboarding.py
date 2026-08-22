import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core import RegistryError
from election_core.onboarding import load_onboarding_profile


def test_georgia_research_profile_loads_without_enabling_state():
    profile = load_onboarding_profile("GA")
    assert profile["state"] == "GA"
    assert profile["enabled"] is False
    assert profile["status"] == "research-only"
    assert profile["expectedLocalJurisdictions"] == 159
    assert profile["authority"] == "Georgia Secretary of State"


def test_missing_profile_fails_closed():
    with pytest.raises(RegistryError, match="profile missing"):
        load_onboarding_profile("TX")


def test_profile_cannot_claim_enabled(tmp_path):
    root = tmp_path / "profiles"
    root.mkdir()
    source = json.loads((ROOT / "data" / "state-onboarding" / "ga.json").read_text())
    source["enabled"] = True
    (root / "ga.json").write_text(json.dumps(source))
    with pytest.raises(RegistryError, match="research-only and disabled"):
        load_onboarding_profile("GA", root)


def test_profile_requires_https_official_sources(tmp_path):
    root = tmp_path / "profiles"
    root.mkdir()
    source = json.loads((ROOT / "data" / "state-onboarding" / "ga.json").read_text())
    source["officialSources"]["resultsIndex"] = "http://example.invalid/results"
    (root / "ga.json").write_text(json.dumps(source))
    with pytest.raises(RegistryError, match="must be https"):
        load_onboarding_profile("GA", root)


def test_profile_requires_core_result_capabilities(tmp_path):
    root = tmp_path / "profiles"
    root.mkdir()
    source = json.loads((ROOT / "data" / "state-onboarding" / "ga.json").read_text())
    source["observedCapabilities"]["congressionalResults"] = False
    (root / "ga.json").write_text(json.dumps(source))
    with pytest.raises(RegistryError, match="congressionalResults"):
        load_onboarding_profile("GA", root)
