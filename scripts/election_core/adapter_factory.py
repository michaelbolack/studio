"""State adapter registry and factory for the national Election Center core."""
from __future__ import annotations
from typing import Type
from .florida_adapter import FloridaElectionAdapter
from .georgia_live_adapter import GeorgiaLiveAdapter
from .alabama_live_adapter import AlabamaLiveAdapter
from .mississippi_live_adapter import MississippiLiveAdapter
from .registry import RegistryError, get_jurisdiction
from .state_adapter import ElectionContext, StateElectionAdapter

ADAPTERS: dict[str, Type[StateElectionAdapter]] = {
    "FL": FloridaElectionAdapter,
    "GA": GeorgiaLiveAdapter,
    "AL": AlabamaLiveAdapter,
    "MS": MississippiLiveAdapter,
}


def registered_adapter_codes() -> tuple[str, ...]:
    return tuple(sorted(ADAPTERS))


def create_state_adapter(context: ElectionContext) -> StateElectionAdapter:
    """Return the adapter for an enabled state or fail closed.

    Registration is a prerequisite, not activation. The jurisdiction must still
    be explicitly enabled in data/jurisdictions.json before an adapter can be
    instantiated.
    """
    code = context.state.strip().upper()
    get_jurisdiction(code, require_enabled=True)
    adapter_class = ADAPTERS.get(code)
    if adapter_class is None:
        raise RegistryError(f"enabled jurisdiction has no registered adapter: {code}")
    return adapter_class(context)
