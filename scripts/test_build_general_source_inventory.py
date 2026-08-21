import unittest

from build_general_source_inventory import build_inventory, source_family


class InventoryTests(unittest.TestCase):
    def test_source_family_classification(self):
        self.assertEqual(source_family("Martin", "https://results.enr.clarityelections.com/x"), "clarity-browser-session")
        self.assertEqual(source_family("Pinellas", "https://enr.votepinellas.gov/x"), "clarity-browser-session")
        self.assertEqual(source_family("Broward", "https://results.browardvotes.gov/x"), "broward-html")
        self.assertEqual(source_family("Seminole", "https://www.livevoterturnout.com/x"), "seminole-html")
        self.assertEqual(source_family("Indian River", "https://enr.electionsfl.org/x"), "standard-florida-enr")

    def test_new_inventory_is_fail_closed(self):
        manifest = {
            "counties": {
                "Martin": {"sourceUrl": "https://results.enr.clarityelections.com/x", "adapter": "clarity", "file": "data/martin.json"},
                "Indian River": {"sourceUrl": "https://enr.electionsfl.org/x", "adapter": "enr", "file": "data/indian-river.json"},
            }
        }
        inventory = build_inventory(manifest, generated_at="2026-08-21T00:00:00+00:00")
        self.assertEqual(inventory["summary"]["countiesInventoried"], 2)
        self.assertFalse(inventory["summary"]["allCountiesInventoried"])
        self.assertEqual(inventory["summary"]["generalSourcesValidated"], 0)
        self.assertFalse(inventory["summary"]["allGeneralSourcesValidated"])

    def test_existing_discovery_fields_are_preserved(self):
        manifest = {"counties": {"Martin": {"sourceUrl": "https://results.enr.clarityelections.com/x", "file": "data/martin.json"}}}
        existing = {"counties": {"Martin": {"generalElection": {
            "status": "discovered",
            "sourceUrl": "https://example.test/general",
            "electionId": "130000",
            "validatedAt": None,
            "validationEvidence": "official listing",
        }}}}
        inventory = build_inventory(manifest, existing=existing, generated_at="2026-08-21T00:00:00+00:00")
        general = inventory["counties"]["Martin"]["generalElection"]
        self.assertEqual(general["status"], "discovered")
        self.assertEqual(general["electionId"], "130000")
        self.assertEqual(inventory["summary"]["generalSourcesDiscovered"], 1)


if __name__ == "__main__":
    unittest.main()
