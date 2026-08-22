"""Per-state local jurisdiction index loading and validation."""
from __future__ import annotations
import json
from pathlib import Path
from .local import LocalJurisdiction, index_local_jurisdictions
from .registry import RegistryError, get_jurisdiction

DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "data" / "jurisdictions"


def local_index_path(state: str, root: Path | str = DEFAULT_ROOT) -> Path:
    code = state.strip().upper()
    get_jurisdiction(code, require_enabled=True)
    return Path(root) / code.lower() / "local.json"


def load_local_index(state: str, root: Path | str = DEFAULT_ROOT) -> dict:
    code = state.strip().upper()
    jurisdiction = get_jurisdiction(code, require_enabled=True)
    path = local_index_path(code, root)
    if not path.exists():
        raise RegistryError(f"local jurisdiction index is not configured for {code}")
    payload = json.loads(path.read_text())
    if payload.get("state") != code:
        raise RegistryError(f"local jurisdiction index state mismatch for {code}")
    raw = payload.get("jurisdictions")
    if not isinstance(raw, list) or not raw:
        raise RegistryError(f"local jurisdiction index is empty for {code}")
    items = [LocalJurisdiction(code, x["name"], x.get("type", jurisdiction.get("localJurisdictionType", "county")), x.get("fips"), x.get("slug")) for x in raw]
    indexed = index_local_jurisdictions(items)
    return {"schemaVersion": 1, "state": code, "count": len(indexed), "jurisdictions": list(indexed.values())}
