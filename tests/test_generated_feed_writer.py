import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.generated_feed_writer import write_released_scope,configured_scope_path


def test_writer_rejects_unconfigured_state_scope():
    with pytest.raises(RuntimeError,match="no configured"):
        configured_scope_path("GA","statewide")


def test_writer_rejects_nonpublishable_payload_before_path_lookup():
    payload={"state":"GA","scope":"statewide","publishable":False,"releaseEvidence":{"authoritativeSource":True}}
    with pytest.raises(RuntimeError,match="non-publishable"):
        write_released_scope(payload,state="GA",scope="statewide")


def test_writer_rejects_identity_mismatch():
    payload={"state":"AL","scope":"statewide","publishable":True,"releaseEvidence":{"authoritativeSource":True}}
    with pytest.raises(RuntimeError,match="identity mismatch"):
        write_released_scope(payload,state="GA",scope="statewide")


def test_writer_requires_positive_release_evidence():
    payload={"state":"GA","scope":"statewide","publishable":True,"releaseEvidence":{"coverageComplete":False}}
    with pytest.raises(RuntimeError,match="release evidence"):
        write_released_scope(payload,state="GA",scope="statewide")
