import json
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import election_core.generated_scope_adapter as module
from election_core.generated_scope_adapter import GeneratedScopeStateAdapter


class Stub(GeneratedScopeStateAdapter):
    expected_state="GA"
    authority="Official"
    system="Stub"


def adapter(tmp_path):
    a=object.__new__(Stub)
    a.context=type("C",(),{"state":"GA"})()
    a.jurisdiction={"scopes":{"statewide":"data/states/ga/statewide.json"}}
    module.REPO_ROOT=tmp_path
    return a


def write(tmp_path,payload):
    path=tmp_path/"data/states/ga/statewide.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload))


def test_publishable_matching_scope_loads(tmp_path):
    a=adapter(tmp_path)
    payload={"state":"GA","scope":"statewide","publishable":True,"contests":[]}
    write(tmp_path,payload)
    assert a.collect_statewide()==payload


def test_missing_or_nonpublishable_feed_fails_closed(tmp_path):
    a=adapter(tmp_path)
    with pytest.raises(RuntimeError,match="missing"): a.collect_statewide()
    write(tmp_path,{"state":"GA","scope":"statewide","publishable":False})
    with pytest.raises(RuntimeError,match="not publishable"): a.collect_statewide()


def test_state_and_scope_mismatch_fail_closed(tmp_path):
    a=adapter(tmp_path)
    write(tmp_path,{"state":"AL","scope":"statewide","publishable":True})
    with pytest.raises(RuntimeError,match="state mismatch"): a.collect_statewide()
    write(tmp_path,{"state":"GA","scope":"local","publishable":True})
    with pytest.raises(RuntimeError,match="scope mismatch"): a.collect_statewide()


def test_unconfigured_scope_fails_closed(tmp_path):
    a=adapter(tmp_path)
    with pytest.raises(RuntimeError,match="no configured congressional"): a.collect_congressional()
