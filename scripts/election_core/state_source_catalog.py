"""Validated source catalog for state election ingestion.

The catalog distinguishes a verified official endpoint from a source that is
actually eligible for publishable release. Unofficial election-night pages and
result indexes can be collected/researched but cannot satisfy release authority.
"""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "state-sources" / "2026.json"
ALLOWED_HOSTS = {
    "GA": {"results.sos.ga.gov"},
    "AL": {"alabamavotes.gov", "www.alabamavotes.gov", "www2.alabamavotes.gov"},
    "MS": {"sos.ms.gov", "www.sos.ms.gov"},
}


def load_source_catalog(path: Path | str = CATALOG_PATH) -> dict[str, Any]:
    data = json.loads(Path(path).read_text())
    if data.get("schemaVersion") != 1 or not isinstance(data.get("states"), dict):
        raise RuntimeError("invalid state source catalog")
    return data


def get_election_source(state: str, election_key: str, *, path: Path | str = CATALOG_PATH) -> dict[str, Any]:
    code = state.strip().upper()
    catalog = load_source_catalog(path)
    try:
        source = catalog["states"][code]["elections"][election_key]
    except KeyError as exc:
        raise RuntimeError(f"unknown election source: {code}/{election_key}") from exc
    url = source.get("resultsUrl")
    if not isinstance(url, str):
        raise RuntimeError("election source has no results URL")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS.get(code, set()):
        raise RuntimeError(f"unapproved official host for {code}")
    return dict(source)


def source_release_authority(state: str, election_key: str, *, path: Path | str = CATALOG_PATH) -> bool:
    source = get_election_source(state, election_key, path=path)
    return source.get("releaseEligible") is True and source.get("status") == "official"
