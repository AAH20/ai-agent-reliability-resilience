from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


STATUSES = {"started", "succeeded", "failed", "abandoned", "escalated"}
TERMINAL_STATUSES = STATUSES - {"started"}


@dataclass(frozen=True)
class JourneyEvent:
    event_id: str
    trace_id: str
    occurred_at: str
    workflow: str
    status: str
    expected_value: float = 0.0
    realized_value: float = 0.0
    currency: str = ""
    failure_category: str = ""
    customer_ref: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JourneyEvent":
        required = ("event_id", "trace_id", "occurred_at", "workflow", "status")
        missing = [field for field in required if not data.get(field)]
        if missing:
            raise ValueError(f"missing journey event fields: {', '.join(missing)}")
        status = str(data["status"])
        if status not in STATUSES:
            raise ValueError(f"unsupported journey status: {status}")
        try:
            occurred_at = datetime.fromisoformat(str(data["occurred_at"]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("occurred_at must be an ISO-8601 timestamp") from exc
        expected = float(data.get("expected_value", 0))
        realized = float(data.get("realized_value", 0))
        if expected < 0 or realized < 0:
            raise ValueError("journey values cannot be negative")
        currency = str(data.get("currency", "")).upper()
        if (expected or realized) and (len(currency) != 3 or not currency.isalpha()):
            raise ValueError("currency must be a three-letter code when a value is supplied")
        return cls(
            event_id=str(data["event_id"]),
            trace_id=str(data["trace_id"]),
            occurred_at=occurred_at.astimezone(timezone.utc).isoformat(),
            workflow=str(data["workflow"]),
            status=status,
            expected_value=expected,
            realized_value=realized,
            currency=currency,
            failure_category=str(data.get("failure_category", "")),
            customer_ref=str(data.get("customer_ref", "")),
        )


class JourneyStore:
    """Small durable ledger for business outcomes linked to agent trace IDs."""

    def __init__(self, path: str | Path):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS journey_events (
                event_id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                workflow TEXT NOT NULL,
                status TEXT NOT NULL,
                expected_value REAL NOT NULL,
                realized_value REAL NOT NULL,
                currency TEXT NOT NULL,
                failure_category TEXT NOT NULL,
                customer_ref TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_journey_trace_time
                ON journey_events(trace_id, occurred_at);
            """
        )

    def close(self) -> None:
        self.connection.close()

    def ingest(self, events: Iterable[JourneyEvent]) -> dict[str, int]:
        accepted = duplicates = 0
        with self.connection:
            for event in events:
                cursor = self.connection.execute(
                    """INSERT OR IGNORE INTO journey_events (
                        event_id, trace_id, occurred_at, workflow, status,
                        expected_value, realized_value, currency,
                        failure_category, customer_ref
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event.event_id, event.trace_id, event.occurred_at,
                        event.workflow, event.status, event.expected_value,
                        event.realized_value, event.currency,
                        event.failure_category, event.customer_ref,
                    ),
                )
                if cursor.rowcount:
                    accepted += 1
                else:
                    duplicates += 1
        return {"accepted": accepted, "duplicates": duplicates}

    def report(self) -> dict[str, Any]:
        rows = self.connection.execute(
            """
            WITH ranked AS (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY trace_id ORDER BY occurred_at DESC, event_id DESC
                ) AS position
                FROM journey_events
            )
            SELECT * FROM ranked WHERE position = 1
            """
        ).fetchall()
        terminal = [row for row in rows if row["status"] in TERMINAL_STATUSES]
        successful = [row for row in terminal if row["status"] == "succeeded"]
        unsuccessful = [row for row in terminal if row["status"] != "succeeded"]
        failure_counts: dict[str, int] = {}
        for row in unsuccessful:
            category = row["failure_category"] or "unclassified"
            failure_counts[category] = failure_counts.get(category, 0) + 1
        completion = round(100 * len(successful) / len(terminal), 2) if terminal else 0.0
        value_by_currency: dict[str, dict[str, float]] = {}
        for row in terminal:
            currency = row["currency"] or "UNSPECIFIED"
            values = value_by_currency.setdefault(currency, {"observed_realized": 0.0, "estimated_exposure": 0.0})
            if row["status"] == "succeeded":
                values["observed_realized"] += row["realized_value"]
            else:
                values["estimated_exposure"] += row["expected_value"]
        for values in value_by_currency.values():
            values.update({key: round(value, 2) for key, value in values.items()})
        return {
            "journeys_observed": len(rows),
            "terminal_journeys": len(terminal),
            "successful_journeys": len(successful),
            "unsuccessful_journeys": len(unsuccessful),
            "completion_rate_pct": completion,
            "value_by_currency": dict(sorted(value_by_currency.items())),
            "failure_categories": dict(sorted(failure_counts.items(), key=lambda item: (-item[1], item[0]))),
            "claim_boundary": (
                "Realized value is caller-supplied observed data. Exposure is an estimate, "
                "not proven loss or recovered revenue."
            ),
        }


def load_jsonl(path: str | Path) -> list[JourneyEvent]:
    events: list[JourneyEvent] = []
    for line_number, line in enumerate(Path(path).read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError("event must be a JSON object")
            events.append(JourneyEvent.from_dict(value))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"invalid event at line {line_number}: {exc}") from exc
    return events
