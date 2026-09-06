from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


OUTCOMES = {
    "SAFE_SUCCESS", "SAFE_DEGRADED", "SAFE_ABORT", "RECOVERED",
    "RECOVERED_WITH_MANUAL_RECONCILIATION", "SILENT_CORRUPTION",
    "DUPLICATE_SIDE_EFFECT", "UNAUTHORIZED_SIDE_EFFECT", "UNRECOVERABLE",
}


@dataclass
class Refund:
    transaction_id: str
    customer_id: str
    amount: float
    approval_id: str
    idempotency_key: str


@dataclass
class RunEvidence:
    attempts: int = 0
    duplicate_attempts: int = 0
    refunds: list[Refund] = field(default_factory=list)
    notifications: list[str] = field(default_factory=list)
    trace_events: list[dict[str, Any]] = field(default_factory=list)
    buffered_events: list[dict[str, Any]] = field(default_factory=list)
    manual_reconciliation: bool = False
    token_expired: bool = False
    elapsed_ms: float = 0
    recovery_point_loss: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
