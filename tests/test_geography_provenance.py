import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core import RegistryError
from election_core.geography_provenance import load_research_geography_sources


def test_georgia_research_geography_uses_2026_vintages():
    data = load_research_geography_sources("GA")
    assert data["enabled"] is False
    assert data["sources"]["congressional"]["vintage"] == "120th Congress"
    assert data["sources"]["congressional"]["layer"] == "cd120"
    assert data["sources"]["stateSenate"]["layer"] == "sldu"
    assert data["sources"]["stateHouse"]["layer"] == "sldl"


def test_legacy_congressional_vintage_is_rejected(tmp_path):
    source = ROOT / "data" / "state-onboarding" / "ga-geography-sources.json"
    payload = json.loads(source.read_text())
    payload["sources"]["congressional"]["vintage"] = "119th Congress"
    (tmp_path / "ga-geography-sources.json").write_text(json.dumps(payload))
    with pytest.raises(RegistryError, match="wrong 2026 vintage"):
        load_research_geography_sources("GA", tmp_path)


def test_wrong_state_legislative_layer_is_rejected(tmp_path):
    source = ROOT / "data" / "state-onboarding" / "ga-geography-sources.json"
    payload = json.loads(source.read_text())
    payload["sources"]["stateHouse"]["layer"] = "sldu"
    (tmp_path / "ga-geography-sources.json").write_text(json.dumps(payload))
    with pytest.raises(RegistryError, match="wrong 2026 vintage"):
        load_research_geography_sources("GA", tmp_path)


def test_non_https_geography_source_is_rejected(tmp_path):
    source = ROOT / "data" / "state-onboarding" / "ga-geography-sources.json"
    payload = json.loads(source.read_text())
    payload["sources"]["congressional"]["url"] = "http://example.invalid"
    (tmp_path / "ga-geography-sources.json").write_text(json.dumps(payload))
    with pytest.raises(RegistryError, match="must be https"):
        load_research_geography_sources("GA", tmp_path)
