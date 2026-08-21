import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load(name):
    return json.loads((DATA / name).read_text())


def main():
    readiness = load("election-readiness.json")
    manifest = load("manifest.json")
    statewide = load("statewide.json")
    district9 = load("district-9.json")

    counties = manifest.get("counties", {})
    connected = sorted(name for name, entry in counties.items() if entry.get("connected") is True)
    disconnected = sorted(name for name, entry in counties.items() if entry.get("connected") is not True)

    checks = []
    checks.append({
        "id": "county-baseline",
        "passed": len(connected) == 67 and not disconnected,
        "detail": f"{len(connected)}/67 county-local feeds connected",
        "disconnected": disconnected,
    })
    checks.append({
        "id": "statewide-protection",
        "passed": statewide.get("schemaVersion") == 2
        and statewide.get("coverageComplete") is True
        and statewide.get("countiesIncluded") == 67,
        "detail": f"statewide {statewide.get('countiesIncluded')}/67",
    })
    checks.append({
        "id": "district9-protection",
        "passed": district9.get("schemaVersion") == 2
        and district9.get("coverageComplete") is True
        and district9.get("countiesIncluded") == 7,
        "detail": f"district 9 {district9.get('countiesIncluded')}/7",
    })

    clarity = next(g for g in readiness["collectorGroups"] if g["id"] == "clarity-browser-session")
    clarity_operational = clarity.get("collectorOperationalStatus") == "green"
    clarity_general_sources_ready = clarity.get("generalElectionSourceStatus") == "green"
    checks.append({
        "id": "clarity-collector-operational",
        "passed": clarity_operational,
        "detail": "browser-session collector proven with non-empty Martin, Osceola and Pinellas fixtures",
    })
    checks.append({
        "id": "clarity-general-sources",
        "passed": clarity_general_sources_ready,
        "detail": "2026 General Election IDs and source paths validated for Martin, Osceola and Pinellas",
    })

    live_enabled = readiness.get("livePublishingEnabled") is True
    critical_ready = all(check["passed"] for check in checks)
    activation_safe = critical_ready and live_enabled

    report = {
        "electionId": readiness.get("electionId"),
        "electionDate": readiness.get("electionDate"),
        "checks": checks,
        "criticalReady": critical_ready,
        "livePublishingEnabled": live_enabled,
        "activationSafe": activation_safe,
        "status": "ready" if activation_safe else "not-ready",
    }

    print(json.dumps(report, indent=2))

    # This checker is intentionally fail-closed for election-night activation.
    # Planning mode is allowed to report red/yellow gates without failing CI.
    if live_enabled and not activation_safe:
        raise SystemExit("Live publishing is enabled while one or more critical readiness gates are not green.")


if __name__ == "__main__":
    main()
