"""Read-only bridge from Florida's existing county manifest into the national core.

This module does not fetch, repair, rewrite, or publish county results. The existing
Florida recovery workflow remains authoritative. This bridge only validates and
indexes the county files that workflow already produced.
"""
from __future__ import annotations
import json
from pathlib import Path, PurePosixPath
from .local_index import load_local_index
from .registry import RegistryError

DEFAULT_MANIFEST = Path(__file__).resolve().parents[2] / "data" / "manifest.json"


def _safe_repo_path(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise RegistryError(f"unsafe county data path: {value}")
    return path.as_posix()


def load_florida_local_compat(manifest_path: Path | str = DEFAULT_MANIFEST) -> dict:
    expected = load_local_index("FL")["jurisdictions"]
    expected_by_name = {item["name"]: item for item in expected}
    manifest = json.loads(Path(manifest_path).read_text())
    counties = manifest.get("counties")
    if not isinstance(counties, dict):
        raise RegistryError("Florida county manifest has no counties map")

    missing = sorted(set(expected_by_name) - set(counties))
    unexpected = sorted(set(counties) - set(expected_by_name))
    if missing or unexpected:
        raise RegistryError(f"Florida county manifest coverage mismatch: missing={missing}; unexpected={unexpected}")

    items = []
    disconnected = []
    for name in expected_by_name:
        source = counties[name]
        if not source.get("connected"):
            disconnected.append(name)
            continue
        file_path = source.get("file")
        if not file_path:
            raise RegistryError(f"connected Florida county has no file: {name}")
        jurisdiction = expected_by_name[name]
        items.append({
            "id": jurisdiction["id"],
            "state": "FL",
            "name": name,
            "type": "county",
            "fips": jurisdiction["fips"],
            "slug": jurisdiction["slug"],
            "file": _safe_repo_path(file_path),
            "sourceUrl": source.get("sourceUrl"),
            "adapter": source.get("adapter"),
            "races": source.get("races"),
        })

    return {
        "schemaVersion": 1,
        "state": "FL",
        "scope": "local",
        "generatedAt": manifest.get("generatedAt"),
        "expected": len(expected),
        "connected": len(items),
        "coverageComplete": not disconnected and len(items) == len(expected),
        "disconnected": disconnected,
        "jurisdictions": items,
    }
