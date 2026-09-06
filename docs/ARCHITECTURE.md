# Architecture and trust boundaries

AgentResilience treats an agent workflow as a distributed transaction without assuming that every participant supports atomic commit.

## Evidence hierarchy

1. Authoritative destination state: the payment, entitlement, cloud resource or record that changed.
2. Approval state: who authorized which effect, value, scope and expiry.
3. Delivery state: queue receipt, deduplication key and retry history.
4. Orchestrator state: workflow step and recovery decision.
5. Model narrative: useful context, never authoritative proof of completion.

The reference runner maintains a synthetic destination ledger. A delayed success response causes reconciliation using the idempotency key; it does not authorize a second refund. Notifications depend on a confirmed destination effect, not the agent's assertion.

## Recovery state machine

```text
ACCEPTED
  ├─ dependency/schema unavailable ─► SAFE_DEGRADED
  └─ request sent
       ├─ committed + response received ─► SAFE_SUCCESS
       └─ response uncertain ─► RECONCILE DESTINATION
              ├─ effect exists and matches approval ─► RECOVERED
              ├─ no effect ─► controlled retry or SAFE_ABORT
              └─ multiple/wrong effects ─► INTEGRITY FAILURE
```

Every production adapter should implement read-after-uncertain-write reconciliation, an idempotency contract, an approval binding, bounded retry, abort criteria and tamper-evident evidence.

## Extension contract

A workflow pack needs:

- a transaction definition and authoritative identifier;
- an approval object and its continuity rules;
- a destination adapter capable of reconciliation;
- fault injectors placed at real trust boundaries;
- invariants defined in business language;
- RTO, RPO and financial-variance objectives;
- at least one negative control proving that the detector fails closed.

The current runner is deterministic and single-process by design. It is a transparent reference implementation, not a distributed production fault platform.
