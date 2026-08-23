"""Georgia pre-activation collection and state-feed release pipeline."""
from __future__ import annotations
from typing import Callable
from .georgia_loader import GeorgiaENRLoader
from .georgia_transport import GeorgiaENRTransport
from .ingestion_context import IngestionContext
from .state_feed_release import SCOPES, prepare_state_release, write_state_release

TextGetter = Callable[[str], str]


def collect_georgia_payloads(*, election_url: str, get_text: TextGetter, context: IngestionContext) -> dict[str, dict]:
    if context.state != "GA":
        raise ValueError("Georgia release pipeline requires GA ingestion context")
    transport = GeorgiaENRTransport(election_url, get_text)
    loader = GeorgiaENRLoader(transport.fetch_scope)
    return {scope: loader(scope, context) for scope in SCOPES}


def prepare_georgia_release(*, election_url: str, get_text: TextGetter, context: IngestionContext, evidence: dict[str, dict[str, bool]]) -> dict[str, dict]:
    payloads = collect_georgia_payloads(election_url=election_url, get_text=get_text, context=context)
    return prepare_state_release(state="GA", payloads=payloads, evidence=evidence)


def write_georgia_release(*, election_url: str, get_text: TextGetter, context: IngestionContext, evidence: dict[str, dict[str, bool]]) -> dict[str, str]:
    payloads = collect_georgia_payloads(election_url=election_url, get_text=get_text, context=context)
    return write_state_release(state="GA", payloads=payloads, evidence=evidence)
