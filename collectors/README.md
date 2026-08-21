# Clarity browser-session collector

This collector is for public election-result sites that render correctly in a normal browser/network session but return empty or blocked responses to GitHub-hosted automation.

## Safety model

The collector is deliberately separated from publishing:

1. Browser session reads `current_ver.txt` from the official county result host.
2. It reads the version-pinned `json/en/summary.json` endpoint.
3. It validates only the basic Clarity structure and writes an atomic snapshot under `collector-staging/clarity/`.
4. It **does not** edit `data/*.json`, the county manifest, statewide data, District 9 data, or GitHub.
5. A separate election validator/publisher must approve the staged snapshot before production changes occur.

If a county fails, its previous production result remains untouched. Failure in Martin, Osceola or Pinellas must never block or overwrite statewide or other counties.

## Current test fixtures

The checked-in configuration contains the completed 2026 Primary election IDs only so the collector can be proven before November:

- Martin: `126768`
- Osceola: `126781`
- Pinellas: `126780`

These IDs must be replaced with the 2026 General Election IDs during Election Readiness source discovery. The readiness gate must stay red until the General Election IDs and live collection path have been tested.

## Running on a normal Mac or PC network

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r collectors/requirements.txt
playwright install chromium
python collectors/clarity_browser_collector.py --once
```

For election-night polling after readiness is green:

```bash
python collectors/clarity_browser_collector.py --interval 300
```

The default browser is visible/headful and uses a persistent profile directory. This is intentional because the county result hosts have already shown different behavior for normal browser sessions versus hosted GitHub runners.

## Election-night activation rules

Do not enable live publishing merely because this collector can fetch data. Before activation:

- update the collector config to the General Election IDs;
- confirm all three counties return non-empty structured JSON;
- validate candidate/race mapping against official statewide/district sources where applicable;
- make the `clarity-browser-session` readiness gate green;
- keep the five-minute publishing schedule disabled until the election-night window;
- maintain fail-closed behavior and last-known-good production data on any collector failure.
