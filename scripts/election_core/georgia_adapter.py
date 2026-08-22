"""Georgia Election Night Reporting adapter scaffold.

Intentionally cannot be instantiated while GA is disabled in the jurisdiction
registry. This gives us the production adapter shape without activating Georgia.
Network/source parsing is injected so fixtures can be proven before live enablement.
"""
from __future__ import annotations
from typing import Any, Callable
from .state_adapter import ElectionContext, StateElectionAdapter

PayloadLoader = Callable[[str, ElectionContext], dict[str, Any]]


class GeorgiaElectionAdapter(StateElectionAdapter):
    def __init__(self, context: ElectionContext, loader: PayloadLoader) -> None:
        if context.state.upper() != "GA":
            raise ValueError("GeorgiaElectionAdapter only supports GA")
        super().__init__(context)
        self.loader = loader

    def source_metadata(self) -> dict[str, str]:
        return {
            "authority": "Georgia Secretary of State",
            "system": "Election Night Reporting",
            "results": "https://results.sos.ga.gov/results/public/Georgia/elections",
        }

    def _collect(self, scope: str) -> dict[str, Any]:
        payload = self.loader(scope, self.context)
        if not isinstance(payload, dict):
            raise RuntimeError(f"Georgia loader returned invalid {scope} payload")
        if payload.get("state") not in (None, "GA"):
            raise RuntimeError("Georgia loader returned another state's payload")
        payload.setdefault("state", "GA")
        payload.setdefault("scope", scope)
        return payload

    def collect_statewide(self) -> dict[str, Any]:
        return self._collect("statewide")

    def collect_congressional(self) -> dict[str, Any]:
        return self._collect("congressional")

    def collect_legislative(self) -> dict[str, Any]:
        return self._collect("legislative")

    def collect_local(self) -> dict[str, Any]:
        return self._collect("local")
