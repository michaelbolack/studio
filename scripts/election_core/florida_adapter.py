"""Compatibility adapter for Florida's existing v2 collectors.

This wrapper deliberately delegates to the collectors that already work. It does
not replace their parsing or result logic; it only exposes them through the common
national StateElectionAdapter contract.
"""
from __future__ import annotations
from importlib import import_module
from typing import Any
from .state_adapter import ElectionContext, StateElectionAdapter
from .florida_local_compat import load_florida_local_compat


class FloridaElectionAdapter(StateElectionAdapter):
    def __init__(self, context: ElectionContext) -> None:
        if context.state.upper() != "FL":
            raise ValueError("FloridaElectionAdapter only supports FL")
        super().__init__(context)

    def source_metadata(self) -> dict[str, str]:
        return {
            "authority": "Florida Department of State / Division of Elections",
            "system": "Florida Election Watch",
        }

    @staticmethod
    def _build(module_name: str) -> dict[str, Any]:
        module = import_module(module_name)
        build = getattr(module, "build", None)
        if not callable(build):
            raise RuntimeError(f"existing collector has no build() entry point: {module_name}")
        payload = build()
        if not isinstance(payload, dict):
            raise RuntimeError(f"existing collector returned invalid payload: {module_name}")
        return payload

    def collect_statewide(self) -> dict[str, Any]:
        return self._build("statewide_ingestion_v2")

    def collect_congressional(self) -> dict[str, Any]:
        return self._build("congressional_ingestion_v2")

    def collect_legislative(self) -> dict[str, Any]:
        return self._build("florida_legislative_ingestion_v2")

    def collect_local(self) -> dict[str, Any]:
        # Read-only compatibility bridge. The existing update/recovery workflow
        # remains responsible for producing and validating county files.
        return load_florida_local_compat()
