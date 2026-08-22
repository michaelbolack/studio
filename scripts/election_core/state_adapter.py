"""Contract for state-specific election source adapters.

The national core owns validation and output shape. Individual states only provide
source discovery/fetch behavior. Disabled states cannot instantiate an adapter.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from .registry import get_jurisdiction


@dataclass(frozen=True)
class ElectionContext:
    state: str
    election_key: str
    name: str
    date: str

    def __post_init__(self) -> None:
        code = self.state.strip().upper()
        get_jurisdiction(code, require_enabled=True)
        if not self.election_key.strip():
            raise ValueError("election_key is required")
        if not self.name.strip():
            raise ValueError("election name is required")
        if not self.date.strip():
            raise ValueError("election date is required")
        object.__setattr__(self, "state", code)


class StateElectionAdapter(ABC):
    """Minimum interface every state source implementation must satisfy."""

    def __init__(self, context: ElectionContext) -> None:
        self.context = context
        self.jurisdiction = get_jurisdiction(context.state, require_enabled=True)

    @property
    def state(self) -> str:
        return self.context.state

    @abstractmethod
    def source_metadata(self) -> dict[str, str]:
        """Return authority and source URL metadata."""

    @abstractmethod
    def collect_statewide(self) -> dict[str, Any]:
        """Collect statewide races in normalized national-core shape."""

    @abstractmethod
    def collect_congressional(self) -> dict[str, Any]:
        """Collect U.S. House races in normalized national-core shape."""

    def collect_legislative(self) -> dict[str, Any]:
        raise NotImplementedError(f"legislative collection is not implemented for {self.state}")

    def collect_local(self) -> dict[str, Any]:
        raise NotImplementedError(f"local collection is not implemented for {self.state}")
