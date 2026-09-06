from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Refund, RunEvidence


ALLOWED_FAULTS = {
    "response_delay_after_commit", "duplicate_delivery", "token_expiry",
    "telemetry_outage", "tool_schema_drift", "mcp_unavailable",
}
ALLOWED_INVARIANTS = {
    "single_refund", "amount_matches_approval", "approval_continuity",
    "idempotency_present", "notification_after_commit", "single_notification",
    "trace_reconstructable", "rto_met", "rpo_met", "financial_variance_zero",
}


def load_experiment(path: str | Path) -> dict[str, Any]:
    data=json.loads(Path(path).read_text())
    for field in ("schema_version","id","business_process","transaction","faults","invariants","recovery_objectives"):
        if field not in data: raise ValueError(f"missing field: {field}")
    if data["schema_version"]!="1.0": raise ValueError("schema_version must be 1.0")
    unknown={f["type"] for f in data["faults"]}-ALLOWED_FAULTS
    if unknown: raise ValueError(f"unknown faults: {sorted(unknown)}")
    unknown_invariants=set(data["invariants"])-ALLOWED_INVARIANTS
    if unknown_invariants: raise ValueError(f"unknown invariants: {sorted(unknown_invariants)}")
    return data


class RefundSystem:
    """Synthetic destination system: the authoritative source for payment effects."""
    def __init__(self, evidence: RunEvidence, honor_idempotency: bool=True):
        self.evidence=evidence; self.honor_idempotency=honor_idempotency; self.by_key: dict[str,Refund]={}

    def issue(self, tx: dict[str,Any], key: str) -> Refund:
        self.evidence.attempts+=1
        if self.honor_idempotency and key in self.by_key:
            self.evidence.duplicate_attempts+=1
            return self.by_key[key]
        refund=Refund(f"refund-{len(self.evidence.refunds)+1}",tx["customer_id"],float(tx["amount"]),tx.get("approval_id",""),key)
        self.evidence.refunds.append(refund); self.by_key[key]=refund
        return refund


def _event(evidence: RunEvidence, name: str, telemetry_available: bool, trace_id: str) -> None:
    event={"name":name,"trace_id":trace_id,"sequence":len(evidence.trace_events)+len(evidence.buffered_events)+1}
    (evidence.trace_events if telemetry_available else evidence.buffered_events).append(event)


def run(experiment: dict[str,Any], unsafe_idempotency: bool=False) -> dict[str,Any]:
    evidence=RunEvidence(); tx=experiment["transaction"]; faults={f["type"]:f for f in experiment["faults"]}
    trace_id=f'trace-{experiment["id"].lower()}'; telemetry_available="telemetry_outage" not in faults
    system=RefundSystem(evidence,honor_idempotency=not unsafe_idempotency)
    _event(evidence,"workflow.accepted",telemetry_available,trace_id)
    key=tx["idempotency_key"]

    if "mcp_unavailable" in faults or "tool_schema_drift" in faults:
        if "mcp_unavailable" in faults:
            _event(evidence,"mcp.unavailable",telemetry_available,trace_id)
            evidence.elapsed_ms += float(faults["mcp_unavailable"].get("duration_ms", 1000))
        else:
            _event(evidence,"tool.schema_rejected",telemetry_available,trace_id)
            evidence.elapsed_ms += float(faults["tool_schema_drift"].get("duration_ms", 100))
    else:
        system.issue(tx,key); _event(evidence,"refund.committed",telemetry_available,trace_id)
        evidence.elapsed_ms+=float(experiment.get("baseline_latency_ms",100))
        if "response_delay_after_commit" in faults:
            evidence.elapsed_ms+=float(faults["response_delay_after_commit"].get("delay_ms",500))
            _event(evidence,"response.timeout",telemetry_available,trace_id)
            system.issue(tx,key); _event(evidence,"refund.reconciled",telemetry_available,trace_id)
        if "duplicate_delivery" in faults:
            system.issue(tx,key); _event(evidence,"queue.redelivery",telemetry_available,trace_id)

    if "token_expiry" in faults:
        evidence.token_expired=True; _event(evidence,"identity.token_expired",telemetry_available,trace_id)
    if evidence.refunds:
        evidence.notifications.append(evidence.refunds[0].transaction_id); _event(evidence,"customer.notified",telemetry_available,trace_id)
    if not telemetry_available:
        evidence.trace_events.extend(evidence.buffered_events); evidence.buffered_events.clear()
    evidence.elapsed_ms+=float(experiment.get("reconciliation_latency_ms",200))
    result=evaluate(experiment,evidence)
    payload={"experiment_id":experiment["id"],"faults":[f["type"] for f in experiment["faults"]],"result":result,"evidence":evidence.as_dict(),"notice":"Synthetic controlled experiment; not observed production performance."}
    canonical=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode(); payload["evidence_sha256"]=hashlib.sha256(canonical).hexdigest()
    payload["generated_at"]=datetime.now(timezone.utc).isoformat()
    return payload


def evaluate(experiment: dict[str,Any], evidence: RunEvidence) -> dict[str,Any]:
    tx=experiment["transaction"]
    ordered_events=sorted(evidence.trace_events,key=lambda event:event["sequence"])
    commit_sequences=[event["sequence"] for event in ordered_events if event["name"]=="refund.committed"]
    notification_sequences=[event["sequence"] for event in ordered_events if event["name"]=="customer.notified"]
    all_checks={
        "single_refund":len(evidence.refunds)<=1,
        "amount_matches_approval":len(evidence.refunds)==0 or all(r.amount==float(tx["amount"]) for r in evidence.refunds),
        "approval_continuity":len(evidence.refunds)==0 or all(r.approval_id==tx.get("approval_id") and bool(r.approval_id) for r in evidence.refunds),
        "idempotency_present":all(bool(r.idempotency_key) for r in evidence.refunds),
        "notification_after_commit":not notification_sequences or bool(commit_sequences) and min(notification_sequences)>min(commit_sequences),
        "single_notification":len(evidence.notifications)<=1,
        "trace_reconstructable":bool(ordered_events) and not evidence.buffered_events and all(e.get("trace_id") for e in ordered_events) and [e["sequence"] for e in ordered_events]==list(range(1,len(ordered_events)+1)),
        "rto_met":evidence.elapsed_ms<=float(experiment["recovery_objectives"]["rto_ms"]),
        "rpo_met":evidence.recovery_point_loss<=int(experiment["recovery_objectives"]["rpo_transactions"]),
        "financial_variance_zero": (
            len(evidence.refunds) == 0
            if {"mcp_unavailable", "tool_schema_drift"} & {f["type"] for f in experiment["faults"]}
            else round(sum(r.amount for r in evidence.refunds) - float(tx["amount"]), 2) == 0
        ),
    }
    checks={name:all_checks[name] for name in experiment["invariants"]}
    failed=[name for name,passed in checks.items() if not passed]
    if not checks["single_refund"]: outcome="DUPLICATE_SIDE_EFFECT"
    elif not checks["approval_continuity"]: outcome="UNAUTHORIZED_SIDE_EFFECT"
    elif not checks["financial_variance_zero"]: outcome="SILENT_CORRUPTION"
    elif failed: outcome="UNRECOVERABLE"
    elif evidence.duplicate_attempts or evidence.token_expired: outcome="RECOVERED"
    elif {"mcp_unavailable", "tool_schema_drift"} & {f["type"] for f in experiment["faults"]}: outcome="SAFE_DEGRADED"
    else: outcome="SAFE_SUCCESS"
    return {"passed":not failed,"outcome":outcome,"checks":checks,"failed_invariants":failed}
