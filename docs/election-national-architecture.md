# Election Center national architecture

## Goal

Scale the Election Center from Florida to all U.S. states, DC, and territories without making Florida-specific assumptions part of the core system.

## Geographic model

The core hierarchy is:

`country -> state/territory -> jurisdiction -> district -> election -> race -> candidate -> result`

A county is one jurisdiction type, not the universal parent of every race. Congressional and legislative districts may cross county boundaries and must retain independent geographic scope.

## Compatibility rule

Florida remains the first enabled state and the existing `data/manifest.json` remains its county manifest during migration. Existing production paths and frontend behavior must continue working while the national registry is introduced.

## Registry

`data/jurisdictions.json` is the top-level registry. Each state or territory may declare its own manifest, statewide data, congressional data, legislative data, source policy, and local jurisdiction type.

## Data integrity

Accuracy outranks completeness. Aggregate leaders must not be published when required geographic coverage cannot be proven complete. Official state sources are preferred; official local sources may supplement them when appropriate.

## Expansion sequence

1. Stabilize Florida ingestion and current frontend.
2. Make collectors accept state/jurisdiction configuration instead of hard-coded Florida assumptions.
3. Add a second state with a materially different election-results system as an architecture test.
4. Expand federal/statewide/congressional coverage across states.
5. Expand county-equivalent and deep-local coverage incrementally.
6. Add DC and territories under the same jurisdiction model.

## UI principle

State selection, county-equivalent selection, and district selection are separate concepts. Selecting a map geography should synchronize the corresponding selector, but districtwide totals must never be reduced to one county's totals.
