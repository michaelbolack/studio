# IRC Media Election Center — Project State

Last updated: 2026-11-02

## Canonical repository and production

- Repository: michaelbolack/studio. IRC Publishing Suite is separate and must remain untouched.
- Public page: https://www.ircmedia.net/election-center
- Actual Wix embed source observed: https://michaelbolack.github.io/studio/?v=20261023-layout2
- Approved release: PR #62, merge d8d9dbfb878c8c65c1f94d082be3bedda0a14976.
- First production General Watch run 41441592623 succeeded: both official sources healthy, snapshot committed, explicit GitHub Pages deployment succeeded. First production source checks: 2026-11-02T12:03:51Z.
- Deployed exact embedded application URL was browser-verified with the new General watch. A previously loaded Wix-frame browser cache still showed the preceding release during propagation; do not mistake a cached frame for missing source deployment.

## Independent General Election watch

- County source: https://enr.electionsfl.org/IND/4096/Summary/
- State source: https://flelectionfiles.floridados.gov/enightfilespublic/20261103_ElecResultsFL.txt
- Source contracts pinned in data/general-watch-contract.json. The collector validates full candidate/county identity, date, integer totals and reporting consistency.
- 26 county contests; 60 records across local, statewide, district, and Indian River state/federal scopes. Local contests lead. Top primary navigation opens General views; legacy map remains the August Primary archive.
- County source initially contains nonzero values dated October 27. Do not expose them as election returns. County values require the page's own post-November-3 7 p.m. Eastern update; statewide nonzero values require 8 p.m. Eastern and a post-release source modification timestamp.
- All returns remain unofficial. Never infer winner calls or certification from precinct completion or an Official page title.
- General workflow: .github/workflows/general-watch.yml, active on main. Scheduled about every five minutes November 3–4; hourly November 5–17; hard publishing date window ends November 18, 2026 UTC. GitHub schedule and source-release delays are possible.
- Browser checks every 30 seconds, retains selected scope, and marks failed or overdue updates. Each failed source retains its last valid independent snapshot.
- Bot commits explicitly deploy Pages. Publication safely rebases over unrelated main updates; no force pushes. Legacy recovery preserves all General snapshot files.

## Archive and existing protections

- Existing Primary data, map, polling, markets and legacy 67-county activation gates remain intact. The OLD General source inventory still reports not-ready; do not enable that legacy pipeline or confuse it with this independent verified watch.
- Legacy Publish live election results run 41441592482 failed closed at its existing coverage-complete protection for Alachua. This did not block the successful independent General Watch deployment. Do not bypass that protection.
- No restricted DDHQ ingestion. Public resources only as permitted.

## Verification

- 12 Python and 22 scoped Node tests passed. Final premerge General Watch run 41441193381 and Election Readiness run 41441193309 succeeded. Real runner dry runs returned both sources healthy.
- Desktop and 390px iframe mobile preview tested; no horizontal overflow. Review fixes have regression coverage.
- Full Node suite has an unrelated existing letters-newsroom.test.mjs failure: letters section follows Sunshine and published letters remain in ordinary feed (3 != 0). newsroom.html unchanged.

Read NEXT_TASK.md before subsequent work. Preserve the source gates, archive and separate Publishing Suite boundary.
