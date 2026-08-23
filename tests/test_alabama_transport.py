import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.alabama_transport import AlabamaVotesTransport


def test_official_https_host_is_accepted_and_cached():
    calls=[]
    t=AlabamaVotesTransport("https://www2.alabamavotes.gov/electionNight/statewideResultsByContest.aspx?ecode=1",lambda u:calls.append(u) or "results")
    assert t.fetch_text()=="results"; assert t.fetch_text()=="results"; assert len(calls)==1


def test_nonofficial_host_is_rejected():
    with pytest.raises(ValueError,match="official"):
        AlabamaVotesTransport("https://example.com/results",lambda u:"x")


def test_http_is_rejected():
    with pytest.raises(ValueError,match="HTTPS"):
        AlabamaVotesTransport("http://www2.alabamavotes.gov/results",lambda u:"x")


def test_empty_response_fails_closed():
    t=AlabamaVotesTransport("https://www2.alabamavotes.gov/results",lambda u:"")
    with pytest.raises(RuntimeError,match="empty"): t.fetch_text()
