# Election Center Voter Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the approved modern Election Day countdown, 67-county Voter Action Center, and Indian River–prioritized polling experience to the existing Election Center without disrupting results, maps, prediction markets, or the Publishing Suite.

**Architecture:** Keep the existing static Election Center and its fail-closed Python validation model. Add one focused voter-information dataset, one testable browser module for countdown/county/poll presentation logic, and small additions to the existing `index.html`; extend the existing polling schema and validators rather than creating a second polling system.

**Tech Stack:** Static HTML/CSS/JavaScript, ES modules, JSON datasets, Python 3 validation scripts, Node built-in test runner, GitHub Actions, existing GitHub Pages/Wix embed workflow.

**Spec:** `docs/superpowers/specs/2026-10-05-election-center-voter-hub-design.md`

## Global Constraints

- Work only in `michaelbolack/studio`.
- Do not modify `michaelbolack/IRC-Publishing-Suite`, its deployment, or its memory files.
- Use no paid API.
- Preserve the existing county map, race listings, prediction markets, automated snapshots, and results behavior.
- Use official Florida Division of Elections and county Supervisor of Elections sources for voter information.
- Include exactly 67 Florida counties, with Indian River County first and the other 66 alphabetical.
- Use `America/New_York` for the November 3, 2026 countdown.
- Do not recreate or regenerate an IRC Media logo.
- Leave the four root repository-memory files unchanged until live Election Center verification succeeds.
- Fail closed on missing, malformed, duplicated, or unverified election information.

## Review Focus

- Daylight-saving and midnight boundaries must not make the countdown skip or duplicate a day; Task 3 pins this with fixed instants around November 3.
- Missing county-specific links must fall back to statewide guidance plus the verified county office instead of rendering dead controls; Tasks 1 and 3 test this.
- A county choice from an old session must be ignored when it is not one of the 67 validated counties; Task 3 tests this.
- Stale or partially described polls must never appear as current verified polls; Task 4 tests freshness and metadata status.
- A module/data fetch failure must leave the map, races, markets, and results usable; Task 5 tests the integration fallback.

---

## File Structure

**Create**

- `data/voter-information.json` — election metadata, verified statewide guidance, and all 67 county office/action links.
- `assets/election-voter-hub.mjs` — pure countdown, county ordering, voter-link fallback, and poll-priority functions plus browser initialization.
- `tests/election-voter-hub.test.mjs` — Node tests for the browser module's pure functions.
- `scripts/validate_voter_information.py` — fail-closed schema, county-count, uniqueness, date, source, and HTTPS validation.
- `scripts/test_voter_information.py` — Python unit tests for valid and invalid voter-information records.
- `scripts/validate_voter_hub_ui.py` — static integration checks for required markup, accessibility hooks, module loading, and fallback containers.
- `docs/superpowers/plans/2026-10-05-election-center-voter-hub.md` — this plan.

**Modify**

- `index.html` — approved countdown, voter cards, navigation, polling hierarchy, responsive styles, and non-destructive fallbacks.
- `data/polling.json` — current verified Indian River–relevant, Florida, and national polling records plus priority metadata.
- `data/polling-readiness.json` — source permissions, supported scopes, required metadata, and freshness gates.
- `scripts/validate_polling.py` — extended sponsor/publication/margin/scope/freshness and display-status checks.
- `scripts/validate_polling_ui.py` — new hierarchy and metadata rendering requirements.
- `.github/workflows/election-readiness-check.yml` — run voter-data, browser-module, and UI validation.
- `PROJECT_STATE.md`, `NEXT_TASK.md`, `ROADMAP.md`, `CHANGELOG.md` — replace Publishing Suite text only after successful live Election Center verification.

### Task 1: Voter-information contract and fail-closed validator

**Files:**
- Create: `data/voter-information.json`
- Create: `scripts/validate_voter_information.py`
- Create: `scripts/test_voter_information.py`

**Interfaces:**
- Produces: `validate_document(document: dict, today: date | None = None) -> list[str]`
- Produces dataset fields: `schemaVersion`, `generatedAt`, `election`, `statewide`, `counties`
- Each county produces: `id`, `name`, `officeName`, `officeUrl`, and optional `registrationUrl`, `voteByMailUrl`, `earlyVotingUrl`, `precinctUrl`, `sampleBallotUrl`, `contactUrl`

- [ ] **Step 1: Write failing Python tests**

Add tests named:

- `test_valid_document_has_67_unique_counties`
- `test_duplicate_county_fails`
- `test_missing_indian_river_fails`
- `test_missing_office_url_fails`
- `test_non_https_url_fails`
- `test_invalid_election_date_fails`
- `test_missing_statewide_source_fails`
- `test_optional_missing_action_link_is_allowed`

Assert exact error fragments and an empty error list for the valid fixture.

- [ ] **Step 2: Run tests and verify red**

Run: `python3 -m unittest scripts.test_voter_information -v`  
Expected: FAIL because `validate_voter_information` and `validate_document` do not exist.

- [ ] **Step 3: Implement the validator and minimal schema-valid fixture**

Implement `validate_document(document, today=None)` and a CLI `main()` that reads `data/voter-information.json`, prints a JSON report, and exits nonzero on errors. Seed the dataset with the election/statewide contract and 67 county identifiers; do not invent unverified action URLs.

- [ ] **Step 4: Run tests and validator**

Run: `python3 -m unittest scripts.test_voter_information -v`  
Expected: all tests PASS.

Run: `python3 scripts/validate_voter_information.py`  
Expected: PASS only after every required official county-office URL is populated in Task 2.

- [ ] **Step 5: Commit**

```bash
git add data/voter-information.json scripts/validate_voter_information.py scripts/test_voter_information.py
git commit -m "feat: add Florida voter information contract"
```

### Task 2: Populate and verify all statewide and county voter sources

**Files:**
- Modify: `data/voter-information.json`
- Modify: `scripts/test_voter_information.py`

**Interfaces:**
- Consumes: Task 1 dataset and `validate_document`
- Produces: verified 67-county dataset with Indian River local details and per-field official sources/verification dates

- [ ] **Step 1: Add failing source-completeness assertions**

Require exactly 67 counties; require every county `officeUrl`; require `Indian River` to provide every action URL; require statewide registration, ID, vote-by-mail, early-voting, and Election Day guidance to include `sourceUrl` and `verifiedAt`.

- [ ] **Step 2: Run tests and verify red**

Run: `python3 -m unittest scripts.test_voter_information -v`  
Expected: FAIL on incomplete sources.

- [ ] **Step 3: Research and populate official sources**

Use only Florida Division of Elections and official county Supervisor of Elections sites. Verify each destination resolves to the intended official office/tool. Store missing optional county actions as `null`, never guessed URLs. Give Indian River County full action coverage.

- [ ] **Step 4: Validate the completed dataset**

Run: `python3 -m unittest scripts.test_voter_information -v && python3 scripts/validate_voter_information.py`  
Expected: PASS; report shows 67 counties, 67 official office links, Indian River full coverage, and zero errors.

- [ ] **Step 5: Commit**

```bash
git add data/voter-information.json scripts/test_voter_information.py
git commit -m "data: add verified Florida voter resources"
```

### Task 3: Testable countdown, county, fallback, and polling-priority logic

**Files:**
- Create: `assets/election-voter-hub.mjs`
- Create: `tests/election-voter-hub.test.mjs`

**Interfaces:**
- Produces: `getCountdownState(now: Date, electionDate: string, timeZone: string) -> {state: 'countdown'|'election-day'|'results', days: number | null, label: string}`
- Produces: `orderCounties(counties: CountyRecord[], pinnedId: string) -> CountyRecord[]`
- Produces: `resolveVoterActions(statewide: StatewideRecord, county: CountyRecord) -> VoterAction[]`
- Produces: `pollPriority(poll: PollRecord, countyId: string) -> number`
- Produces: `sortPollsForCounty(polls: PollRecord[], countyId: string) -> PollRecord[]`
- Produces: `initVoterHub(options) -> Promise<void>`

- [ ] **Step 1: Write failing Node tests**

Cover:

- October 5, 2026 Eastern returns `countdown` with 29 days.
- November 3 Eastern returns `election-day`.
- November 4 Eastern returns `results`.
- DST/timezone boundary inputs do not skip a state.
- Indian River sorts first; remaining counties are alphabetical.
- Unknown stored county selection falls back to Indian River.
- Missing optional county action uses statewide/office fallback.
- Indian River–relevant polls sort ahead of Florida statewide, then national.
- Stable ordering keeps newest `endDate` first within the same priority.

- [ ] **Step 2: Run tests and verify red**

Run: `node --test tests/election-voter-hub.test.mjs`  
Expected: FAIL because module exports do not exist.

- [ ] **Step 3: Implement pure functions and guarded browser initialization**

Keep pure functions independent of the DOM. `initVoterHub` fetches `data/voter-information.json` and reuses already-loaded polling data when supplied; it must catch errors, mark the module unavailable, and leave unrelated page sections untouched.

- [ ] **Step 4: Run tests and verify green**

Run: `node --test tests/election-voter-hub.test.mjs`  
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add assets/election-voter-hub.mjs tests/election-voter-hub.test.mjs
git commit -m "feat: add Election Day and voter hub logic"
```

### Task 4: Upgrade polling metadata, priority, freshness, and current records

**Files:**
- Modify: `data/polling.json`
- Modify: `data/polling-readiness.json`
- Modify: `scripts/validate_polling.py`
- Modify: `scripts/validate_polling_ui.py`
- Modify: `tests/election-voter-hub.test.mjs`

**Interfaces:**
- Consumes: `sortPollsForCounty` from Task 3
- Poll records add: `scope: 'county-relevant'|'florida-statewide'|'national'`, `countyIds: string[]`, optional `sponsor`, optional `publicationDate`, optional `marginOfError`, and derived display status
- Produces validated current polling snapshot and clear current/older/incomplete states

- [ ] **Step 1: Extend failing polling validator tests/checks**

Require valid `scope`; county-relevant records require nonempty `countyIds`; dates cannot be future or reversed; current status requires the configured freshness window; optional margin must be numeric and nonnegative; primary-display records require the existing required fields and a permitted source.

- [ ] **Step 2: Run polling validations and verify red**

Run: `python3 scripts/validate_polling.py && python3 scripts/validate_polling_ui.py && node --test tests/election-voter-hub.test.mjs`  
Expected: FAIL until schema, records, and UI contract are updated.

- [ ] **Step 3: Curate current original-source polling**

Research current original pollster releases for Indian River–relevant districts, Florida statewide races, and major national races. Store only records with direct HTTPS releases and sufficient methodology. If no current poll exists for a priority level, render an honest empty state instead of substituting prediction-market data.

- [ ] **Step 4: Implement metadata validation and status labeling**

Extend `validate_poll` without weakening existing rights, source, duplicate, or freshness gates. Keep individual polls distinct from averages and preserve the existing disclosure.

- [ ] **Step 5: Run polling validations**

Run: `python3 scripts/validate_polling.py && python3 scripts/validate_polling_ui.py && node --test tests/election-voter-hub.test.mjs`  
Expected: PASS with current verified records or explicit validated empty states.

- [ ] **Step 6: Commit**

```bash
git add data/polling.json data/polling-readiness.json scripts/validate_polling.py scripts/validate_polling_ui.py tests/election-voter-hub.test.mjs
git commit -m "feat: prioritize verified Florida election polling"
```

### Task 5: Integrate the approved visual design into the Election Center

**Files:**
- Modify: `index.html`
- Create: `scripts/validate_voter_hub_ui.py`
- Modify: `assets/election-voter-hub.mjs`

**Interfaces:**
- Consumes: Task 2 dataset and Task 3/4 module functions/data
- Produces DOM hooks: `#election-countdown`, `#voter-information`, `#voter-county-select`, `#voter-actions`, `#latest-polls`, `#voter-hub-status`

- [ ] **Step 1: Write failing static UI validation**

Require the six DOM hooks, the module script, accessible labels, visible focus rules, reduced-motion rule, mobile stacking rules, approved countdown state strings, navigation links, and a voter-module error fallback. Assert that existing map, polling, prediction-market, and results anchors remain present.

- [ ] **Step 2: Run static validation and verify red**

Run: `python3 scripts/validate_voter_hub_ui.py`  
Expected: FAIL listing missing voter-hub markup and module tokens.

- [ ] **Step 3: Add approved markup and styling**

Insert the countdown immediately beneath the Election Center header, followed by Voter Action Center and Latest Polls. Match the approved mockup while following existing design tokens. Preserve current results view behavior and existing section IDs.

- [ ] **Step 4: Wire module initialization and guarded failure behavior**

Initialize after existing page data loads. A voter-data failure shows a compact status and official statewide fallback; it must not hide or clear map, races, polling, markets, or results.

- [ ] **Step 5: Run UI and module tests**

Run: `python3 scripts/validate_voter_hub_ui.py && node --test tests/election-voter-hub.test.mjs`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add index.html assets/election-voter-hub.mjs scripts/validate_voter_hub_ui.py
git commit -m "feat: add modern Election Center voter hub"
```

### Task 6: Add CI gates and run full regression

**Files:**
- Modify: `.github/workflows/election-readiness-check.yml`
- Modify only if required by failures: existing validators and tests

**Interfaces:**
- Consumes all Task 1–5 validators/tests
- Produces one CI gate that blocks invalid voter data or broken voter-hub presentation

- [ ] **Step 1: Add failing workflow/static assertion**

Add a small assertion in `scripts/validate_voter_hub_ui.py` that the readiness workflow invokes:

- `python3 -m unittest scripts.test_voter_information -v`
- `python3 scripts/validate_voter_information.py`
- `node --test tests/election-voter-hub.test.mjs`
- `python3 scripts/validate_voter_hub_ui.py`

- [ ] **Step 2: Run and verify red**

Run: `python3 scripts/validate_voter_hub_ui.py`  
Expected: FAIL until the workflow contains all commands.

- [ ] **Step 3: Update the readiness workflow**

Add Node setup only if the runner's existing Node is insufficient. Preserve every current readiness and integrity command.

- [ ] **Step 4: Run the complete local gate**

Run:

```bash
python3 -m unittest scripts.test_voter_information -v
python3 scripts/validate_voter_information.py
node --test tests/election-voter-hub.test.mjs
python3 scripts/validate_voter_hub_ui.py
python3 scripts/validate_polling.py
python3 scripts/validate_polling_ui.py
python3 scripts/validate_prediction_markets.py
python3 scripts/validate_prediction_markets_ui.py
python3 scripts/validate_florida_heatmap.py
python3 scripts/check_election_readiness.py
python3 scripts/final_integrity_gate.py
```

Expected: every command exits 0.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/election-readiness-check.yml scripts/validate_voter_hub_ui.py
git commit -m "ci: validate Election Center voter hub"
```

### Task 7: Deploy, verify the Wix embed, then correct repository memory

**Files:**
- Modify after successful live verification: `PROJECT_STATE.md`
- Modify after successful live verification: `NEXT_TASK.md`
- Modify after successful live verification: `ROADMAP.md`
- Modify after successful live verification: `CHANGELOG.md`

**Interfaces:**
- Consumes the fully verified Task 6 commit
- Produces a deployed Election Center checkpoint and accurate future-session memory

- [ ] **Step 1: Deploy using the existing Election Center workflow**

Do not use Publishing Suite deployment tooling. Record the exact deployed commit.

- [ ] **Step 2: Verify the live Wix Election Center embed on desktop**

Verify countdown value/state, Indian River first, 67-county selection, voter actions, poll ordering/metadata, map, races, markets, and results. Confirm no horizontal overflow or blocked navigation.

- [ ] **Step 3: Verify the live Wix Election Center embed at mobile width**

Verify 320px layout, stacked cards, full-width county selector, readable countdown, 44px-class touch targets, visible focus behavior, and no clipping.

- [ ] **Step 4: Verify failure states without disturbing production data**

Using local fixtures or safe request interception, verify voter-data failure leaves existing content visible and stale/incomplete polling is labeled or withheld.

- [ ] **Step 5: Replace the four incorrect memory-file contents**

Write Election Center-specific state, next task, roadmap, and changelog. Include the deployed commit, live URL/embed location, verified election date, voter-hub status, polling status, and explicit Publishing Suite separation.

- [ ] **Step 6: Run memory and regression verification**

Run the complete Task 6 gate again. Confirm the four memory files contain `Election Center` and do not identify the repository as the Publishing Suite.

- [ ] **Step 7: Commit and stop**

```bash
git add PROJECT_STATE.md NEXT_TASK.md ROADMAP.md CHANGELOG.md
git commit -m "docs: checkpoint Election Center voter hub"
```

Stop without beginning unrelated Election Center expansion, Wix redesign, Publishing Suite work, or paid-service integration.
