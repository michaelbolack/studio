"""State-agnostic Election Center ingestion primitives."""

from .districts import DistrictScope, ValidationResult, checksum_geographies, make_race_id
from .adapter import build_district_race

__all__ = [
    "DistrictScope",
    "ValidationResult",
    "checksum_geographies",
    "make_race_id",
    "build_district_race",
]
