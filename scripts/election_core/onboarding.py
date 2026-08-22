"""Validation for research-only state onboarding profiles.

Onboarding profiles document official sources and activation requirements. Loading a
profile never enables a jurisdiction or registers an adapter.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from .registry import RegistryError, get_jurisdiction

DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "data" / "state-onboarding"
REQUIRED_CAPABILITIES = (
    "statewideResults",
    "congressionalResults",
    "legislativeResults",
    "resultsByLocality",
)


def onboarding_path(state: str, root: Path | str = DEFAULT_ROOT) -> Path:
    code = state.strip().upper()
    get_jurisdiction(code)
    return Path(root) / f"{code.lower()}.json"


def _official_https(url: Any, field: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise RegistryError(f"onboarding source is missing: {field}")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise RegistryError(f"onboarding source must be https: {field}")
    return url


def load_onboarding_profile(state: str, root: Path | str = DEFAULT_ROOT) -> dict[str, Any]:
    code = state.strip().upper()
    jurisdiction = get_jurisdiction(code)
    path = onboarding_path(code, root)
    if not path.is_file():
        raise RegistryError(f"state onboarding profile missing: {code}")
    data = json.loads(path.read_text())
    if data.get("state") != code:
        raise RegistryError(f"onboarding state mismatch: expected {code}")
    if data.get("enabled") is not False or data.get("status") != "research-only":
        raise RegistryError("onboarding profiles must remain research-only and disabled")
    if jurisdiction.get("enabled"):
        raise RegistryError(f"research-only onboarding profile cannot target enabled jurisdiction: {code}")
    if not data.get("authority"):
        raise RegistryError("onboarding authority is required")
    sources = data.get("officialSources")
    if not isinstance(sources, dict) or not sources:
        raise RegistryError("onboarding officialSources are required")
    for field, url in sources.items():
        _official_https(url, field)
    expected = data.get("expectedLocalJurisdictions")
    if not isinstance(expected, int) or expected <= 0:
        raise RegistryError("expectedLocalJurisdictions must be a positive integer")
    capabilities = data.get("observedCapabilities")
    if not isinstance(capabilities, dict):
        raise RegistryError("observedCapabilities are required")
    missing = [key for key in REQUIRED_CAPABILITIES if capabilities.get(key) is not True]
    if missing:
        raise RegistryError("onboarding missing required observed capabilities: " + ", ".join(missing))
    requirements = data.get("activationRequirements")
    if not isinstance(requirements, list) or not requirements:
        raise RegistryError("activationRequirements are required")
    return data
