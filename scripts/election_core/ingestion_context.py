"""Election metadata context for pre-activation ingestion.

Unlike StateElectionAdapter's ElectionContext, this context may be used while a
jurisdiction is still disabled. It validates that the jurisdiction exists but does
not authorize publication or adapter instantiation.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from .registry import get_jurisdiction


class ElectionMetadata(Protocol):
    state: str
    election_key: str
    name: str
    date: str


@dataclass(frozen=True)
class IngestionContext:
    state: str
    election_key: str
    name: str
    date: str

    def __post_init__(self) -> None:
        code = self.state.strip().upper()
        get_jurisdiction(code, require_enabled=False)
        if not self.election_key.strip():
            raise ValueError("election_key is required")
        if not self.name.strip():
            raise ValueError("election name is required")
        if not self.date.strip():
            raise ValueError("election date is required")
        object.__setattr__(self, "state", code)
