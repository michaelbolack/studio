"""Release all four state scopes as one validated unit.

A state is never left half-released: every scope must validate before any file is
written. This module intentionally accepts already-normalized collector payloads
and explicit per-scope evidence; state-specific collectors remain responsible for
source retrieval and reconciliation.
"""
from __future__ import annotations
from typing import Any
from .feed_release import release_scope_payload
from .generated_feed_writer import write_released_scope

SCOPES=("statewide","congressional","legislative","local")


def prepare_state_release(*,state:str,payloads:dict[str,dict[str,Any]],evidence:dict[str,dict[str,bool]])->dict[str,dict[str,Any]]:
    code=state.strip().upper()
    missing_payloads=[scope for scope in SCOPES if scope not in payloads]
    missing_evidence=[scope for scope in SCOPES if scope not in evidence]
    if missing_payloads or missing_evidence:
        raise RuntimeError(f"state release incomplete: payloads={missing_payloads}; evidence={missing_evidence}")
    released={}
    for scope in SCOPES:
        released[scope]=release_scope_payload(payloads[scope],state=code,scope=scope,evidence=evidence[scope])
    return released


def write_state_release(*,state:str,payloads:dict[str,dict[str,Any]],evidence:dict[str,dict[str,bool]])->dict[str,str]:
    """Validate every scope first, then write every released feed."""
    released=prepare_state_release(state=state,payloads=payloads,evidence=evidence)
    paths={}
    for scope in SCOPES:
        paths[scope]=str(write_released_scope(released[scope],state=state,scope=scope))
    return paths
