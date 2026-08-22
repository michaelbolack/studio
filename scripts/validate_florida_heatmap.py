#!/usr/bin/env python3
"""Fail-closed integrity checks for the Florida county results map."""

from __future__ import annotations

import json
import colorsys
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GEOMETRY = ROOT / "data" / "florida-counties.geojson"
INDEX = ROOT / "index.html"
STATEWIDE = ROOT / "data" / "statewide.json"
REGISTRATION = ROOT / "data" / "voter-registration-by-county.json"

EXPECTED = {
    "12001": "Alachua", "12003": "Baker", "12005": "Bay",
    "12007": "Bradford", "12009": "Brevard", "12011": "Broward",
    "12013": "Calhoun", "12015": "Charlotte", "12017": "Citrus",
    "12019": "Clay", "12021": "Collier", "12023": "Columbia",
    "12027": "DeSoto", "12029": "Dixie", "12031": "Duval",
    "12033": "Escambia", "12035": "Flagler", "12037": "Franklin",
    "12039": "Gadsden", "12041": "Gilchrist", "12043": "Glades",
    "12045": "Gulf", "12047": "Hamilton", "12049": "Hardee",
    "12051": "Hendry", "12053": "Hernando", "12055": "Highlands",
    "12057": "Hillsborough", "12059": "Holmes", "12061": "Indian River",
    "12063": "Jackson", "12065": "Jefferson", "12067": "Lafayette",
    "12069": "Lake", "12071": "Lee", "12073": "Leon", "12075": "Levy",
    "12077": "Liberty", "12079": "Madison", "12081": "Manatee",
    "12083": "Marion", "12085": "Martin", "12086": "Miami-Dade",
    "12087": "Monroe", "12089": "Nassau", "12091": "Okaloosa",
    "12093": "Okeechobee", "12095": "Orange", "12097": "Osceola",
    "12099": "Palm Beach", "12101": "Pasco", "12103": "Pinellas",
    "12105": "Polk", "12107": "Putnam", "12109": "St. Johns",
    "12111": "St. Lucie", "12113": "Santa Rosa", "12115": "Sarasota",
    "12117": "Seminole", "12119": "Sumter", "12121": "Suwannee",
    "12123": "Taylor", "12125": "Union", "12127": "Volusia",
    "12129": "Wakulla", "12131": "Walton", "12133": "Washington",
}


def coordinates(value):
    if (
        isinstance(value, list)
        and len(value) >= 2
        and all(isinstance(item, (int, float)) for item in value[:2])
    ):
        yield value[:2]
        return
    if isinstance(value, list):
        for item in value:
            yield from coordinates(item)


def main() -> None:
    data = json.loads(GEOMETRY.read_text(encoding="utf-8-sig"))
    assert data.get("type") == "FeatureCollection"
    features = data.get("features")
    assert isinstance(features, list) and len(features) == 67

    actual = {}
    for feature in features:
        properties = feature.get("properties") or {}
        fips = str(feature.get("id") or properties.get("GEOID") or "")
        name = str(properties.get("NAME") or "").removesuffix(" County")
        assert re.fullmatch(r"12[0-9]{3}", fips), f"Invalid Florida FIPS: {fips!r}"
        assert fips not in actual, f"Duplicate FIPS: {fips}"
        assert feature.get("geometry", {}).get("type") in {"Polygon", "MultiPolygon"}
        points = list(coordinates(feature["geometry"].get("coordinates")))
        assert points, f"Empty geometry: {fips}"
        assert all(-88 < lon < -79 and 24 < lat < 32 for lon, lat in points)
        actual[fips] = name

    assert actual == EXPECTED, {
        "missing_or_changed": sorted(set(EXPECTED.items()) - set(actual.items())),
        "unexpected": sorted(set(actual.items()) - set(EXPECTED.items())),
    }

    registration = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    assert registration.get("asOf") == "2026-07-31"
    assert registration.get("sourceUrl") == (
        "https://dos.fl.gov/elections/data-statistics/voter-registration-statistics/"
        "voter-registration-reports/voter-registration-by-county-and-party/"
    )
    rows = registration.get("counties") or []
    assert len(rows) == 67
    assert {row.get("county") for row in rows} == set(EXPECTED.values())
    keys = ("republican", "democratic", "minorParty", "noPartyAffiliation", "total")
    sums = {key: 0 for key in keys}
    for row in rows:
        calculated = sum(row.get(key, 0) for key in keys[:-1])
        assert calculated == row.get("total") and calculated > 0, row.get("county")
        for key in keys:
            sums[key] += row[key]
    assert sums == registration.get("statewideTotals")
    assert sums == {
        "republican": 5_607_836,
        "democratic": 4_066_503,
        "minorParty": 497_679,
        "noPartyAffiliation": 3_327_656,
        "total": 13_499_674,
    }

    statewide = json.loads(STATEWIDE.read_text(encoding="utf-8"))
    assert statewide.get("coverageComplete") is True
    assert statewide.get("displayStatus") == "complete"
    assert statewide.get("countiesIncluded") == statewide.get("countiesExpected") == 67
    races = statewide.get("races") or []
    default_race = next(
        (
            race
            for race in races
            if race.get("name") == "REP Governor and Lieutenant Governor"
        ),
        None,
    )
    assert default_race, "Default Republican Governor primary race is missing"
    geography = default_race.get("geography") or []
    assert len(geography) == 67
    assert {item.get("county") for item in geography} == set(EXPECTED.values())
    for item in geography:
        votes = item.get("votes")
        assert isinstance(votes, dict) and len(votes) >= 2
        assert all(isinstance(value, (int, float)) and value >= 0 for value in votes.values())
        ordered = sorted(votes.values(), reverse=True)
        assert sum(ordered) > 0, f"Empty default race result: {item.get('county')}"
        assert ordered[0] > ordered[1], f"Tied default race result: {item.get('county')}"

    html = INDEX.read_text(encoding="utf-8")
    required = (
        'id="florida-heatmap"',
        'id="heatmap-race"',
        "function heatmapRaceComplete",
        "race.geography.length!==67",
        "Florida geometry failed the 67-county FIPS integrity gate",
        "General Election remains neutral until validated",
        "Unavailable / incomplete",
        "const HEATMAP_REP_COLORS=",
        "const HEATMAP_DEM_COLORS=",
        "party==='REP'?HEATMAP_REP_COLORS:party==='DEM'?HEATMAP_DEM_COLORS",
        'id="heatmap-mode"',
        "Registered Voters",
        "function voterRegistrationSafe",
        "data/voter-registration-by-county.json",
        "Official active voter registration",
    )
    for marker in required:
        assert marker in html, f"Missing heat-map safety marker: {marker}"
    assert "const HEATMAP_COLORS=" not in html, "Cross-party candidate palette is still enabled"
    assert "currentCounty=county;s.value=county;loadAll()" in html, (
        "Map selection must synchronize the county and reload results"
    )
    assert (
        "currentCounty=county;s.value=county;loadAll().then(()=>document.getElementById('local-races').scrollIntoView"
        not in html
    ), "Map selection must not jump away from the county map"
    assert html.index('id="florida-heatmap"') < html.index('id="local-races"'), (
        "Florida map must appear before race cards"
    )

    def palette_hues(name):
        line = next(
            (line for line in html.splitlines() if line.startswith(f"const {name}=")),
            None,
        )
        assert line, f"Missing palette: {name}"
        colors = re.findall(r"#[0-9a-fA-F]{6}", line)
        for color in colors:
            red, green, blue = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
            yield colorsys.rgb_to_hsv(red, green, blue)[0] * 360

    republican_hues = list(palette_hues("HEATMAP_REP_COLORS"))
    democratic_hues = list(palette_hues("HEATMAP_DEM_COLORS"))
    nonpartisan_hues = list(palette_hues("HEATMAP_NONPARTISAN_COLORS"))
    assert not any(190 <= hue <= 250 for hue in republican_hues), (
        "Republican palette contains a blue-family shade"
    )
    assert not any(hue <= 15 or hue >= 345 for hue in democratic_hues), (
        "Democratic palette contains a red-family shade"
    )
    assert not any(hue <= 15 or hue >= 345 or 190 <= hue <= 250 for hue in nonpartisan_hues), (
        "Independent/nonpartisan palette contains a reserved red- or blue-family shade"
    )

    print(
        "Florida heat-map gate passed: 67/67 FIPS geometries, registration totals, "
        "and fail-closed UI hooks verified"
    )


if __name__ == "__main__":
    main()
