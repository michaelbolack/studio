# IRC Media Election Center — Project State

Last updated: 2026-10-05

## Canonical Repository

- Repository: `michaelbolack/studio`
- Purpose: canonical source for the IRC Media Election Center.
- The IRC Media Publishing Suite is a separate application in `michaelbolack/IRC-Publishing-Suite`; do not place its application code or deployment work here.

## Verified Production

- Public page: `https://www.ircmedia.net/election-center`
- Embedded application: `https://michaelbolack.github.io/studio/?v=4`
- Verified production release commit: `3599020c598d104086f27f24a5dc853d2d965cb5`
- Release pull request: `michaelbolack/studio#50`
- GitHub Election Readiness workflow passed for release head `18c326aef8eccf6df8a63bfc7fc1aead63e63d4f`.
- Live GitHub Pages content was verified on 2026-10-05 after deployment.

## Current Election Center Experience

- Election Day: November 3, 2026.
- Countdown uses America/New_York calendar days and transitions to Election Day and results states at Eastern midnight.
- The voter hub presents official registration, early-voting, Election Day, county-office, precinct, vote-by-mail, and sample-ballot resources.
- All 67 Florida counties are available. Indian River County is pinned first and is the default selection.
- Current verified Florida statewide polls appear before national indicators; original releases, field dates, population, sample size, sponsor, and margin are shown when reported.
- No current verified Indian River County-relevant poll was available at the 2026-10-05 checkpoint, and the interface says so rather than substituting stale or unrelated data.
- Existing county map, county and statewide primary results, national polling, prediction markets, and results navigation remain available.

## Data Readiness

- Completed 2026 Primary results remain frozen and connected across all 67 counties.
- The General Election results pipeline is intentionally not marked ready yet: verified General Election result sources are not connected for all counties.
- Do not weaken readiness gates or present unavailable General Election results as live.

## Verification Notes

- Voter-information, polling, prediction-market, map, UI, module, and integrity gates passed before deployment.
- Desktop live checks confirmed no horizontal overflow, usable navigation, six Indian River voter actions, correct poll ordering, and preserved legacy Election Center sections.
- A 320px responsive contract is enforced in the repository CSS and CI: stacked cards, full-width county selection, 52px controls, visible focus styling, and reduced-motion handling.
- Failure fixtures confirmed voter-data outages leave existing results visible and incomplete or unavailable polls are withheld.

## Session Rule

Read this file and `NEXT_TASK.md` first. Do not start new features, deployment changes, or data-source expansion without an explicit task.
