import copy
import json
import unittest
from pathlib import Path

from agentresilience.repair import analyze, apply_adapter

INCIDENT = json.loads((Path(__file__).parents[1] / "examples/mcp-schema-rename.json").read_text())


class RepairTests(unittest.TestCase):
    def test_reproduces_rejection_and_verifies_local_rename(self):
        report = analyze(INCIDENT)
        self.assertEqual(report["status"], "candidate")
        self.assertEqual(report["current_schema_errors"], ["missing:case_id", "unknown:ticket_id"])
        self.assertEqual(report["repaired_schema_errors"], [])
        self.assertTrue(all(report["checks"].values()))
        transformed = apply_adapter(INCIDENT, report["adapter"])
        self.assertEqual(transformed["arguments"], {"case_id": "SYNTHETIC-1001", "resolution": "Synthetic resolution for a fictional ticket"})

    def test_report_omits_original_values(self):
        incident = copy.deepcopy(INCIDENT)
        incident["arguments"]["resolution"] = "PRIVATE_CUSTOMER_SECRET_123"
        report = analyze(incident)
        self.assertNotIn("PRIVATE_CUSTOMER_SECRET_123", json.dumps(report))
        self.assertNotIn(incident["incident_id"], json.dumps(report))
        self.assertEqual(report["fingerprint_sha256"], analyze(INCIDENT)["fingerprint_sha256"])

    def test_unrelated_missing_required_field_blocks_candidate(self):
        incident = copy.deepcopy(INCIDENT)
        incident["current_schema"]["properties"]["approval_token"] = {"type": "string"}
        incident["current_schema"]["required"].append("approval_token")
        report = analyze(incident)
        self.assertEqual(report["status"], "manual_review")
        self.assertIsNone(report["adapter"])

    def test_no_drift_blocks_candidate(self):
        incident = copy.deepcopy(INCIDENT)
        incident["current_schema"] = copy.deepcopy(incident["original_schema"])
        incident["current_schema"]["properties"]["case_id"] = {"type": "string"}
        incident["current_schema"]["required"].append("case_id")
        # Old call still rejects only the new required field, not a simple rename.
        report = analyze(incident)
        self.assertEqual(report["status"], "manual_review")

    def test_unsupported_constraints_fail_closed(self):
        incident = copy.deepcopy(INCIDENT)
        incident["current_schema"]["properties"]["case_id"]["pattern"] = "^C-"
        with self.assertRaisesRegex(ValueError, "unsupported property constraint"):
            analyze(incident)

    def test_type_changes_and_tampered_adapters_are_rejected(self):
        incident = copy.deepcopy(INCIDENT)
        incident["current_schema"]["properties"]["case_id"]["type"] = "integer"
        with self.assertRaisesRegex(ValueError, "cannot change an argument type"):
            analyze(incident)
        report = analyze(INCIDENT)
        adapter = copy.deepcopy(report["adapter"])
        adapter["renames"] = {"ticket_id": "resolution"}
        with self.assertRaisesRegex(ValueError, "does not match"):
            apply_adapter(INCIDENT, adapter)


if __name__ == "__main__": unittest.main()
