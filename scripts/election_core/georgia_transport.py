"""Georgia official ENR transport boundary.

HTTP is injected deliberately: production may use requests/urllib while tests use
captured official-page text. Only the pinned Georgia SOS HTTPS host is accepted.
"""
from __future__ import annotations
from typing import Callable
from urllib.parse import urlparse
from .georgia_enr_parser import parse_enr_contests
from .ingestion_context import ElectionMetadata

TextGetter = Callable[[str], str]
ALLOWED_HOST = "results.sos.ga.gov"


class GeorgiaENRTransport:
    def __init__(self, election_url: str, get_text: TextGetter) -> None:
        parsed = urlparse(election_url)
        if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
            raise ValueError("Georgia ENR URL must use official results.sos.ga.gov HTTPS host")
        self.election_url = election_url
        self.get_text = get_text
        self._cache: dict[str, list[dict]] | None = None

    def fetch_grouped(self) -> dict[str, list[dict]]:
        if self._cache is None:
            text = self.get_text(self.election_url)
            if not isinstance(text, str) or not text.strip():
                raise RuntimeError("Georgia ENR returned empty rendered text")
            self._cache = parse_enr_contests(text)
        return self._cache

    def fetch_scope(self, scope: str, context: ElectionMetadata) -> list[dict]:
        if context.state != "GA":
            raise ValueError("Georgia ENR transport only supports GA")
        grouped = self.fetch_grouped()
        if scope not in grouped:
            raise ValueError(f"unsupported Georgia scope: {scope}")
        return grouped[scope]
