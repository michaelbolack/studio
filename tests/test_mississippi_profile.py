import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_mississippi_profile_is_research_only_and_82_counties():
    p=json.loads((ROOT/"data"/"state-onboarding"/"ms.json").read_text())
    assert p["state"]=="MS"
    assert p["enabled"] is False
    assert p["status"]=="research-only"
    assert p["expectedLocalJurisdictions"]==82
    assert p["authority"]=="Mississippi Secretary of State"
    assert p["officialSources"]["resultsIndex"].startswith("https://www.sos.ms.gov/")
    assert p["sourcePolicy"]["publishIncompleteAggregateLeader"] is False
    assert p["sourcePolicy"]["countyElectionNightResults"]=="provisional-only"
