import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.mississippi_pipeline import normalize_certified_results,normalize_provisional_county_results
from election_core.mississippi_district_safety import validate_mississippi_district_source
ROWS=[{"scope":"congressional","title":"US House District 1","district":"1","complete":True,"candidates":[{"name":"A","votes":10},{"name":"B","votes":8}]}]

def test_certified_and_provisional_pipelines_remain_distinct():
    certified=normalize_certified_results(ROWS)["congressional"]["contests"][0]
    provisional=normalize_provisional_county_results(ROWS,county_name="Hinds",county_fips="28049")["congressional"]["contests"][0]
    assert certified["certified"] is True and certified["publishableAsCertified"] is True
    assert provisional["certified"] is False and provisional["publishableAsCertified"] is False

def test_split_district_rejects_county_aggregation():
    members=[{"fips":"28049","membership":"partial"},{"fips":"28121","membership":"whole"}]
    with pytest.raises(ValueError,match="split Mississippi district"):
        validate_mississippi_district_source(district_type="congressional",district=2,members=members,result_source="provisional-county")
    assert validate_mississippi_district_source(district_type="congressional",district=2,members=members,result_source="certified-district")["safe"] is True
