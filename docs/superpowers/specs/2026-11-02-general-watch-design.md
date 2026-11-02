# General Election Watch — approved design

Mike approved using official feeds in the existing Election Center on November 2, 2026. Indian River County comes first, followed by statewide Florida and complete district totals. Today shows candidate lists and awaiting-results states; election night shows votes, shares and precinct reporting without winner calls. The open page refreshes without losing coverage selection. Data collection continues without an open chat.

Use the existing GitHub repository and hosting. A separate General-only pipeline preserves the frozen Primary and its 67-county activation gates. Direct official sources were chosen over external embeds (limited control) and licensed third-party feeds (cost/authorization). No DDHQ ingestion or Publishing Suite changes.

Verified sources: Florida DOS November 3 TSV download, and Indian River ENR election 4096. The collector runs on GitHub, where both sources returned HTTP 200. Official host and election date, complete candidate/county identity, integer totals, and consistent reporting counts are validated before replacing each snapshot. A failed source retains its last valid snapshot, exposes error health, and does not prevent publication of the other source or a delay notice.

Local return values remain suppressed until the county page's own update timestamp is after November 3, 7 p.m. Eastern. The initial page contains nonzero pre-election values dated October 27; those values never become live merely because the clock passes Election Day. State publication starts at 8 p.m. Eastern and requires a post-release source modification timestamp for nonzero values.

Scheduled GitHub collection targets five-minute intervals on November 3–4, then hourly through November 17. GitHub schedules and official releases may delay updates. Browser checks every 30 seconds, with a 15-minute overdue indicator. All returns remain unofficial; certification is never inferred from complete precincts or the page title. No automatic winner calls. Multi-seat races display share of candidate votes and their vote-for count.

Deployment requires Mike's approval after the tested result is reviewable.
