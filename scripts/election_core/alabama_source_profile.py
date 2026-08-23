"""Research-only Alabama source profile for national Election Center onboarding."""
ALABAMA_SOURCE_PROFILE = {
    "state": "AL",
    "name": "Alabama",
    "status": "research-only",
    "enabled": False,
    "localJurisdictionType": "county",
    "expectedLocalJurisdictions": 67,
    "officialAuthority": "Alabama Secretary of State",
    "electionNight": {
        "host": "www2.alabamavotes.gov",
        "scheme": "https",
        "statewidePath": "/electionNight/statewideResultsByContest.aspx",
        "countyPath": "/electionNight/countyResultsByContest.aspx",
        "coverageLabel": "Counties Reported",
        "countyCoverageLabel": "Boxes Reported",
    },
    "officialData": {
        "electionInformation": "https://www.sos.alabama.gov/alabama-votes/voter/election-information/2026",
        "downloads": "https://www.sos.alabama.gov/alabama-votes/voter/election-data",
        "precinctResultsAvailable": True,
    },
    "sourcePolicy": {
        "authoritativeStateSource": "Alabama Secretary of State / AlabamaVotes.gov",
        "publishIncompleteAggregateLeaders": False,
        "requireExactCoverageBeforeComplete": True,
    },
}
