import json
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.state_source_catalog import get_election_source,source_release_authority


def test_verified_2026_state_sources_are_pinned_to_official_https_hosts():
    ga=get_election_source("GA","2026-general-primary")
    al=get_election_source("AL","2026-primary-runoff")
    ms=get_election_source("MS","2026-primary")
    assert ga["resultsUrl"].startswith("https://results.sos.ga.gov/")
    assert al["resultsUrl"].startswith("https://www2.alabamavotes.gov/")
    assert ms["resultsUrl"].startswith("https://www.sos.ms.gov/")


def test_only_explicit_official_result_source_satisfies_release_authority():
    assert source_release_authority("GA","2026-general-primary") is True
    assert source_release_authority("AL","2026-primary-runoff") is False
    assert source_release_authority("MS","2026-primary") is False


def test_unapproved_host_is_rejected(tmp_path):
    data={"schemaVersion":1,"states":{"GA":{"elections":{"bad":{"resultsUrl":"https://example.com/results","status":"official","releaseEligible":True}}}}}
    path=tmp_path/"sources.json"; path.write_text(json.dumps(data))
    with pytest.raises(RuntimeError,match="unapproved official host"):
        get_election_source("GA","bad",path=path)
