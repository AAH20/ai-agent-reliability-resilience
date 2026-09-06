# Threat model

## Protected properties

- Exactly-once business effect where the destination supports idempotency
- Approval continuity across retries and recovery
- Correct amount, subject, scope and notification order
- Recoverability within the declared RTO and RPO
- Trace reconstruction when the primary telemetry path is unavailable
- Honest separation of observed value, attributed value and pipeline capacity

## Failure and abuse cases

| Case | Failure mode | Required control |
|---|---|---|
| Response lost after commit | Agent interprets uncertainty as failure and retries | Destination reconciliation plus idempotency key |
| Duplicate queue delivery | Same instruction executes twice | Durable deduplication and bounded retry |
| Token expires mid-workflow | Identity changes or step is partially complete | Re-authentication without approval substitution |
| Tool schema changes | Wrong arguments reach a consequential tool | Versioned validation and reject-before-write |
| MCP dependency unavailable | Agent fabricates or assumes a result | Safe degradation or abort |
| Telemetry path unavailable | Operator cannot reconstruct the transaction | Local buffering, immutable correlation ID and later flush |
| Prompt/tool result injection | Untrusted data tries to alter authority | Explicit policy, typed calls and least-privilege tools |
| Malicious or accidental replay | Old approval triggers a new effect | Approval expiry, nonce and destination deduplication |
| Metric gaming | Average availability hides integrity loss | Zero-gated critical-invariant score and disclosed denominator |
| Revenue overclaim | Pipeline is presented as realized value | Attribution classes and finance approval |

## Trust boundaries

The model, orchestrator, identity provider, MCP server, message broker, telemetry backend, approval system and destination system are separate failure domains. A production test must not collapse them into one success flag.

## Out of scope in v0.1

The reference runner does not establish cryptographic identity, attack a live model, validate a vendor MCP implementation, measure production availability or replace penetration testing, incident response, audit or financial review.
