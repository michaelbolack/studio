"""Parser boundaries for Mississippi's two result tiers.

Actual format-specific extractors can feed these validators without ever losing
certification provenance.
"""
from __future__ import annotations
from typing import Any

SCOPES={"statewide","congressional","legislative","local"}

def _validate_rows(rows:list[dict[str,Any]],*,source_tier:str,source_authority:str)->list[dict[str,Any]]:
    if not isinstance(rows,list) or not rows: raise ValueError("Mississippi parser requires contest rows")
    out=[]
    for raw in rows:
        scope=str(raw.get("scope","")).strip()
        title=str(raw.get("title","")).strip()
        if scope not in SCOPES or not title: raise ValueError("invalid Mississippi parsed contest")
        candidates=raw.get("candidates") or []
        if not candidates: raise ValueError("parsed contest requires candidates")
        out.append({"scope":scope,"title":title,"district":raw.get("district"),"complete":bool(raw.get("complete",False)),"candidates":candidates,"sourceTier":source_tier,"sourceAuthority":source_authority})
    return out

def parse_certified_rows(rows:list[dict[str,Any]])->list[dict[str,Any]]:
    return _validate_rows(rows,source_tier="certified-state",source_authority="Mississippi Secretary of State")

def parse_provisional_county_rows(rows:list[dict[str,Any]],*,county_name:str,county_fips:str)->list[dict[str,Any]]:
    name=county_name.strip()
    if not name or len(county_fips)!=5 or not county_fips.startswith("28") or not county_fips.isdigit(): raise ValueError("valid Mississippi county identity required")
    parsed=_validate_rows(rows,source_tier="provisional-county",source_authority=f"{name} County election authority")
    for row in parsed:
        row["county"]=name; row["countyFips"]=county_fips; row["jurisdictionId"]=f"MS-{county_fips}"
    return parsed
