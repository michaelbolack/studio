"""Require district-scoped Georgia results for congressional/legislative races."""
from __future__ import annotations
from typing import Any

SCOPES=("statewide","congressional","legislative","local")
DISTRICT_SCOPES={"congressional","legislative"}
SAFE_DISTRICT_SOURCES={"official-district","official-precinct"}


def audit_georgia_district_safety(grouped:dict[str,list[dict[str,Any]]])->dict[str,Any]:
    scopes={}; failures=[]
    for scope in SCOPES:
        contests=grouped.get(scope) or []
        unsafe=[]
        if scope in DISTRICT_SCOPES:
            for contest in contests:
                district=str(contest.get("district") or "").strip()
                source_scope=str(contest.get("resultScope") or "").strip()
                if not district or source_scope not in SAFE_DISTRICT_SOURCES:
                    unsafe.append(str(contest.get("title") or "unnamed contest"))
        # Statewide/local contests do not require district reconstruction proof;
        # their source/coverage checks are enforced elsewhere.
        passed=bool(contests) and not unsafe
        scopes[scope]={"passed":passed,"unsafe":unsafe,"contestCount":len(contests)}
        if not passed: failures.append(f"{scope}: district safety not proven")
    return {"state":"GA","districtSafetyPassed":not failures,"failures":failures,"scopes":scopes}


def georgia_district_safety_evidence(grouped:dict[str,list[dict[str,Any]]])->dict[str,bool]:
    audit=audit_georgia_district_safety(grouped)
    return {scope:audit["scopes"][scope]["passed"] for scope in SCOPES}
