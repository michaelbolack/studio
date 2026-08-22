"""State-agnostic Election Center ingestion primitives."""

from .districts import DistrictScope, ValidationResult, checksum_geographies, make_race_id
from .adapter import build_district_race
from .registry import RegistryError, default_jurisdiction, enabled_jurisdictions, get_jurisdiction, load_registry
from .paths import VALID_SCOPES, resolve_data_path, resolve_manifest_path

__all__ = [
    "DistrictScope",
    "ValidationResult",
    "checksum_geographies",
    "make_race_id",
    "build_district_race",
    "RegistryError",
    "load_registry",
    "get_jurisdiction",
    "enabled_jurisdictions",
    "default_jurisdiction",
    "VALID_SCOPES",
    "resolve_data_path",
    "resolve_manifest_path",
]
