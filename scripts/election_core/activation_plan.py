"""Plan activation for completed states without changing registry state.

This is deliberately read-only: every requested state must pass the existing
feed/adaptor preflight before a later registry mutation is permitted.
"""
from __future__ import annotations
from pathlib import Path
from typing import Iterable,Any
from .activation_preflight import preflight_state_activation
from .adapter_factory import registered_adapter_codes


def plan_state_activations(states:Iterable[str],*,repo_root:Path|None=None)->dict[str,Any]:
    codes=[]
    for state in states:
        code=state.strip().upper()
        if code not in codes: codes.append(code)
    if not codes: raise ValueError("at least one state is required")
    adapters=registered_adapter_codes()
    results={code:preflight_state_activation(code,registered_adapters=adapters,repo_root=repo_root) for code in codes}
    ready=[code for code,r in results.items() if r["activationReady"]]
    blocked=[code for code,r in results.items() if not r["activationReady"]]
    return {"states":results,"ready":ready,"blocked":blocked,"allReady":not blocked,"registryMutationAuthorized":not blocked}
