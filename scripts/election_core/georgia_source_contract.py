"""Validate the pinned Georgia Election Night Reporting research contract."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .registry import RegistryError, get_jurisdiction

REQUIRED_CAPABILITIES = {
    "statewideContests", "congressionalContests", "stateSenateContests",
    "stateHouseContests", "countyBreakouts", "reportingStatus",
}


def load_georgia_source_contract(path: Path | str) -> dict[str, Any]:
    if get_jurisdiction("GA").get("enabled"):
        raise RegistryError("Georgia research source contract must be replaced by production configuration after activation")
    payload = json.loads(Path(path).read_text())
    if payload.get("state") != "GA" or payload.get("status") != "research-only" or payload.get("publishable") is not False:
        raise RegistryError("Georgia source contract must remain research-only and non-publishable")
    if payload.get("authority") != "Georgia Secretary of State Elections Division":
        raise RegistryError("Georgia source authority is not pinned to the Secretary of State")
    root = payload.get("resultsRoot", "")
    if not root.startswith("https://results.sos.ga.gov/"):
        raise RegistryError("Georgia results root must use official HTTPS results.sos.ga.gov")
    caps = payload.get("observedCapabilities")
    if not isinstance(caps, dict) or any(caps.get(key) is not True for key in REQUIRED_CAPABILITIES):
        raise RegistryError("Georgia official results source is missing a required capability")
    rules = payload.get("coverageRules")
    if not isinstance(rules, dict) or rules.get("statewideExpectedLocalities") != 159:
        raise RegistryError("Georgia statewide coverage must require 159 localities")
    if rules.get("requireCompleteLocalitiesBeforeAggregateLeader") is not True:
        raise RegistryError("Georgia aggregate leaders must fail closed on incomplete locality coverage")
    if rules.get("requireOfficialAggregateChecksum") is not True:
        raise RegistryError("Georgia aggregate totals must checksum against official totals")
    if rules.get("allowWholeCountyReconstructionForSplitDistricts") is not False:
        raise RegistryError("Georgia split districts cannot be reconstructed from whole counties")
    return payload
