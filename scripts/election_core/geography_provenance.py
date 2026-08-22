"""Research-only district geography source provenance validation."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from .registry import RegistryError, get_jurisdiction

DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "data" / "state-onboarding"
REQUIRED_GA_2026 = {
    "congressional": ("120th Congress", "cd120"),
    "stateSenate": ("2026 State Legislative Districts", "sldu"),
    "stateHouse": ("2026 State Legislative Districts", "sldl"),
}


def load_research_geography_sources(state: str, root: Path | str = DEFAULT_ROOT) -> dict[str, Any]:
    code = state.strip().upper()
    jurisdiction = get_jurisdiction(code)
    if jurisdiction.get("enabled"):
        raise RegistryError(f"research geography provenance cannot target enabled jurisdiction: {code}")
    path = Path(root) / f"{code.lower()}-geography-sources.json"
    if not path.is_file():
        raise RegistryError(f"research geography source profile missing: {code}")
    data = json.loads(path.read_text())
    if data.get("state") != code or data.get("status") != "research-only" or data.get("enabled") is not False:
        raise RegistryError(f"invalid research geography source profile: {code}")
    if data.get("electionCycle") != 2026:
        raise RegistryError(f"research geography source cycle must be 2026: {code}")
    sources = data.get("sources")
    if not isinstance(sources, dict):
        raise RegistryError("research geography sources are required")
    if code == "GA":
        for key, (vintage, layer) in REQUIRED_GA_2026.items():
            item = sources.get(key)
            if not isinstance(item, dict):
                raise RegistryError(f"Georgia geography source missing: {key}")
            if item.get("vintage") != vintage or item.get("layer") != layer or item.get("effectiveCycle") != 2026:
                raise RegistryError(f"Georgia geography source uses wrong 2026 vintage: {key}")
            url = item.get("url")
            parsed = urlparse(url) if isinstance(url, str) else None
            if parsed is None or parsed.scheme != "https" or not parsed.netloc:
                raise RegistryError(f"Georgia geography source URL must be https: {key}")
    return data
