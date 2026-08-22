import sys
from dataclasses import dataclass
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from election_core.georgia_transport import GeorgiaENRTransport
from election_core.georgia_loader import GeorgiaENRLoader


@dataclass(frozen=True)
class ContextFixture:
    state: str = "GA"
    election_key: str = "2026-runoff"
    name: str = "2026 Georgia General Primary Runoff"
    date: str = "2026-06-16"


PAGE = """## Secretary of State - Dem
Vote for 1
Candidate A
DEM
55.0% 550
Candidate B
DEM
45.0% 450
Localities reporting 159 / 159

## US House of Representatives - District 1 - Rep
Vote for 1
Candidate C
REP
60.0% 600
Candidate D
REP
40.0% 400
Localities reporting 15 / 15

## State Senate - District 2 - Dem
Vote for 1
Candidate E
DEM
52.0% 520
Candidate F
DEM
48.0% 480
Localities reporting 4 / 4
"""


def test_transport_parser_loader_pipeline():
    calls = []
    transport = GeorgiaENRTransport(
        "https://results.sos.ga.gov/results/public/Georgia/fixture",
        lambda url: calls.append(url) or PAGE,
    )
    loader = GeorgiaENRLoader(transport.fetch_scope)
    ctx = ContextFixture()

    statewide = loader("statewide", ctx)
    congressional = loader("congressional", ctx)
    legislative = loader("legislative", ctx)

    assert statewide["contests"][0]["leader"] == "Candidate A"
    assert congressional["contests"][0]["district"] == "1"
    assert legislative["contests"][0]["district"] == "2"
    assert all(x["publishable"] is False for x in (statewide, congressional, legislative))
    assert len(calls) == 1  # one official page fetch is safely reused across scopes


def test_transport_rejects_nonofficial_host():
    with pytest.raises(ValueError, match="official"):
        GeorgiaENRTransport("https://example.com/results", lambda url: PAGE)


def test_transport_rejects_http():
    with pytest.raises(ValueError, match="HTTPS"):
        GeorgiaENRTransport("http://results.sos.ga.gov/results", lambda url: PAGE)


def test_empty_official_response_fails_closed():
    transport = GeorgiaENRTransport(
        "https://results.sos.ga.gov/results/public/Georgia/fixture", lambda url: ""
    )
    with pytest.raises(RuntimeError, match="empty"):
        transport.fetch_grouped()
