import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from validate_clarity_staging import validate


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.staging = self.root / "staging"
        self.staging.mkdir()
        self.now = datetime(2026, 8, 21, 20, 0, tzinfo=timezone.utc)
        self.config = {
            "electionId": "2026-fl-primary-fixture",
            "mode": "test-fixture",
            "counties": [{
                "county": "Martin",
                "host": "https://results.enr.clarityelections.com/",
                "electionId": "126768",
                "enabled": True,
            }],
        }
        (self.root / "config.json").write_text(json.dumps(self.config))

    def tearDown(self):
        self.temp.cleanup()

    def write_snapshot(self, **updates):
        snapshot = {
            "schemaVersion": 1,
            "collector": "clarity-browser-session",
            "county": "Martin",
            "electionId": "126768",
            "clarityVersion": "378685",
            "sourceDataUrl": "https://results.enr.clarityelections.com/FL/Martin/126768/378685/json/en/summary.json",
            "collectedAt": self.now.isoformat(),
            "contestCount": 1,
            "payload": [{"C": "REP United States Senator", "CH": ["A", "B"], "V": [10, "20"]}],
        }
        snapshot.update(updates)
        (self.staging / "martin.json").write_text(json.dumps(snapshot))

    def report(self):
        return validate(self.root / "config.json", self.staging, 900, self.now)

    def test_fixture_passes_structure_but_not_general_gate(self):
        self.write_snapshot()
        report = self.report()
        self.assertTrue(report["structuralValidationPassed"])
        self.assertFalse(report["generalElectionSourceReady"])
        self.assertFalse(report["publishesProductionData"])

    def test_rejects_wrong_election_id(self):
        self.write_snapshot(electionId="wrong")
        self.assertFalse(self.report()["structuralValidationPassed"])

    def test_rejects_mismatched_vote_arrays(self):
        self.write_snapshot(payload=[{"C": "Race", "CH": ["A", "B"], "V": [10]}])
        self.assertFalse(self.report()["structuralValidationPassed"])

    def test_rejects_stale_snapshot(self):
        self.write_snapshot(collectedAt="2026-08-21T19:00:00+00:00")
        self.assertFalse(self.report()["structuralValidationPassed"])


if __name__ == "__main__":
    unittest.main()
