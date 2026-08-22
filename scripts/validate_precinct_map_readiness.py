#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest_path = ROOT / "data" / "precinct-map-readiness.json"
data = json.loads(manifest_path.read_text())

errors = []
if data.get("pilotCounty") != "Indian River":
    errors.append("pilotCounty must be Indian River")
if data.get("expectedPrecincts") != 36:
    errors.append("expectedPrecincts must be 36")
geometry = data.get("geometry") or {}
results = data.get("results") or {}
activation = data.get("activation") or {}

for label, section in (("geometry", geometry), ("results", results)):
    if section.get("validated") is True:
        rel = section.get("path")
        if not rel or not (ROOT / rel).is_file():
            errors.append(f"{label} is marked validated but its file is missing")

ready = geometry.get("validated") is True and results.get("validated") is True
if activation.get("ready") is not ready:
    errors.append("activation.ready does not match validated source gates")
if activation.get("publish") is True and not ready:
    errors.append("publish cannot be enabled before both source gates pass")

print("Indian River precinct-map readiness")
print(f"  Expected precincts: {data.get('expectedPrecincts')}")
print(f"  Geometry validated: {geometry.get('validated') is True}")
print(f"  Results validated: {results.get('validated') is True}")
print(f"  Activation ready: {activation.get('ready') is True}")
print(f"  Publishing enabled: {activation.get('publish') is True}")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Precinct-map readiness gate passed.")
