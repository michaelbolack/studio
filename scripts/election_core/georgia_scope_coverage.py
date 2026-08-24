"""Coverage audit for Georgia generated election feeds.

Do not allow a state release to claim complete four-scope coverage merely because
an official ENR page parsed successfully.  Every required scope must contain at
least one contest, and every contest must report complete locality/precinct
coverage before the release evidence can mark coverage complete.
"""
from __future__ import annotations
from typing import Any

REQUIRED_SCOPES=("statewide","congressional","legislative","local")


def audit_georgia_scope_coverage(grouped:dict[str,list[dict[str,Any]]])->dict[str,Any]:
    failures=[]
    status={}
    for scope in REQUIRED_SCOPES:
        contests=grouped.get(scope)
        if not isinstance(contests,list) or not contests:
            failures.append(f"{scope}: no contests parsed")
            status[scope]={"complete":False,"contestCount":0}
            continue
        incomplete=[]
        for contest in contests:
            reporting=contest.get("reporting") or {}
            reported=reporting.get("reported")
            total=reporting.get("total")
            if not isinstance(reported,int) or not isinstance(total,int) or total<=0 or reported!=total:
                incomplete.append(str(contest.get("title") or "unnamed contest"))
        status[scope]={"complete":not incomplete,"contestCount":len(contests),"incomplete":incomplete}
        if incomplete:
            failures.append(f"{scope}: {len(incomplete)} contest(s) incomplete")
    return {"state":"GA","coverageComplete":not failures,"failures":failures,"scopes":status}
