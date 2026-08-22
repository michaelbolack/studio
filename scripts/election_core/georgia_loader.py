"""Georgia ENR loader boundary.

The fetcher is injected so transport/discovery can evolve independently from the
normalizer and can be tested without enabling Georgia or making network calls.
"""
from __future__ import annotations
from typing import Any, Callable
from .georgia_normalizer import normalize_georgia_scope
from .state_adapter import ElectionContext

Fetcher = Callable[[str, ElectionContext], list[dict[str, Any]]]


class GeorgiaENRLoader:
    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    def __call__(self, scope: str, context: ElectionContext) -> dict[str, Any]:
        raw = self.fetcher(scope, context)
        if not isinstance(raw, list):
            raise RuntimeError("Georgia ENR fetcher must return a contest list")
        result = normalize_georgia_scope(raw, scope=scope)
        result["election"] = {
            "key": context.election_key,
            "name": context.name,
            "date": context.date,
        }
        return result
