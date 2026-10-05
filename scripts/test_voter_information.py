import copy
import json
import re
import unittest
from datetime import date
from pathlib import Path

from scripts.validate_voter_information import validate_document


COUNTY_NAMES = [
    "Alachua", "Baker", "Bay", "Bradford", "Brevard", "Broward",
    "Calhoun", "Charlotte", "Citrus", "Clay", "Collier", "Columbia",
    "DeSoto", "Dixie", "Duval", "Escambia", "Flagler", "Franklin",
    "Gadsden", "Gilchrist", "Glades", "Gulf", "Hamilton", "Hardee",
    "Hendry", "Hernando", "Highlands", "Hillsborough", "Holmes",
    "Indian River", "Jackson", "Jefferson", "Lafayette", "Lake", "Lee",
    "Leon", "Levy", "Liberty", "Madison", "Manatee", "Marion", "Martin",
    "Miami-Dade", "Monroe", "Nassau", "Okaloosa", "Okeechobee", "Orange",
    "Osceola", "Palm Beach", "Pasco", "Pinellas", "Polk", "Putnam",
    "Santa Rosa", "Sarasota", "Seminole", "St. Johns", "St. Lucie",
    "Sumter", "Suwannee", "Taylor", "Union", "Volusia", "Wakulla",
    "Walton", "Washington",
]


def county_id(name):
    return re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")


def valid_document():
    return {
        "schemaVersion": 1,
        "generatedAt": "2026-10-05T12:00:00Z",
        "election": {
            "name": "Florida General Election",
            "date": "2026-11-03",
            "timeZone": "America/New_York",
        },
        "statewide": {
            "officeName": "Florida Division of Elections",
            "sourceUrl": "https://dos.fl.gov/elections/for-voters/",
            "verifiedAt": "2026-10-05",
        },
        "counties": [
            {
                "id": county_id(name),
                "name": name,
                "officeName": f"{name} County Supervisor of Elections",
                "officeUrl": f"https://{county_id(name)}.example.gov/elections",
                "registrationUrl": None,
            }
            for name in COUNTY_NAMES
        ],
    }


class VoterInformationValidationTests(unittest.TestCase):
    def test_repository_dataset_valid(self):
        data_file = Path(__file__).resolve().parents[1] / "data" / "voter-information.json"
        document = json.loads(data_file.read_text(encoding="utf-8"))
        self.assertEqual(validate_document(document, today=date(2026, 10, 5)), [])
        self.assertEqual(len(document["counties"]), 67)
        self.assertTrue(all(county["officeUrl"] for county in document["counties"]))

        indian_river = next(
            county for county in document["counties"]
            if county["name"] == "Indian River"
        )
        for field in (
            "registrationUrl", "voteByMailUrl", "earlyVotingUrl",
            "precinctUrl", "sampleBallotUrl", "contactUrl",
        ):
            self.assertTrue(indian_river[field], field)

        for topic in (
            "registration", "identification", "voteByMail",
            "earlyVoting", "electionDay",
        ):
            self.assertTrue(document["statewide"][topic]["sourceUrl"], topic)
            self.assertEqual(document["statewide"][topic]["verifiedAt"], "2026-10-05")

    def test_valid_document_has_67_unique_counties(self):
        self.assertEqual(validate_document(valid_document(), today=date(2026, 10, 5)), [])

    def test_duplicate_county_fails(self):
        document = valid_document()
        document["counties"][-1] = copy.deepcopy(document["counties"][0])
        errors = validate_document(document, today=date(2026, 10, 5))
        self.assertIn("county names must be unique", errors)
        self.assertIn("county ids must be unique", errors)

    def test_missing_indian_river_fails(self):
        document = valid_document()
        document["counties"] = [
            county for county in document["counties"]
            if county["name"] != "Indian River"
        ]
        document["counties"].append({
            "id": "replacement",
            "name": "Replacement",
            "officeName": "Replacement Supervisor of Elections",
            "officeUrl": "https://replacement.example.gov/elections",
        })
        self.assertIn(
            "Indian River County is required",
            validate_document(document, today=date(2026, 10, 5)),
        )

    def test_missing_office_url_fails(self):
        document = valid_document()
        del document["counties"][0]["officeUrl"]
        self.assertIn(
            "Alachua: officeUrl is required",
            validate_document(document, today=date(2026, 10, 5)),
        )

    def test_non_https_url_fails(self):
        document = valid_document()
        document["counties"][0]["officeUrl"] = "http://alachua.example.gov/elections"
        self.assertIn(
            "Alachua: officeUrl must be an HTTPS URL",
            validate_document(document, today=date(2026, 10, 5)),
        )

    def test_invalid_election_date_fails(self):
        document = valid_document()
        document["election"]["date"] = "November 3, 2026"
        self.assertIn(
            "election.date must be ISO YYYY-MM-DD",
            validate_document(document, today=date(2026, 10, 5)),
        )

    def test_missing_statewide_source_fails(self):
        document = valid_document()
        del document["statewide"]["sourceUrl"]
        self.assertIn(
            "statewide.sourceUrl is required",
            validate_document(document, today=date(2026, 10, 5)),
        )

    def test_optional_missing_action_link_is_allowed(self):
        document = valid_document()
        document["counties"][0]["registrationUrl"] = None
        self.assertEqual(validate_document(document, today=date(2026, 10, 5)), [])


if __name__ == "__main__":
    unittest.main()
