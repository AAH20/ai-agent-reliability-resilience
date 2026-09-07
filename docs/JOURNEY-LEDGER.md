# Journey outcome ledger

The journey ledger connects an agent trace identifier to a declared business
outcome without storing prompts, model outputs, tool arguments, credentials or
customer PII. It is intentionally an ingestion boundary, not another tracing
backend. Langfuse, Phoenix, LangSmith or an OpenTelemetry pipeline can remain
the system of record for detailed traces.

## Event contract

Each JSONL event requires `event_id`, `trace_id`, `occurred_at`, `workflow` and
`status`. Supported states are `started`, `succeeded`, `failed`, `abandoned`
and `escalated`. Optional fields are:

- `expected_value`: caller-declared value exposed when a journey is unsuccessful;
- `realized_value`: caller-supplied observed value for successful journeys;
- `currency`: required three-letter currency code whenever either value is non-zero;
- `failure_category`: a controlled classification such as `mcp_timeout`;
- `customer_ref`: an opaque or hashed correlation value, never raw PII.

Event IDs make ingestion idempotent. The latest event for each trace determines
the current journey outcome. Timestamp ordering is deterministic.

## Fifteen-minute proof

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .

agentresilience ingest examples/journey-events.jsonl \
  --db journey.db --output evidence/ingestion.json
agentresilience journeys --db journey.db \
  --output evidence/journey-report.json
```

The included fixture produces one successful journey, one failed journey, a
50% completion rate, USD 80 of caller-supplied realized value and USD 120 of
estimated exposure. Values are grouped by currency and are never silently
converted or combined. These values are synthetic and demonstrate calculation
semantics only.

## Claim boundary

Expected value is not booked revenue, proven loss or causal attribution. A
production integration must document the authoritative source of realized
value, currency, attribution method, retention policy and treatment of refunds
or reversals. Currency conversion is deliberately outside version 0.1.
