"""Mississippi release boundary.

Only certified-state payloads may enter the four-scope publishable release path.
Provisional county election-night payloads remain usable for clearly provisional
views, but cannot satisfy state activation feeds.
"""
from __future__ import annotations
from typing import Any
from .mississippi_pipeline import normalize_certified_results
from .state_feed_release import prepare_state_release,write_state_release

SCOPES={"statewide","congressional","legislative","local"}

def collect_mississippi_certified_release(rows:list[dict[str,Any]])->dict[str,dict[str,Any]]:
    payloads=normalize_certified_results(rows)
    if set(payloads)!=SCOPES:
        raise RuntimeError("Mississippi certified collector must produce all four scopes")
    for payload in payloads.values():
        if payload.get("sourceTier")!="certified-state":
            raise RuntimeError("Mississippi activation feeds require certified-state provenance")
        if any(c.get("certified") is not True for c in payload.get("contests",[])):
            raise RuntimeError("Mississippi activation feeds cannot contain provisional contests")
    return payloads

def prepare_mississippi_release(rows:list[dict[str,Any]],*,evidence:dict[str,dict[str,bool]])->dict[str,dict[str,Any]]:
    return prepare_state_release(state="MS",payloads=collect_mississippi_certified_release(rows),evidence=evidence)

def write_mississippi_release(rows:list[dict[str,Any]],*,evidence:dict[str,dict[str,bool]])->dict[str,str]:
    return write_state_release(state="MS",payloads=collect_mississippi_certified_release(rows),evidence=evidence)
