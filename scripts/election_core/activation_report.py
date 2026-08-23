"""Summarize pre-activation readiness for nationally onboarded states."""
from __future__ import annotations
from typing import Iterable
from .activation_preflight import preflight_state_activation
from .adapter_factory import registered_adapter_codes


def national_activation_report(states: Iterable[str] = ("GA", "AL", "MS")) -> dict:
    registered = registered_adapter_codes()
    results = {code.upper(): preflight_state_activation(code, registered_adapters=registered) for code in states}
    return {
        "states": results,
        "activationReady": [code for code, item in results.items() if item["activationReady"]],
        "blocked": [code for code, item in results.items() if not item["activationReady"]],
    }
