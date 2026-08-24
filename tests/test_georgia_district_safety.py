import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.georgia_district_safety import georgia_district_safety_evidence
SCOPES=("statewide","congressional","legislative","local")

def base(scope):
    r={"title":scope,"candidates":[{"name":"A","votes":1}]}
    if scope in {"congressional","legislative"}: r.update({"district":"1","resultScope":"official-district"})
    return r

def test_official_district_results_pass():
    grouped={s:[base(s)] for s in SCOPES}
    assert all(georgia_district_safety_evidence(grouped).values())

def test_whole_county_reconstruction_cannot_pass_congressional():
    grouped={s:[base(s)] for s in SCOPES}; grouped["congressional"][0]["resultScope"]="whole-county"
    e=georgia_district_safety_evidence(grouped)
    assert e["congressional"] is False and e["statewide"] is True

def test_missing_district_identity_fails_closed():
    grouped={s:[base(s)] for s in SCOPES}; grouped["legislative"][0].pop("district")
    assert georgia_district_safety_evidence(grouped)["legislative"] is False

def test_precinct_scoped_district_result_is_accepted():
    grouped={s:[base(s)] for s in SCOPES}; grouped["legislative"][0]["resultScope"]="official-precinct"
    assert georgia_district_safety_evidence(grouped)["legislative"] is True
