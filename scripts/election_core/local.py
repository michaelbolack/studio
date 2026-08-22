"""Local jurisdiction primitives for national Election Center expansion."""
from __future__ import annotations
from dataclasses import dataclass
import re

VALID_LOCAL_TYPES = {
    "county", "parish", "borough", "census-area", "independent-city",
    "municipality", "ward", "district", "other"
}

@dataclass(frozen=True)
class LocalJurisdiction:
    state: str
    name: str
    local_type: str = "county"
    fips: str | None = None
    slug: str | None = None

    def __post_init__(self) -> None:
        state = self.state.strip().upper()
        name = self.name.strip()
        if len(state) != 2:
            raise ValueError("state must be a two-character postal code")
        if not name:
            raise ValueError("local jurisdiction name is required")
        if self.local_type not in VALID_LOCAL_TYPES:
            raise ValueError(f"unsupported local jurisdiction type: {self.local_type}")
        if self.fips is not None and (len(self.fips) != 5 or not self.fips.isdigit()):
            raise ValueError("local jurisdiction FIPS must be five digits")
        slug = self.slug or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if not slug:
            raise ValueError("local jurisdiction slug is required")
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "slug", slug)

    @property
    def id(self) -> str:
        return f"{self.state}-{self.fips or self.slug}"

    def as_json(self) -> dict:
        data = {"id": self.id, "state": self.state, "name": self.name,
                "type": self.local_type, "slug": self.slug}
        if self.fips is not None:
            data["fips"] = self.fips
        return data


def index_local_jurisdictions(items: list[LocalJurisdiction]) -> dict[str, dict]:
    indexed = {}
    seen_fips = set()
    for item in items:
        if item.id in indexed:
            raise ValueError(f"duplicate local jurisdiction id: {item.id}")
        if item.fips and item.fips in seen_fips:
            raise ValueError(f"duplicate local jurisdiction FIPS: {item.fips}")
        indexed[item.id] = item.as_json()
        if item.fips:
            seen_fips.add(item.fips)
    return indexed
