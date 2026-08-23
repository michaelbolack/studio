"""Normalize Mississippi results while preserving certification status."""
from __future__ import annotations
from typing import Any

def _votes(v:Any)->int:
    try:n=int(v)
    except (TypeError,ValueError) as e: raise ValueError("invalid candidate votes") from e
    if n<0: raise ValueError("negative candidate votes")
    return n

def normalize_mississippi_contest(raw:dict[str,Any],*,scope:str,source_tier:str)->dict[str,Any]:
    if scope not in {"statewide","congressional","legislative","local"}: raise ValueError("unsupported Mississippi scope")
    if source_tier not in {"certified-state","provisional-county"}: raise ValueError("unsupported Mississippi source tier")
    title=str(raw.get("title","")).strip()
    if not title: raise ValueError("contest title is required")
    candidates=[]
    for row in raw.get("candidates") or []:
        name=str(row.get("name","")).strip()
        if not name: raise ValueError("candidate name is required")
        candidates.append({"name":name,"party":str(row.get("party","")).strip() or None,"votes":_votes(row.get("votes"))})
    if not candidates: raise ValueError("contest candidates are required")
    complete=bool(raw.get("complete",False))
    certified=source_tier=="certified-state"
    # Provisional county data may display raw totals, but never masquerades as certified.
    leader=max(candidates,key=lambda x:x["votes"])["name"] if complete else None
    return {"state":"MS","scope":scope,"contest":title,"district":raw.get("district"),"candidates":candidates,"complete":complete,"leader":leader,"sourceTier":source_tier,"certified":certified,"status":"certified" if certified else "provisional","aggregateLeaderPublishable":complete,"publishableAsCertified":complete and certified,"sourceAuthority":"Mississippi Secretary of State" if certified else str(raw.get("sourceAuthority","")).strip()}

def normalize_mississippi_scope(rows:list[dict[str,Any]],*,scope:str,source_tier:str)->dict[str,Any]:
    contests=[normalize_mississippi_contest(x,scope=scope,source_tier=source_tier) for x in rows]
    return {"state":"MS","scope":scope,"sourceTier":source_tier,"status":"research-only","publishable":False,"contests":contests}
