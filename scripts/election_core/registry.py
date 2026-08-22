"""Safe access to the Election Center national jurisdiction registry."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

DEFAULT_REGISTRY = Path(__file__).resolve().parents[2] / "data" / "jurisdictions.json"

class RegistryError(RuntimeError):
    pass

def load_registry(path: Path | str = DEFAULT_REGISTRY) -> dict[str, Any]:
    data = json.loads(Path(path).read_text())
    states = data.get("states")
    if not isinstance(states, dict) or not states:
        raise RegistryError("jurisdiction registry has no states")
    enabled = [code for code, item in states.items() if item.get("enabled")]
    defaults = [code for code, item in states.items() if item.get("default")]
    if len(defaults) != 1:
        raise RegistryError("jurisdiction registry must have exactly one default")
    if defaults[0] not in enabled:
        raise RegistryError("default jurisdiction must be enabled")
    return data

def get_jurisdiction(code: str, *, require_enabled: bool = False, path: Path | str = DEFAULT_REGISTRY) -> dict[str, Any]:
    data = load_registry(path)
    key = code.strip().upper()
    try:
        item = data["states"][key]
    except KeyError as exc:
        raise RegistryError(f"unknown jurisdiction: {key}") from exc
    if require_enabled and not item.get("enabled"):
        raise RegistryError(f"jurisdiction is not enabled: {key}")
    return {"id": key, **item}

def enabled_jurisdictions(path: Path | str = DEFAULT_REGISTRY) -> list[dict[str, Any]]:
    data = load_registry(path)
    return [{"id": code, **item} for code, item in data["states"].items() if item.get("enabled")]

def default_jurisdiction(path: Path | str = DEFAULT_REGISTRY) -> dict[str, Any]:
    data = load_registry(path)
    code = next(code for code, item in data["states"].items() if item.get("default"))
    return {"id": code, **data["states"][code]}
