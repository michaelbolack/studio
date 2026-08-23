"""End-to-end AlabamaVotes county-page normalization pipeline."""
from __future__ import annotations
from .alabama_parser import parse_alabama_county_text
from .alabama_normalizer import normalize_alabama_scope
from .alabama_transport import AlabamaVotesTransport


def normalize_transport(transport: AlabamaVotesTransport) -> dict[str, dict]:
    parsed=parse_alabama_county_text(transport.fetch_text())
    # Alabama county pages expose Boxes Reported as a percentage rather than
    # numerator/denominator. Preserve that source semantics as 0..100 units.
    reported=int(round(parsed["boxesReportedPercent"]*1000))
    total=100000
    if parsed["complete"]:
        reported=total
    grouped={s:[] for s in ("statewide","congressional","legislative","local")}
    for contest in parsed["contests"]:
        scope=contest["scope"]
        row={"title":contest["title"],"district":contest.get("district"),"reporting":{"reported":reported,"total":total},"candidates":contest["candidates"]}
        grouped[scope].append(row)
    return {scope:normalize_alabama_scope(rows,scope=scope) for scope,rows in grouped.items()}
