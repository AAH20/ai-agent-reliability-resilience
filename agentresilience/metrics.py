from __future__ import annotations

import math
from typing import Any


def summarize(runs: list[dict[str,Any]]) -> dict[str,Any]:
    total=max(1,len(runs)); sorted_times=sorted(float(r["evidence"]["elapsed_ms"]) for r in runs)
    def percentile(p: float) -> float:
        return sorted_times[min(len(sorted_times)-1,max(0,math.ceil(p*len(sorted_times))-1))] if sorted_times else 0
    violations=sum(len(r["result"]["failed_invariants"]) for r in runs)
    return {
        "experiments":len(runs),"pass_rate_pct":round(sum(r["result"]["passed"] for r in runs)/total*100,2),
        "business_invariant_violations":violations,
        "duplicate_side_effect_rate_pct":round(sum(r["result"]["outcome"]=="DUPLICATE_SIDE_EFFECT" for r in runs)/total*100,2),
        "unauthorized_side_effect_rate_pct":round(sum(r["result"]["outcome"]=="UNAUTHORIZED_SIDE_EFFECT" for r in runs)/total*100,2),
        "safe_recovery_rate_pct":round(sum(r["result"]["outcome"] in {"SAFE_SUCCESS","SAFE_DEGRADED","SAFE_ABORT","RECOVERED"} for r in runs)/total*100,2),
        "p50_recovery_ms":round(percentile(.5),2),"p95_recovery_ms":round(percentile(.95),2),"p99_recovery_ms":round(percentile(.99),2),
        "manual_reconciliation_rate_pct":round(sum(r["evidence"]["manual_reconciliation"] for r in runs)/total*100,2),
        "trace_reconstruction_rate_pct":round(sum(r["result"]["checks"]["trace_reconstructable"] for r in runs)/total*100,2),
        "recovery_integrity_score_pct":100.0 if violations==0 else 0.0,
        "score_rule":"Any critical business-integrity violation forces Recovery Integrity to zero."
    }
