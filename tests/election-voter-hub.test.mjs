import test from 'node:test';
import assert from 'node:assert/strict';

import {
  getCountdownState,
  getDisplayPolls,
  orderCounties,
  pollPriority,
  resolveCountySelection,
  resolveVoterActions,
  sortPollsForCounty,
  startCountdown,
} from '../assets/election-voter-hub.mjs';


test('October 5 in Eastern time is 29 whole calendar days before the election', () => {
  assert.deepEqual(
    getCountdownState(new Date('2026-10-05T16:00:00Z'), '2026-11-03', 'America/New_York'),
    {state: 'countdown', days: 29, label: 'UNTIL ELECTION DAY'},
  );
});

test('November 3 in Eastern time is Election Day', () => {
  assert.deepEqual(
    getCountdownState(new Date('2026-11-03T17:00:00Z'), '2026-11-03', 'America/New_York'),
    {state: 'election-day', days: null, label: 'ELECTION DAY IS HERE'},
  );
});

test('November 4 in Eastern time switches to results coverage', () => {
  assert.deepEqual(
    getCountdownState(new Date('2026-11-04T17:00:00Z'), '2026-11-03', 'America/New_York'),
    {state: 'results', days: null, label: 'RESULTS COVERAGE'},
  );
});

test('Eastern midnight after daylight saving time ends changes exactly one state', () => {
  assert.equal(
    getCountdownState(new Date('2026-11-03T04:59:59Z'), '2026-11-03', 'America/New_York').state,
    'countdown',
  );
  assert.equal(
    getCountdownState(new Date('2026-11-03T05:00:00Z'), '2026-11-03', 'America/New_York').state,
    'election-day',
  );
  assert.equal(
    getCountdownState(new Date('2026-11-04T05:00:00Z'), '2026-11-03', 'America/New_York').state,
    'results',
  );
});

test('Indian River is pinned first and every other county is alphabetical', () => {
  const counties = [
    {id: 'volusia', name: 'Volusia'},
    {id: 'alachua', name: 'Alachua'},
    {id: 'indian-river', name: 'Indian River'},
    {id: 'baker', name: 'Baker'},
  ];
  assert.deepEqual(
    orderCounties(counties, 'indian-river').map(({id}) => id),
    ['indian-river', 'alachua', 'baker', 'volusia'],
  );
  assert.deepEqual(counties.map(({id}) => id), ['volusia', 'alachua', 'indian-river', 'baker']);
});

test('unknown stored county selection falls back to Indian River', () => {
  const counties = [{id: 'alachua'}, {id: 'indian-river'}];
  assert.equal(resolveCountySelection(counties, 'unknown-county', 'indian-river'), 'indian-river');
  assert.equal(resolveCountySelection(counties, 'alachua', 'indian-river'), 'alachua');
});

test('missing county action uses statewide link or verified county office', () => {
  const actions = resolveVoterActions(
    {registrationUrl: 'https://state.example/register', sampleBallotUrl: null},
    {
      registrationUrl: null,
      sampleBallotUrl: null,
      officeUrl: 'https://county.example/elections',
    },
  );
  assert.deepEqual(
    actions.find(({id}) => id === 'registration'),
    {id: 'registration', label: 'Check Registration', url: 'https://state.example/register', source: 'statewide'},
  );
  assert.deepEqual(
    actions.find(({id}) => id === 'sample-ballot'),
    {id: 'sample-ballot', label: 'View Sample Ballot — County Office', url: 'https://county.example/elections', source: 'county-office'},
  );
});

test('poll priority is county relevant, then Florida, then national', () => {
  assert.equal(pollPriority({scope: 'county-relevant', countyIds: ['indian-river']}, 'indian-river'), 0);
  assert.equal(pollPriority({scope: 'florida-statewide', countyIds: []}, 'indian-river'), 1);
  assert.equal(pollPriority({scope: 'national', countyIds: []}, 'indian-river'), 2);
  assert.equal(pollPriority({scope: 'county-relevant', countyIds: ['orange']}, 'indian-river'), 3);
});

test('poll sorting uses priority and newest end date while preserving exact ties', () => {
  const polls = [
    {pollId: 'national', scope: 'national', countyIds: [], endDate: '2026-10-04'},
    {pollId: 'local-old', scope: 'county-relevant', countyIds: ['indian-river'], endDate: '2026-09-30'},
    {pollId: 'state', scope: 'florida-statewide', countyIds: [], endDate: '2026-10-05'},
    {pollId: 'local-new-a', scope: 'county-relevant', countyIds: ['indian-river'], endDate: '2026-10-03'},
    {pollId: 'local-new-b', scope: 'county-relevant', countyIds: ['indian-river'], endDate: '2026-10-03'},
  ];
  assert.deepEqual(
    sortPollsForCounty(polls, 'indian-river').map(({pollId}) => pollId),
    ['local-new-a', 'local-new-b', 'local-old', 'state', 'national'],
  );
});

test('poll display honors readiness, metadata, safe sources, and runtime freshness', () => {
  const readiness = {
    publicDisplayEnabled: true,
    methodology: {freshnessDays: 14, minimumRequiredFields: [
      'pollId', 'raceId', 'sourceId', 'pollster', 'startDate', 'endDate',
      'population', 'sampleSize', 'answers', 'sourceUrl', 'scope', 'countyIds', 'displayStatus',
    ]},
    sources: [{id: 'verified', enabled: true, permittedForRepublication: true}],
    gates: {publicDisplayReady: true},
  };
  const valid = {
    pollId: 'valid', raceId: 'race', sourceId: 'verified', pollster: 'Pollster',
    startDate: '2026-09-20', endDate: '2026-09-22', population: 'lv', sampleSize: 500,
    answers: [{choice: 'Yes', pct: 50}], sourceUrl: 'https://example.com/poll',
    scope: 'florida-statewide', countyIds: [], displayStatus: 'current',
  };
  const dataset = {races: [valid], nationalIndicators: []};
  assert.deepEqual(getDisplayPolls(dataset, readiness, new Date('2026-10-05T12:00:00Z')).map(p => p.displayStatus), ['current']);
  assert.deepEqual(getDisplayPolls(dataset, readiness, new Date('2026-10-08T12:00:00Z')).map(p => p.displayStatus), ['older-poll']);
  assert.deepEqual(getDisplayPolls(dataset, {...readiness, publicDisplayEnabled: false}, new Date()), []);
  assert.deepEqual(getDisplayPolls({races: [{...valid, sourceUrl: 'javascript:alert(1)'}]}, readiness, new Date()), []);
  const {sampleSize, ...malformed} = valid;
  assert.deepEqual(getDisplayPolls({races: [malformed]}, readiness, new Date()), []);
});

test('countdown starts immediately and schedules refreshes independently of data requests', () => {
  const values = {};
  const root = {dataset: {}, querySelector(selector) { return values[selector] ??= {textContent: ''}; }};
  const documentRef = {getElementById(id) { return id === 'election-countdown' ? root : null; }, addEventListener() {}};
  let callback;
  startCountdown(documentRef, {date: '2026-11-03', timeZone: 'America/New_York'}, {
    now: () => new Date('2026-10-05T12:00:00Z'),
    setIntervalImpl(fn, delay) { callback = fn; assert.equal(delay, 60_000); return 1; },
  });
  assert.equal(values['[data-countdown-value]'].textContent, '29');
  assert.equal(typeof callback, 'function');
});
