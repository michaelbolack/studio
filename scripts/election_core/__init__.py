"""State-agnostic Election Center ingestion primitives."""

from .districts import DistrictScope, ValidationResult, checksum_geographies, make_race_id

__all__ = ["DistrictScope", "ValidationResult", "checksum_geographies", "make_race_id"]
