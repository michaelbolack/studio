"""Guarded service entry point for national Election Center state bundles."""
from __future__ import annotations
from typing import Any
from .adapter_factory import create_state_adapter, registered_adapter_codes
from .state_adapter import ElectionContext
from .state_bundle import build_state_bundle


def supported_state_codes() -> tuple[str, ...]:
    """States with explicitly registered adapters.

    Registry enablement is still enforced when a bundle is built; this function is
    informational only and does not activate a state.
    """
    return registered_adapter_codes()


def build_enabled_state_bundle(context: ElectionContext) -> dict[str, Any]:
    """Build one state bundle only through the fail-closed adapter factory."""
    return build_state_bundle(create_state_adapter(context))
