import json
import tempfile
import unittest
from pathlib import Path

from agentresilience.economics import calculate
from agentresilience.engine import load_experiment, run
from agentresilience.exporters import junit, markdown, sarif
from agentresilience.metrics import summarize

ROOT=Path(__file__).parents[1]


class AgentResilienceTests(unittest.TestCase):
    def setUp(self):
        self.partial=load_experiment(ROOT/"experiments/refund-partial-success.json")
        self.outage=load_experiment(ROOT/"experiments/refund-mcp-outage.json")
        self.schema_drift=load_experiment(ROOT/"experiments/refund-schema-drift.json")

    def test_experiment_loads(self): self.assertEqual(self.partial["schema_version"],"1.0")
    def test_unknown_fault_rejected(self):
        data=dict(self.partial); data["faults"]=[{"type":"meteor"}]
        with tempfile.NamedTemporaryFile("w+",suffix=".json") as f:
            json.dump(data,f); f.flush()
            with self.assertRaises(ValueError): load_experiment(f.name)
    def test_unknown_invariant_rejected(self):
        data=dict(self.partial); data["invariants"]=["always_be_lucky"]
        with tempfile.NamedTemporaryFile("w+",suffix=".json") as f:
            json.dump(data,f); f.flush()
            with self.assertRaises(ValueError): load_experiment(f.name)
    def test_partial_success_recovers(self): self.assertEqual(run(self.partial)["result"]["outcome"],"RECOVERED")
    def test_exactly_one_refund(self): self.assertEqual(len(run(self.partial)["evidence"]["refunds"]),1)
    def test_duplicate_attempts_are_contained(self): self.assertEqual(run(self.partial)["evidence"]["duplicate_attempts"],2)
    def test_approval_is_preserved(self): self.assertTrue(run(self.partial)["result"]["checks"]["approval_continuity"])
    def test_financial_variance_is_zero(self): self.assertTrue(run(self.partial)["result"]["checks"]["financial_variance_zero"])
    def test_buffered_telemetry_is_flushed(self):
        result=run(self.partial); self.assertEqual(result["evidence"]["buffered_events"],[]); self.assertGreater(len(result["evidence"]["trace_events"]),0)
    def test_trace_is_reconstructable(self): self.assertTrue(run(self.partial)["result"]["checks"]["trace_reconstructable"])
    def test_notification_occurs_after_destination_commit(self):
        result=run(self.partial); events=result["evidence"]["trace_events"]; commit=next(e["sequence"] for e in events if e["name"]=="refund.committed"); notification=next(e["sequence"] for e in events if e["name"]=="customer.notified"); self.assertGreater(notification,commit)
    def test_rto_and_rpo_are_met(self):
        checks=run(self.partial)["result"]["checks"]; self.assertTrue(checks["rto_met"]); self.assertTrue(checks["rpo_met"])
    def test_unsafe_idempotency_detects_duplicate_effect(self):
        result=run(self.partial,unsafe_idempotency=True); self.assertFalse(result["result"]["passed"]); self.assertEqual(result["result"]["outcome"],"DUPLICATE_SIDE_EFFECT")
    def test_mcp_outage_is_safe_degraded(self):
        result=run(self.outage); self.assertTrue(result["result"]["passed"]); self.assertEqual(result["result"]["outcome"],"SAFE_DEGRADED"); self.assertEqual(result["evidence"]["refunds"],[])
    def test_schema_drift_is_rejected_before_side_effect(self):
        result=run(self.schema_drift); self.assertTrue(result["result"]["passed"]); self.assertEqual(result["result"]["outcome"],"SAFE_DEGRADED"); self.assertEqual(result["evidence"]["refunds"],[]); self.assertEqual(result["evidence"]["trace_events"][1]["name"],"tool.schema_rejected")
    def test_evidence_digest_is_stable_before_timestamp(self): self.assertEqual(run(self.partial)["evidence_sha256"],run(self.partial)["evidence_sha256"])
    def test_junit_has_all_invariants(self): self.assertEqual(junit(run(self.partial)).count("<testcase"),len(self.partial["invariants"]))
    def test_sarif_empty_for_safe_run(self): self.assertEqual(sarif(run(self.partial))["runs"][0]["results"],[])
    def test_brief_has_evidence_boundary(self): self.assertIn("not observed production performance",markdown(run(self.partial)))
    def test_metrics_gate_is_100_for_safe_runs(self):
        result=summarize([run(self.partial),run(self.outage)]); self.assertEqual(result["recovery_integrity_score_pct"],100); self.assertEqual(result["safe_recovery_rate_pct"],100)
    def test_small_sample_p95_uses_nearest_rank(self):
        result=summarize([run(self.partial),run(self.outage),run(self.schema_drift)]); self.assertEqual(result["p95_recovery_ms"],800)
    def test_metrics_gate_is_zero_for_integrity_failure(self):
        result=summarize([run(self.partial),run(self.partial,unsafe_idempotency=True)]); self.assertEqual(result["recovery_integrity_score_pct"],0)
    def test_economics_excludes_capacity_from_net(self):
        data=json.loads((ROOT/"fixtures/economics.json").read_text()); first=calculate(data); data["additional_reviews"]=999999; second=calculate(data)
        self.assertEqual(first["net_resilience_value"],second["net_resilience_value"])
    def test_economics_are_reconcilable(self):
        result=calculate(json.loads((ROOT/"fixtures/economics.json").read_text())); self.assertEqual(result["gross_resilience_value"]-result["total_program_cost"],result["net_resilience_value"]); self.assertGreater(result["benefit_cost_ratio"],1)


if __name__=="__main__": unittest.main()
