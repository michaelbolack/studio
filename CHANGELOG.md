# IRC Media Election Center — Working Changelog

This is a high-level production checkpoint. Git history remains the authoritative implementation record.

## 2026-10-05 — General Election voter hub deployed

- Deployed release commit `a3b4c253d75401d38d86c8baa67e6c5cdc2273bb` through pull requests #50 and #51.
- Added a prominent November 3, 2026 Election Day countdown with Eastern-time state transitions.
- Added a modern voter action center using official Florida and county election resources.
- Added all 67 Florida counties with Indian River County pinned first and selected by default.
- Added direct Indian River registration, vote-by-mail, early-voting, precinct, sample-ballot, and election-office actions.
- Added verified original-source Florida statewide and national poll cards with methodology metadata and relevance ordering.
- Added honest empty and unavailable states; stale, incomplete, and source-unavailable polling is not silently substituted.
- Preserved the Florida county map, completed-primary result views, national polling, prediction markets, and results navigation.
- Added voter-information, polling, UI, module, and CI validation gates.
- Verified the live GitHub Pages application and its public Wix Election Center location.
- Confirmed this repository remains separate from `michaelbolack/IRC-Publishing-Suite`.
- Hardened runtime polling readiness/freshness, automatic countdown refresh, safe voter links, statewide guidance rendering, and view-aware navigation after final code review.

## Earlier Election Center foundation

- Connected all 67 Florida counties for the completed 2026 Primary snapshot.
- Added statewide and district result aggregation, county map views, prediction-market snapshots, integrity checks, and election-readiness reporting.
