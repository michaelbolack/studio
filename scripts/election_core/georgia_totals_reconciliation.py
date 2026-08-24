"""Reconcile Georgia contest totals before release."""
from __future__ import annotations
from typing import Any
from .georgia_scope_coverage import REQUIRED_SCOPES


def _int(value:Any)->int|None:
    return value if isinstance(value,int) and not isinstance(value,bool) and value>=0 else None


def audit_georgia_totals(grouped:dict[str,list[dict[str,Any]]])->dict[str,Any]:
    scopes={}; failures=[]
    for scope in REQUIRED_SCOPES:
        contests=grouped.get(scope) or []
        bad=[]
        for contest in contests:
            candidate_sum=0; valid=True
            candidates=contest.get("candidates") or []
            if not candidates: valid=False
            for candidate in candidates:
                votes=_int(candidate.get("votes"))
                if votes is None: valid=False; break
                candidate_sum+=votes
            reported_total=_int(contest.get("totalVotes"))
            # If the official parser exposes a contest total, it must exactly equal
            # the sum of candidate vote totals.  Absence of that independent total
            # is not evidence of reconciliation and therefore fails closed.
            if reported_total is None or not valid or candidate_sum!=reported_total:
                bad.append(str(contest.get("title") or "unnamed contest"))
        scopes[scope]={"reconciled":bool(contests) and not bad,"contestCount":len(contests),"failed":bad}
        if not scopes[scope]["reconciled"]: failures.append(f"{scope}: totals not reconciled")
    return {"state":"GA","totalsReconciled":not failures,"failures":failures,"scopes":scopes}


def georgia_totals_evidence(grouped:dict[str,list[dict[str,Any]]])->dict[str,bool]:
    audit=audit_georgia_totals(grouped)
    return {scope:audit["scopes"][scope]["reconciled"] for scope in REQUIRED_SCOPES}
