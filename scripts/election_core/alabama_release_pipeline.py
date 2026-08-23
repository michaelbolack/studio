"""Collect AlabamaVotes output and prepare/write all four scopes as one release."""
from __future__ import annotations
from typing import Any
from .alabama_pipeline import normalize_transport
from .alabama_transport import AlabamaVotesTransport
from .state_feed_release import prepare_state_release, write_state_release


def collect_alabama_release(transport: AlabamaVotesTransport) -> dict[str, dict[str, Any]]:
    payloads=normalize_transport(transport)
    required={"statewide","congressional","legislative","local"}
    if set(payloads)!=required:
        raise RuntimeError("Alabama collector must produce all four scopes")
    return payloads


def prepare_alabama_release(transport: AlabamaVotesTransport, *, evidence: dict[str, dict[str,bool]]) -> dict[str,dict[str,Any]]:
    return prepare_state_release(state="AL",payloads=collect_alabama_release(transport),evidence=evidence)


def write_alabama_release(transport: AlabamaVotesTransport, *, evidence: dict[str, dict[str,bool]]) -> dict[str,str]:
    return write_state_release(state="AL",payloads=collect_alabama_release(transport),evidence=evidence)
