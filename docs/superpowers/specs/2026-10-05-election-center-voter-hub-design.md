# Election Center Pre-Election Voter Hub — Design Specification

**Date:** 2026-10-05  
**Repository:** `michaelbolack/studio`  
**Status:** Approved design; implementation not yet started  
**Target election:** Florida General Election — November 3, 2026

## 1. Purpose

Transform the existing IRC Media Election Center into a useful pre-election destination that helps Florida voters quickly answer three questions:

1. How long remains until Election Day?
2. What do I need to know and do to vote in my county?
3. What do current, properly sourced polls show about races relevant to me?

The update must preserve the existing Florida map, race listings, polling collector, prediction markets, automated snapshots, and results architecture.

## 2. Product Priorities

Before Election Day, the page hierarchy is:

1. Election Center header and section navigation.
2. Modern Election Day countdown.
3. Voter Action Center.
4. Latest Polls.
5. Florida county map and race information.
6. Prediction Markets.
7. Election results.

On Election Day, voter information remains prominent while results coverage becomes the primary downstream destination. After Election Day, the countdown becomes a results-coverage banner.

## 3. Approved Visual Direction

Use the approved dark, modern social-video-inspired design:

- navy and midnight-blue surfaces;
- restrained red and blue glow;
- strong contrast and large, readable typography;
- rounded but professional cards;
- mobile-first stacking;
- minimal animation that does not distract from voter information;
- no recreated or AI-generated IRC Media logo.

The countdown is a full-width feature banner directly beneath the Election Center header.

### Countdown states

Before November 3:

> **29 DAYS**  
> **UNTIL ELECTION DAY**  
> **NOVEMBER 3, 2026**

The number updates automatically once per calendar day using the `America/New_York` timezone and displays whole days only.

On November 3:

> **ELECTION DAY IS HERE**

After November 3:

> **RESULTS COVERAGE**

The design must honor `prefers-reduced-motion`.

## 4. Navigation

The Election Center section navigation will expose:

- Election Home
- Voter Information
- Latest Polls
- County Races
- Prediction Markets
- Results

Existing page views and sections must remain reachable. Navigation changes should use the current single-page view pattern rather than introduce a new application framework.

## 5. Voter Action Center

### County selector

- Include all 67 Florida counties.
- Pin **Indian River County** first.
- List the remaining counties alphabetically.
- Default to Indian River County for a new visitor.
- Preserve the current county selection during the browser session.
- Selecting a county updates county-specific links and information without reloading the page.

### Statewide information

Statewide information must be sourced from the Florida Division of Elections and include:

- registration status and official lookup;
- statewide registration deadline;
- identification requirements;
- vote-by-mail rules and statewide guidance;
- Election Day date and general polling-hours guidance;
- official Florida voter-information link.

Time-sensitive facts must include a source label and last-verified date.

### County-specific information

Each county record must include, when officially available:

- county Supervisor of Elections name;
- official election-office website;
- registration lookup or voter portal;
- vote-by-mail request/status link;
- early-voting information;
- Election Day precinct lookup;
- sample-ballot link;
- official contact or office-information link.

Indian River County may display richer local details, but all counties must provide at least the official county election-office link and Florida statewide guidance.

### Hybrid presentation

Show critical dates and rules directly on the Election Center. Use clear official-action buttons for personalized or frequently changing information:

- Check Registration
- Vote-by-Mail Tools
- Early Voting Information
- Find My Precinct
- View Sample Ballot
- County Election Office

Links to external official tools must open clearly and must not imply that IRC Media operates those tools.

### Missing-data behavior

If county-specific information is unavailable or fails validation:

- do not display a broken or guessed link;
- retain statewide guidance;
- display the county's verified official election-office link;
- label unavailable details honestly.

## 6. Latest Polls

Reuse the existing polling collector, polling data, monitoring, and validation scripts.

### Display priority

1. Races relevant to Indian River County.
2. Florida statewide races.
3. Major national races and congressional-control polling.

A race is Indian River–relevant when the selected county participates in that district or jurisdiction. The first release must correctly prioritize Indian River County. The design must allow other selected counties to receive the same treatment when district mapping is available.

### Required poll metadata

A poll card must display:

- race or question;
- pollster;
- sponsor or commissioner when available;
- field dates;
- publication date when available;
- sample size;
- population type, such as likely voters or registered voters;
- margin of error when reported;
- candidate or answer percentages;
- direct source link;
- collection or last-updated time.

Polls and prediction markets must remain visually and editorially distinct.

### Data-quality states

Poll status must be explicit:

- **Current** — required metadata present and within the configured freshness window.
- **Older poll** — valid but outside the freshness window.
- **Incomplete metadata** — may be withheld from the primary display.
- **Source unavailable** — retain the last verified snapshot only if clearly labeled.

The UI must not invent missing margins, samples, sponsors, dates, or topline values.

### Trend presentation

Where multiple compatible polls exist for the same race:

- show the newest poll first;
- provide a compact trend view;
- do not represent a single poll as a polling average;
- label any calculated average with its methodology.

## 7. Data Model

Add a dedicated voter-information dataset separate from election results.

Recommended structure:

```text
data/
  voter-information.json
  polling.json
  prediction-markets.json
```

`voter-information.json` contains:

- election metadata;
- statewide rules, dates, sources, and verification timestamp;
- 67 county records;
- official URLs;
- optional local details;
- validation status.

Do not place frequently changing voter information directly inside presentation markup when it can be loaded from the dataset.

## 8. Reliability and Validation

Add validation that fails when:

- the county count is not exactly 67;
- county names are duplicated;
- Indian River County is missing;
- an official county-office URL is missing;
- URLs are malformed or use an unexpected insecure scheme;
- election dates are invalid;
- statewide source attribution is missing;
- required poll metadata is missing from primary-display records;
- poll field dates are logically invalid;
- duplicate poll records are produced.

Existing Election Center validation must continue to run.

No paid data API is required for this project.

## 9. Accessibility and Responsive Behavior

- Countdown text must remain readable at 320px width.
- Voter cards stack to one column on narrow screens.
- County selector becomes full width on mobile.
- All buttons and selectors must be keyboard accessible.
- Interactive controls require visible focus states.
- Color cannot be the only indicator of party, poll status, or selection.
- External links require clear accessible names.
- Text contrast must meet WCAG AA expectations.
- Motion must be reduced or removed when the user requests reduced motion.

## 10. Error Handling

- A voter-information load failure must not remove existing race, map, polling, or results content.
- A polling refresh failure must preserve the last verified polling snapshot with a timestamp and warning.
- A county record failure must fall back to statewide information and the county's official office link.
- Countdown calculation must use a fixed election date and explicit timezone.
- Errors should be visible but compact; the page must never appear blank because one module failed.

## 11. Repository Boundaries

This work applies only to the Election Center repository:

`michaelbolack/studio`

It must not modify:

- `michaelbolack/IRC-Publishing-Suite`;
- Publishing Suite source code;
- Publishing Suite memory files;
- Publishing Suite production deployment.

The four root memory files currently in `michaelbolack/studio` contain Publishing Suite information. Leave them untouched during feature implementation. After the Election Center update is implemented, tested, deployed, and verified, replace their contents with an accurate Election Center checkpoint.

## 12. Verification

Implementation is complete only when:

- the modern countdown displays the correct whole-day value;
- countdown state transitions are tested before, on, and after November 3;
- Indian River County appears first;
- all other counties are alphabetized;
- exactly 67 counties validate;
- every county has a verified official election-office link;
- changing counties updates the voter-action links;
- voter information remains usable on mobile;
- Indian River–relevant polls appear before statewide and national polls;
- poll cards display required metadata;
- polls and prediction markets are clearly distinguished;
- existing county map, races, prediction markets, snapshots, and results still work;
- existing and new validation scripts pass;
- the Wix Election Center embed is visually verified on desktop and mobile;
- the Publishing Suite repository and deployment remain unchanged.

## 13. Deployment and Stop Condition

After implementation:

1. run the complete Election Center validation suite;
2. deploy through the existing Election Center workflow;
3. verify the live Wix embed on desktop and mobile;
4. update the Election Center repository-memory files;
5. commit the verified checkpoint;
6. stop.

Do not begin unrelated Election Center expansion, Publishing Suite work, Wix redesign work, or new paid-service integration as part of this project.
