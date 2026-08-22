import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core import RegistryError
from election_core.research_district_coverage import load_research_district_coverage

GA_LOCAL = ROOT / "data" / "jurisdictions" / "ga" / "local.json"


def write_manifest(tmp_path, districts, *, state="GA", district_type="congressional", status="research-only"):
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps({
        "schemaVersion": 1,
        "state": state,
        "districtType": district_type,
        "status": status,
        "districts": districts,
    }))
    return path


def test_disabled_georgia_can_validate_research_district_manifest(tmp_path):
    path = write_manifest(tmp_path, {"1": ["Chatham", "Bryan"], "2": ["Muscogee", "Dougherty"]})
    result = load_research_district_coverage(
        state="GA",
        district_type="congressional",
        manifest_path=path,
        local_index_path=GA_LOCAL,
    )
    assert result["state"] == "GA"
    assert result["districtCount"] == 2
    assert result["publishable"] is False
    assert result["status"] == "research-only"


def test_unknown_geography_fails_closed(tmp_path):
    path = write_manifest(tmp_path, {"1": ["Chatham", "Not A Georgia County"]})
    with pytest.raises(RegistryError, match="unknown geographies"):
        load_research_district_coverage(
            state="GA", district_type="congressional", manifest_path=path, local_index_path=GA_LOCAL
        )


def test_duplicate_geography_fails_closed(tmp_path):
    path = write_manifest(tmp_path, {"1": ["Chatham", "Chatham"]})
    with pytest.raises(RegistryError, match="duplicate geographies"):
        load_research_district_coverage(
            state="GA", district_type="congressional", manifest_path=path, local_index_path=GA_LOCAL
        )


def test_wrong_state_fails_closed(tmp_path):
    path = write_manifest(tmp_path, {"1": ["Chatham"]}, state="FL")
    with pytest.raises(RegistryError, match="state mismatch"):
        load_research_district_coverage(
            state="GA", district_type="congressional", manifest_path=path, local_index_path=GA_LOCAL
        )


def test_non_research_manifest_cannot_be_loaded(tmp_path):
    path = write_manifest(tmp_path, {"1": ["Chatham"]}, status="enabled")
    with pytest.raises(RegistryError, match="must remain research-only"):
        load_research_district_coverage(
            state="GA", district_type="congressional", manifest_path=path, local_index_path=GA_LOCAL
        )


def test_unsupported_district_type_fails_closed(tmp_path):
    path = write_manifest(tmp_path, {"1": ["Chatham"]}, district_type="county-commission")
    with pytest.raises(RegistryError, match="unsupported research district type"):
        load_research_district_coverage(
            state="GA", district_type="county-commission", manifest_path=path, local_index_path=GA_LOCAL
        )
