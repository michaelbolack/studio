import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.mississippi_transport import MississippiCertifiedTransport,MississippiProvisionalTransport

def test_certified_transport_requires_sos_host():
    t=MississippiCertifiedTransport("https://www.sos.ms.gov/elections-voting/election-results",lambda u:"certified")
    assert t.fetch_text()=="certified"
    with pytest.raises(ValueError): MississippiCertifiedTransport("https://county.example/results",lambda u:"x")

def test_provisional_transport_requires_explicit_approved_county_host():
    t=MississippiProvisionalTransport("https://elections.examplecounty.gov/results",lambda u:"provisional",county_fips="28049",approved_hosts={"elections.examplecounty.gov"})
    assert t.fetch_text()=="provisional" and t.county_fips=="28049"

def test_unapproved_or_sos_provisional_host_fails_closed():
    with pytest.raises(ValueError): MississippiProvisionalTransport("https://other.example/results",lambda u:"x",county_fips="28049",approved_hosts={"county.example"})
    with pytest.raises(ValueError): MississippiProvisionalTransport("https://www.sos.ms.gov/results",lambda u:"x",county_fips="28049",approved_hosts={"www.sos.ms.gov"})

def test_http_and_bad_fips_fail_closed():
    with pytest.raises(ValueError): MississippiCertifiedTransport("http://www.sos.ms.gov/results",lambda u:"x")
    with pytest.raises(ValueError): MississippiProvisionalTransport("https://county.example/results",lambda u:"x",county_fips="12061",approved_hosts={"county.example"})
