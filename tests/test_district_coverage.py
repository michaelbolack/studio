import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from election_core.district_coverage import coverage_path, load_district_coverage
from election_core import RegistryError


def test_disabled_state_cannot_resolve_coverage_manifest():
    with pytest.raises(RegistryError, match="not enabled"):
        coverage_path("GA", "congressional", "2026-primary")


def test_missing_florida_manifest_fails_closed():
    with pytest.raises(RegistryError, match="not configured"):
        load_district_coverage("FL", "congressional", "2099-test", 9)


def test_manifest_requires_exact_district_entry(tmp_path):
    path = tmp_path / "fl" / "districts" / "2026-primary"
    path.mkdir(parents=True)
    (path / "congressional.json").write_text(json.dumps({
        "state":"FL","districtType":"congressional","electionKey":"2026-primary",
        "districts":{"8":{"jurisdictions":["Brevard"]}}
    }))
    with pytest.raises(RegistryError, match="district coverage is not configured"):
        load_district_coverage("FL", "congressional", "2026-primary", 9, root=tmp_path)


def test_duplicate_jurisdictions_are_rejected(tmp_path):
    path = tmp_path / "fl" / "districts" / "2026-primary"
    path.mkdir(parents=True)
    (path / "congressional.json").write_text(json.dumps({
        "state":"FL","districtType":"congressional","electionKey":"2026-primary",
        "districts":{"9":{"jurisdictions":["Osceola","Osceola"]}}
    }))
    with pytest.raises(RegistryError, match="invalid district jurisdiction coverage"):
        load_district_coverage("FL", "congressional", "2026-primary", 9, root=tmp_path)


def test_valid_manifest_returns_expected_jurisdictions(tmp_path):
    path = tmp_path / "fl" / "districts" / "2026-primary"
    path.mkdir(parents=True)
    (path / "congressional.json").write_text(json.dumps({
        "state":"FL","districtType":"congressional","electionKey":"2026-primary",
        "districts":{"9":{"jurisdictions":["Orange","Osceola"]}}
    }))
    assert load_district_coverage("FL", "congressional", "2026-primary", 9, root=tmp_path) == ["Orange","Osceola"]
