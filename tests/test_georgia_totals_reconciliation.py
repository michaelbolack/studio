import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from election_core.georgia_totals_reconciliation import audit_georgia_totals,georgia_totals_evidence
SCOPES=("statewide","congressional","legislative","local")

def c(total=18,a=10,b=8): return {"title":"Race","totalVotes":total,"candidates":[{"name":"A","votes":a},{"name":"B","votes":b}]}

def test_matching_official_total_reconciles_every_scope():
    grouped={s:[c()] for s in SCOPES}
    assert audit_georgia_totals(grouped)["totalsReconciled"] is True
    assert all(georgia_totals_evidence(grouped).values())

def test_mismatched_candidate_sum_blocks_only_affected_scope():
    grouped={s:[c()] for s in SCOPES}; grouped["congressional"]=[c(total=19)]
    e=georgia_totals_evidence(grouped)
    assert e["congressional"] is False and e["statewide"] is True

def test_missing_independent_contest_total_fails_closed():
    grouped={s:[c()] for s in SCOPES}; grouped["local"][0].pop("totalVotes")
    assert georgia_totals_evidence(grouped)["local"] is False

def test_negative_or_non_integer_votes_fail_reconciliation():
    grouped={s:[c()] for s in SCOPES}; grouped["legislative"]=[c(a=-1)]
    assert georgia_totals_evidence(grouped)["legislative"] is False
