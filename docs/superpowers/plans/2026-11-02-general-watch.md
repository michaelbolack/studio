# General Election Watch Implementation Plan

> Implement inline using executing-plans, with a fresh whole-branch review.

**Goal:** An Indian River and Florida General Election watch page that updates unattended from official sources.
**Architecture:** Separate General snapshot/collector/UI from the frozen Primary pipeline. Server collectors validate election identity and scope before publishing atomically; browser polls the snapshot without reloading or losing selection. Source errors retain the last verified snapshot and expose health separately.
**Stack:** Existing static HTML/ES modules, Python, GitHub Actions/Pages.
**Spec:** User-approved official-feed design in this conversation, November 2.

## Global Constraints
Preserve archive, all existing data, source permissions, and existing 67-county activation gates. Never activate that legacy pipeline with partial coverage. Scope the new independent watch feed to explicitly validated Indian River and state sources. No DDHQ ingestion. No Publishing Suite edits. No premature numbers or winner calls. Deployment approval remains required.

## Review Focus
Wrong election; local totals mistaken for statewide totals; stale snapshots; incomplete candidate rows; scheduled runs delayed or unavailable.

### Task 1: Verify live source contracts
- [x] Probe official state downloads and county links from GitHub runner; retain diagnostics as artifacts. Do not publish data.
- [x] Record actual General election URLs and sample payloads; stop unsupported adapters from activating.

### Task 2: Collect safely
- [x] Write failing Python tests for identity, scoped totals, partial data, zero-vote pending, malformed counts, stale time, and failed-source preservation.
- [x] Add scripts/collect_general_watch.py using observed official formats; output data/general-watch.json and separate health.
- [x] Add scheduled collector workflow with bounded election window, concurrency and atomic publication; run same exact path in dry-run CI.

### Task 3: Watch page
- [x] Write failing module tests for pending/live/delayed states and refresh without selection loss.
- [x] Add assets/general-watch.mjs and a prominent General section ahead of archive. Local/state tabs, counts, percentages, reporting when supplied, timestamps, official links. Pending means no fabricated zero results.
- [x] Preserve existing map and Primary totals under clear archive identification.

### Task 4: Verify and deliver
- [x] Run readiness and all scoped tests, failure fixtures and real runner dry-run.
- [x] Review whole branch, fix material findings, confirm mobile/desktop where controls permit.
- [x] Prepare review PR and report exactly which sources are operational. Request deployment approval only after reviewable result.

## Execution record
- Official sources verified by runs 41438612487 and 41439237092. Full collector dry run 41440197227 returned 60 records and both sources healthy.
- County source has October 27 nonzero values; release gating uses the source timestamp so these stay pending.
- Review fixes: treat health failures as delayed; retry snapshot publication over concurrent unrelated main updates; preserve General snapshots during legacy recovery; label archive clearly and route top race navigation to General views.
- Responsive preview used an actual 390px iframe viewport; content width equals viewport (375px excluding scrollbar).
- Broader Node suite retains unrelated existing letters-newsroom failure, 3 != 0.
- Deployment remains pending Mike's approval.
