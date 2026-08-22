import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core.florida_local_compat import load_florida_local_compat
from election_core.local_index import load_local_index
from election_core.registry import RegistryError


def make_manifest(path, mutate=None):
    counties = {}
    for item in load_local_index("FL")["jurisdictions"]:
        counties[item["name"]] = {
            "connected": True,
            "file": f"data/{item['slug']}.json",
            "sourceUrl": f"https://example.invalid/{item['slug']}",
            "adapter": "test",
            "races": 1,
        }
    manifest = {"generatedAt": "2026-08-22T00:00:00+00:00", "counties": counties}
    if mutate:
        mutate(manifest)
    path.write_text(json.dumps(manifest))
    return path


def test_all_67_connected_is_complete(tmp_path):
    result = load_florida_local_compat(make_manifest(tmp_path / "manifest.json"))
    assert result["expected"] == 67
    assert result["connected"] == 67
    assert result["coverageComplete"] is True
    assert result["disconnected"] == []
    indian_river = next(x for x in result["jurisdictions"] if x["name"] == "Indian River")
    assert indian_river["id"] == "FL-12061"
    assert indian_river["fips"] == "12061"


def test_disconnected_county_cannot_be_complete(tmp_path):
    def mutate(manifest):
        manifest["counties"]["Brevard"]["connected"] = False
    result = load_florida_local_compat(make_manifest(tmp_path / "manifest.json", mutate))
    assert result["connected"] == 66
    assert result["coverageComplete"] is False
    assert result["disconnected"] == ["Brevard"]


def test_missing_county_fails_closed(tmp_path):
    def mutate(manifest):
        del manifest["counties"]["St. Lucie"]
    with pytest.raises(RegistryError, match="coverage mismatch"):
        load_florida_local_compat(make_manifest(tmp_path / "manifest.json", mutate))


def test_unexpected_county_fails_closed(tmp_path):
    def mutate(manifest):
        manifest["counties"]["Not A Florida County"] = {"connected": True, "file": "data/fake.json"}
    with pytest.raises(RegistryError, match="coverage mismatch"):
        load_florida_local_compat(make_manifest(tmp_path / "manifest.json", mutate))


def test_connected_county_requires_file(tmp_path):
    def mutate(manifest):
        manifest["counties"]["Indian River"].pop("file")
    with pytest.raises(RegistryError, match="has no file"):
        load_florida_local_compat(make_manifest(tmp_path / "manifest.json", mutate))


def test_unsafe_county_file_path_rejected(tmp_path):
    def mutate(manifest):
        manifest["counties"]["Indian River"]["file"] = "../outside.json"
    with pytest.raises(RegistryError, match="unsafe county data path"):
        load_florida_local_compat(make_manifest(tmp_path / "manifest.json", mutate))
