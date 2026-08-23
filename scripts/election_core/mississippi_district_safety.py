"""Prevent unsafe whole-county reconstruction of Mississippi districts."""
from __future__ import annotations
from typing import Any

def validate_mississippi_district_source(*,district_type:str,district:str|int,members:list[dict[str,Any]],result_source:str)->dict[str,Any]:
    if district_type not in {"congressional","state_senate","state_house"}: raise ValueError("unsupported Mississippi district type")
    if not str(district).strip() or not members: raise ValueError("district geography required")
    partial=[]; seen=set()
    for row in members:
        fips=str(row.get("fips","")).strip(); membership=row.get("membership")
        if len(fips)!=5 or not fips.startswith("28") or not fips.isdigit(): raise ValueError("invalid Mississippi county FIPS")
        if fips in seen: raise ValueError("duplicate district county")
        seen.add(fips)
        if membership not in {"whole","partial"}: raise ValueError("membership must be whole or partial")
        if membership=="partial": partial.append(fips)
    if result_source not in {"certified-district","official-precinct","provisional-county","whole-county"}: raise ValueError("unsupported result source")
    if partial and result_source in {"provisional-county","whole-county"}: raise ValueError("split Mississippi district requires district or precinct scoped results")
    return {"state":"MS","districtType":district_type,"district":str(district),"partialCounties":partial,"resultSource":result_source,"safe":True,"publishable":False}
