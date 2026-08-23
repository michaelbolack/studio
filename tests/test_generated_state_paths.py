import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=json.loads((ROOT/"data"/"jurisdictions.json").read_text())


def test_ga_al_ms_have_four_generated_scope_paths_and_remain_disabled():
    for code in ("GA","AL","MS"):
        item=REGISTRY["states"][code]
        assert item["enabled"] is False
        assert set(item["scopes"])=={"statewide","congressional","legislative","local"}
        for scope,path in item["scopes"].items():
            assert path==f"data/states/{code.lower()}/{scope}.json"
        assert item["localJurisdictionType"]=="county"
        assert item["sourcePolicy"]["publishIncompleteAggregateLeaders"] is False


def test_florida_paths_are_unchanged():
    fl=REGISTRY["states"]["FL"]
    assert fl["enabled"] is True and fl["default"] is True
    assert fl["manifest"]=="data/manifest.json"
    assert fl["scopes"]["statewide"]=="data/statewide.json"
    assert fl["scopes"]["congressional"]=="data/congressional.json"
    assert fl["scopes"]["legislative"]=="data/legislative.json"
