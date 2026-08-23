"""Alabama congressional/legislative district safety.

District totals must come from official district-scoped results or official
precinct/reporting-unit data. Whole-county aggregation is rejected when any
county is split by the district.
"""
from __future__ import annotations
from typing import Any


def validate_alabama_district_source(*, district_type: str, district: str | int, members: list[dict[str, Any]], result_source: str) -> dict[str, Any]:
    if district_type not in {"congressional", "state_senate", "state_house"}:
        raise ValueError("unsupported Alabama district type")
    if not str(district).strip() or not members:
        raise ValueError("district and geography membership are required")
    seen=set(); partial=[]
    for row in members:
        fips=str(row.get("fips", "")).strip()
        membership=row.get("membership")
        if len(fips)!=5 or not fips.startswith("01") or not fips.isdigit():
            raise ValueError("invalid Alabama district county FIPS")
        if fips in seen: raise ValueError("duplicate district county")
        seen.add(fips)
        if membership not in {"whole","partial"}: raise ValueError("district membership must be whole or partial")
        if membership=="partial": partial.append(fips)
    allowed={"official-district","official-precinct","whole-county"}
    if result_source not in allowed: raise ValueError("unsupported Alabama district result source")
    if partial and result_source=="whole-county":
        raise ValueError("split Alabama district cannot use whole-county aggregation")
    return {"state":"AL","districtType":district_type,"district":str(district),"partialCounties":partial,"resultSource":result_source,"safe":True,"publishable":False}
