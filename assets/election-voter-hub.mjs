const DAY_MS = 86_400_000;
const DEFAULT_COUNTY_ID = 'indian-river';
const COUNTY_STORAGE_KEY = 'irc-election-county';
const DEFAULT_ELECTION = {date: '2026-11-03', timeZone: 'America/New_York'};

const ACTIONS = [
  ['registration', 'Check Registration', 'registrationUrl'],
  ['vote-by-mail', 'Vote-by-Mail Tools', 'voteByMailUrl'],
  ['early-voting', 'Early Voting Information', 'earlyVotingUrl'],
  ['precinct', 'Find My Precinct', 'precinctUrl'],
  ['sample-ballot', 'View Sample Ballot', 'sampleBallotUrl'],
  ['county-office', 'County Election Office', 'officeUrl'],
];


function isoDateOrdinal(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value));
  if (!match) throw new TypeError('electionDate must use ISO YYYY-MM-DD');
  const [, year, month, day] = match.map(Number);
  const ordinal = Date.UTC(year, month - 1, day);
  const parsed = new Date(ordinal);
  if (
    parsed.getUTCFullYear() !== year
    || parsed.getUTCMonth() !== month - 1
    || parsed.getUTCDate() !== day
  ) throw new TypeError('electionDate must be a real calendar date');
  return ordinal;
}


function zonedDateOrdinal(now, timeZone) {
  if (!(now instanceof Date) || Number.isNaN(now.getTime())) {
    throw new TypeError('now must be a valid Date');
  }
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(now);
  const values = Object.fromEntries(parts.map(({type, value}) => [type, value]));
  return Date.UTC(Number(values.year), Number(values.month) - 1, Number(values.day));
}


export function getCountdownState(now, electionDate, timeZone) {
  const days = Math.round((isoDateOrdinal(electionDate) - zonedDateOrdinal(now, timeZone)) / DAY_MS);
  if (days > 0) return {state: 'countdown', days, label: 'UNTIL ELECTION DAY'};
  if (days === 0) return {state: 'election-day', days: null, label: 'ELECTION DAY IS HERE'};
  return {state: 'results', days: null, label: 'RESULTS COVERAGE'};
}


export function orderCounties(counties, pinnedId = DEFAULT_COUNTY_ID) {
  return [...counties].sort((left, right) => {
    if (left.id === pinnedId) return -1;
    if (right.id === pinnedId) return 1;
    return String(left.name).localeCompare(String(right.name), 'en', {sensitivity: 'base'});
  });
}


export function resolveCountySelection(counties, storedId, pinnedId = DEFAULT_COUNTY_ID) {
  const ids = new Set(counties.map(({id}) => id));
  if (ids.has(storedId)) return storedId;
  if (ids.has(pinnedId)) return pinnedId;
  return counties[0]?.id ?? null;
}


export function resolveVoterActions(statewide, county) {
  return ACTIONS.map(([id, label, field]) => {
    if (isSafeHttpsUrl(county?.[field])) return {id, label, url: county[field], source: 'county'};
    if (isSafeHttpsUrl(statewide?.[field])) return {id, label, url: statewide[field], source: 'statewide'};
    return {
      id,
      label: id === 'county-office' ? label : `${label} — County Office`,
      url: isSafeHttpsUrl(county?.officeUrl) ? county.officeUrl : null,
      source: 'county-office',
    };
  });
}


export function pollPriority(poll, countyId) {
  if (poll?.scope === 'county-relevant' && poll.countyIds?.includes(countyId)) return 0;
  if (poll?.scope === 'florida-statewide') return 1;
  if (poll?.scope === 'national') return 2;
  return 3;
}


export function sortPollsForCounty(polls, countyId) {
  return polls
    .map((poll, index) => ({poll, index}))
    .sort((left, right) => (
      pollPriority(left.poll, countyId) - pollPriority(right.poll, countyId)
      || String(right.poll.endDate ?? '').localeCompare(String(left.poll.endDate ?? ''))
      || left.index - right.index
    ))
    .map(({poll}) => poll);
}


function isSafeHttpsUrl(value) {
  try { return new URL(String(value)).protocol === 'https:'; } catch { return false; }
}


export function getDisplayPolls(pollingData, readiness, now = new Date()) {
  if (!pollingData || !readiness?.publicDisplayEnabled || !readiness?.gates?.publicDisplayReady) return [];
  const required = readiness.methodology?.minimumRequiredFields ?? [];
  const sources = new Set((readiness.sources ?? [])
    .filter(({enabled, permittedForRepublication}) => enabled && permittedForRepublication)
    .map(({id}) => id));
  const freshnessDays = Number(readiness.methodology?.freshnessDays ?? 14);
  const today = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  return [...(pollingData.races ?? []), ...(pollingData.nationalIndicators ?? [])]
    .filter((poll) => required.every((field) => poll[field] !== undefined && poll[field] !== null))
    .filter((poll) => sources.has(poll.sourceId) && isSafeHttpsUrl(poll.sourceUrl))
    .filter((poll) => Array.isArray(poll.answers) && poll.answers.length > 0 && Number(poll.sampleSize) > 0)
    .filter((poll) => ['county-relevant', 'florida-statewide', 'national'].includes(poll.scope))
    .filter((poll) => ['current', 'older-poll'].includes(poll.displayStatus))
    .map((poll) => {
      const end = Date.parse(`${poll.endDate}T00:00:00Z`);
      const ageDays = Number.isFinite(end) ? Math.floor((today - end) / DAY_MS) : Infinity;
      return {...poll, displayStatus: ageDays <= freshnessDays ? poll.displayStatus : 'older-poll'};
    });
}


function setText(root, selector, value) {
  const node = root?.querySelector?.(selector);
  if (node) node.textContent = value;
}


function renderCountdown(documentRef, election, now = new Date()) {
  const root = documentRef.getElementById('election-countdown');
  if (!root) return;
  const state = getCountdownState(now, election.date, election.timeZone);
  root.dataset.state = state.state;
  setText(root, '[data-countdown-value]', state.days == null ? '' : String(state.days));
  setText(root, '[data-countdown-unit]', state.days == null ? '' : 'DAYS');
  setText(root, '[data-countdown-label]', state.label);
  setText(root, '[data-countdown-date]', 'NOVEMBER 3, 2026');
}


export function startCountdown(documentRef, election = DEFAULT_ELECTION, options = {}) {
  const now = options.now ?? (() => new Date());
  const update = () => renderCountdown(documentRef, election, now());
  update();
  const setIntervalImpl = options.setIntervalImpl ?? globalThis.setInterval;
  const timer = setIntervalImpl?.(update, 60_000);
  documentRef?.addEventListener?.('visibilitychange', () => {
    if (documentRef.visibilityState !== 'hidden') update();
  });
  return timer;
}


function renderActions(documentRef, statewide, county) {
  const root = documentRef.getElementById('voter-actions');
  if (!root) return;
  root.replaceChildren();
  for (const action of resolveVoterActions(statewide, county)) {
    if (!action.url) continue;
    const link = documentRef.createElement('a');
    link.href = action.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.className = 'voter-action';
    link.dataset.source = action.source;
    link.textContent = action.label;
    root.append(link);
  }
}


function formatGuidanceDate(value) {
  if (!value) return '';
  return new Intl.DateTimeFormat('en-US', {month: 'long', day: 'numeric', timeZone: 'UTC'})
    .format(new Date(`${value}T12:00:00Z`));
}


function renderGuidance(documentRef, voterData) {
  const root = documentRef.querySelector?.('.voter-facts');
  if (!root) return;
  const {statewide, election} = voterData;
  const topics = [
    ['registration', formatGuidanceDate(election.registrationDeadline)],
    ['identification', 'Photo + signature ID'],
    ['voteByMail', `Request by ${formatGuidanceDate(election.voteByMailRequestDeadline)}`],
    ['earlyVoting', `${formatGuidanceDate(election.earlyVotingStart)}–${formatGuidanceDate(election.earlyVotingEnd)}`],
    ['electionDay', formatGuidanceDate(election.date)],
  ];
  root.replaceChildren();
  for (const [key, dateLabel] of topics) {
    const topic = statewide[key];
    if (!topic) continue;
    const article = documentRef.createElement('article');
    article.className = 'voter-fact';
    const label = documentRef.createElement('div');
    label.className = 'voter-fact-label';
    label.textContent = topic.title;
    const strong = documentRef.createElement('strong');
    strong.textContent = dateLabel;
    const summary = documentRef.createElement('p');
    summary.textContent = topic.summary;
    const source = documentRef.createElement('a');
    source.className = 'voter-fact-source';
    article.append(label, strong, summary);
    if (isSafeHttpsUrl(topic.sourceUrl)) {
      source.href = topic.sourceUrl;
      source.target = '_blank';
      source.rel = 'noopener noreferrer';
      source.textContent = 'Official source ↗';
      article.append(source);
    }
    root.append(article);
  }
  setText(documentRef, '[data-voter-source-note]', `Source: ${statewide.officeName} · Verified ${formatGuidanceDate(statewide.verifiedAt)}, 2026`);
}


function renderPolls(documentRef, pollingData, readiness, countyId, now = new Date()) {
  const root = documentRef.getElementById('latest-polls');
  if (!root) return;
  const localStatus = root.querySelector('[data-local-poll-status]');
  if (!pollingData || !readiness?.publicDisplayEnabled || !readiness?.gates?.publicDisplayReady) {
    if (localStatus) localStatus.textContent = 'Polling is temporarily unavailable. No survey data is being substituted or estimated.';
    return;
  }
  const polls = getDisplayPolls(pollingData, readiness, now);
  const list = root.querySelector('[data-poll-list]');
  if (!list) return;
  list.replaceChildren();
  const hasLocalPoll = polls.some((poll) => (
    poll.displayStatus === 'current' && poll.scope === 'county-relevant' && poll.countyIds?.includes(countyId)
  ));
  if (localStatus) {
    localStatus.textContent = hasLocalPoll
      ? 'Current verified polling is available for a race relevant to this county.'
      : 'No current verified county-relevant poll is available. Showing current Florida statewide and national polls.';
  }
  for (const poll of sortPollsForCounty(polls, countyId)) {
    const article = documentRef.createElement('article');
    article.className = 'voter-poll-card';
    const header = documentRef.createElement('div');
    header.className = 'voter-poll-head';
    const kicker = documentRef.createElement('div');
    kicker.className = 'voter-poll-kicker';
    const scopeLabel = {
      'county-relevant': 'County-relevant race',
      'florida-statewide': 'Florida statewide',
      national: 'National indicator',
    }[poll.scope] ?? 'Election poll';
    const heading = documentRef.createElement('h3');
    heading.textContent = poll.raceName ?? poll.question ?? poll.raceId ?? 'Election poll';
    const metadata = documentRef.createElement('p');
    metadata.className = 'voter-poll-meta';
    const statusLabel = {
      current: 'Current',
      'older-poll': 'Older poll',
      'incomplete-metadata': 'Incomplete metadata',
      'source-unavailable': 'Source unavailable',
    }[poll.displayStatus] ?? 'Status unavailable';
    metadata.textContent = [
      statusLabel,
      poll.pollster,
      poll.sponsor ? `Sponsored by ${poll.sponsor}` : null,
      `${poll.startDate}–${poll.endDate}`,
      poll.publicationDate ? `Published ${poll.publicationDate}` : null,
      `${String(poll.population ?? '').toUpperCase()} · n=${poll.sampleSize}`,
      poll.marginOfError == null ? null : `Margin ±${poll.marginOfError} points`,
    ].filter(Boolean).join(' · ');
    kicker.textContent = `${scopeLabel} · ${statusLabel}`;
    header.append(kicker, heading, metadata);
    const source = documentRef.createElement('a');
    source.className = 'voter-poll-source';
    source.href = poll.sourceUrl;
    source.target = '_blank';
    source.rel = 'noopener noreferrer';
    source.textContent = 'Original poll and methodology ↗';
    header.append(source);
    article.append(header);
    for (const answer of poll.answers ?? []) {
      const row = documentRef.createElement('div');
      row.className = 'voter-poll-answer';
      const value = Math.max(0, Math.min(100, Number(answer.pct)));
      const top = documentRef.createElement('div');
      top.className = 'voter-poll-answer-row';
      const choice = documentRef.createElement('span');
      choice.textContent = answer.choice;
      const percentage = documentRef.createElement('span');
      percentage.textContent = `${value.toFixed(1)}%`;
      top.append(choice, percentage);
      const track = documentRef.createElement('div');
      track.className = 'voter-poll-track';
      const fill = documentRef.createElement('div');
      fill.className = 'voter-poll-fill';
      fill.style.width = `${value}%`;
      track.append(fill);
      row.append(top, track);
      article.append(row);
    }
    list.append(article);
  }
}


export async function initVoterHub(options = {}) {
  const documentRef = options.document ?? globalThis.document;
  const fetchImpl = options.fetchImpl ?? globalThis.fetch;
  const storage = options.storage ?? globalThis.sessionStorage;
  const status = documentRef?.getElementById?.('voter-hub-status');
  try {
    const voterData = options.voterData ?? await fetchImpl('data/voter-information.json', {cache: 'no-store'}).then((response) => {
      if (!response.ok) throw new Error(`voter information request failed: ${response.status}`);
      return response.json();
    });
    const counties = orderCounties(voterData.counties, DEFAULT_COUNTY_ID);
    renderGuidance(documentRef, voterData);
    let storedId = null;
    try { storedId = storage?.getItem?.(COUNTY_STORAGE_KEY); } catch { storedId = null; }
    let selectedId = resolveCountySelection(counties, storedId, DEFAULT_COUNTY_ID);
    const select = documentRef.getElementById('voter-county-select');

    const update = () => {
      const county = counties.find(({id}) => id === selectedId);
      renderActions(documentRef, voterData.statewide, county);
      renderPolls(documentRef, options.pollingData, options.pollingReadiness, selectedId, options.now?.() ?? new Date());
      setText(documentRef, '[data-selected-county]', `${county?.name ?? 'County'} County`);
    };

    if (select) {
      select.replaceChildren();
      for (const county of counties) {
        const option = documentRef.createElement('option');
        option.value = county.id;
        option.textContent = `${county.name} County`;
        option.selected = county.id === selectedId;
        select.append(option);
      }
      select.addEventListener('change', () => {
        selectedId = resolveCountySelection(counties, select.value, DEFAULT_COUNTY_ID);
        try { storage?.setItem?.(COUNTY_STORAGE_KEY, selectedId); } catch { /* session storage is optional */ }
        update();
      });
    }
    renderCountdown(documentRef, voterData.election, options.now?.() ?? new Date());
    update();
    if (status) {
      status.dataset.state = 'ready';
      status.textContent = '';
    }
  } catch (error) {
    if (status) {
      status.dataset.state = 'unavailable';
      status.textContent = 'Voter tools are temporarily unavailable. Use the official Florida voter information link below.';
    }
    options.onError?.(error);
  }
}


async function bootVoterHub() {
  startCountdown(document, DEFAULT_ELECTION);
  let pollingData = null;
  let pollingReadiness = null;
  try {
    const [dataResponse, readinessResponse] = await Promise.all([
      fetch('data/polling.json', {cache: 'no-store'}),
      fetch('data/polling-readiness.json', {cache: 'no-store'}),
    ]);
    if (dataResponse.ok && readinessResponse.ok) {
      pollingData = await dataResponse.json();
      pollingReadiness = await readinessResponse.json();
    }
  } catch { /* voter tools still load with an honest polling empty state */ }
  await initVoterHub({pollingData, pollingReadiness});
}


if (typeof window !== 'undefined' && typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootVoterHub, {once: true});
  } else {
    bootVoterHub();
  }
}
