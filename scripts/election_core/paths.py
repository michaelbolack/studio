"""Resolve Election Center data paths from the jurisdiction registry.

Disabled jurisdictions cannot resolve live feeds. State adapters may use different
physical files while the frontend consumes the same logical scope names.
"""
from __future__ import annotations
from pathlib import PurePosixPath
from .registry import RegistryError, get_jurisdiction

VALID_SCOPES = {"statewide", "congressional", "legislative", "local"}


def resolve_data_path(code: str, scope: str) -> str:
    jurisdiction = get_jurisdiction(code, require_enabled=True)
    key = scope.strip().lower()
    if key not in VALID_SCOPES:
        raise RegistryError(f"unsupported election scope: {key}")
    scopes = jurisdiction.get("scopes", {})
    path = scopes.get(key)
    if not path:
        raise RegistryError(f"scope is not configured for {jurisdiction['id']}: {key}")
    normalized = PurePosixPath(path)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise RegistryError(f"unsafe data path for {jurisdiction['id']}: {key}")
    return normalized.as_posix()


def resolve_manifest_path(code: str) -> str:
    jurisdiction = get_jurisdiction(code, require_enabled=True)
    path = jurisdiction.get("manifest")
    if not path:
        raise RegistryError(f"manifest is not configured for {jurisdiction['id']}")
    normalized = PurePosixPath(path)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise RegistryError(f"unsafe manifest path for {jurisdiction['id']}")
    return normalized.as_posix()
