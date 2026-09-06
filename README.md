# AI Agent Reliability Engineering

**MCP chaos testing, operational resilience, transaction recovery, SRE metrics and Agentic AI unit economics.**

[![CI](https://github.com/AAH20/ai-agent-reliability-resilience/actions/workflows/ci.yml/badge.svg)](https://github.com/AAH20/ai-agent-reliability-resilience/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab.svg)](pyproject.toml)

AgentResilience is an open-source reliability lab for testing AI agents that execute consequential business workflows. It injects failures at tool, identity, queue and telemetry boundaries, then reconciles against authoritative destination state. The question is not *did the agent say it succeeded?* It is *did exactly the approved business effect occur, can we prove it, and did recovery meet its objective?*

The first reference workflow is a customer refund because partial success is concrete: a payment can commit while its MCP response times out, an event can redeliver, a token can expire and observability can disappear at the same time. AgentResilience verifies that only one authorized refund occurs, one notification follows it and a reconstructable evidence trail survives.

> This repository contains deterministic synthetic experiments. Results are not observed production performance, certification, an audit opinion or a guarantee of future resilience.

## What it proves

| Failure injected | Destination-state expectation | Reference result |
|---|---|---|
| Delayed response after commit | Reconcile; never blindly repeat the effect | `RECOVERED` |
| Duplicate queue delivery | One refund, duplicate attempt contained | `RECOVERED` |
| Identity token expiry | Preserve the committed effect and trace the identity event | `RECOVERED` |
| Telemetry outage | Buffer and restore a complete ordered trace | `RECOVERED` |
| MCP unavailable | No unverified write and no customer notification | `SAFE_DEGRADED` |
| Tool schema drift | Reject before the side effect | `SAFE_DEGRADED` |
| Idempotency disabled (negative control) | Detect multiple destination effects | `DUPLICATE_SIDE_EFFECT` |

The outcome taxonomy separates safe success and controlled degradation from silent corruption, duplicate or unauthorized effects and unrecoverable execution. A single critical business-integrity failure gates the Recovery Integrity Score to zero; averages cannot hide it.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .

agentresilience run experiments/refund-partial-success.json \
  --output report.json \
  --junit report.xml \
  --sarif report.sarif \
  --brief report.md

agentresilience run experiments/refund-mcp-outage.json --output outage.json
agentresilience metrics report.json outage.json --output metrics.json
agentresilience economics fixtures/economics.json --output economics.json
```

To prove the detector is active, deliberately disable destination idempotency. The command exits non-zero and reports `DUPLICATE_SIDE_EFFECT`:

```bash
agentresilience run experiments/refund-partial-success.json \
  --unsafe-idempotency --output negative-control.json
```

No third-party Python dependency is required at runtime. Experiments and reports are portable JSON; CI consumers can ingest JUnit and SARIF, while humans receive a Markdown recovery brief.

## Architecture

```text
Experiment contract
  ├─ transaction + approval + idempotency key
  ├─ fault schedule
  ├─ business invariants
  └─ RTO / RPO / financial tolerance
             │
             ▼
   Deterministic fault runner ─────► Synthetic destination ledger
             │                         (authoritative effects)
             ├─ telemetry buffer
             ├─ reconciliation
             └─ notification ordering
             │
             ▼
 Business-invariant evaluator
  ├─ outcome taxonomy
  ├─ cryptographic evidence digest
  ├─ KPI portfolio
  └─ JSON / JUnit / SARIF / Markdown
```

Production adapters should place the destination system—payment processor, CRM, ticketing system, cloud control plane or evidence store—above agent narrative and orchestration state in the evidence hierarchy. See [architecture](docs/ARCHITECTURE.md), [threat model](docs/THREAT_MODEL.md) and the [experiment schema](schemas/resilience-experiment.schema.json).

## KPIs that resist vanity reporting

| KPI | Definition | Decision use |
|---|---|---|
| Recovery Integrity Score | 100 only when no critical business invariant fails; otherwise 0 | Release gate |
| Safe Recovery Rate | Safe success, safe degradation, safe abort or recovered runs / all runs | Reliability trend |
| Duplicate Side-Effect Rate | Runs producing more than one destination effect / all runs | Financial-control gate |
| Unauthorized Side-Effect Rate | Runs breaking approval continuity / all runs | Access/control gate |
| Trace Reconstruction Rate | Runs with complete attributable traces / all runs | Auditability gate |
| p50/p95/p99 Recovery Time | Percentiles of deterministic recovery duration | RTO design |
| Manual Reconciliation Rate | Runs requiring a human reconciliation / all runs | Operating-cost driver |

The denominator, owner, evidence source, target, guardrail and review cadence for every KPI are defined in [KPIs and unit economics](docs/KPIS_AND_UNIT_ECONOMICS.md). A benchmark claim is valid only when the experiment set, runner version, fault configuration and negative controls are disclosed.

## Unit economics

AgentResilience reports cost per experiment and recovered transaction, expected disruption loss reduction, recovery labor savings, downtime value protected, explicitly attributable revenue and net resilience value. It keeps three revenue classes separate:

1. **Direct revenue enabled** — a signed or renewed contract whose gating resilience requirement is evidenced.
2. **Contributory revenue attributed** — revenue multiplied by an approved contribution factor.
3. **Capacity-enabled pipeline** — qualified opportunity capacity, disclosed separately and excluded from net value.

Illustrative fixture formulas:

```text
Total program cost = engineering + review + infrastructure + model cost
Expected loss reduction = baseline expected loss - residual expected loss
Net resilience value = expected loss reduction + labor savings
                     + attributed downtime value + direct revenue
                     + contributory revenue - total program cost
Resilience ROI = net resilience value / total program cost
Benefit-cost ratio = gross resilience value / total program cost
Modeled payback months = total cost / gross value × analysis-period months
```

The model is decision support, not booked revenue. Replace every fixture with finance-approved observations and attribution rules before business use.

## CI, containers and Kubernetes

- Reusable GitHub Action: `uses: AAH20/ai-agent-reliability-resilience@main`
- GitHub Actions matrix tests Python 3.10 and 3.12 and runs the safe and negative-control paths.
- The image runs as a non-root user and defaults to the partial-success experiment.
- The Helm chart schedules repeatable resilience experiments and preserves JSON results in the pod log.
- JUnit supports build gates; SARIF exposes failed invariants in code-scanning compatible tooling.

```yaml
- uses: AAH20/ai-agent-reliability-resilience@main
  with:
    experiment: experiments/refund-partial-success.json
    output: agent-resilience-report.json
```

```bash
docker build -t agentresilience:local .
docker run --rm agentresilience:local

helm template agentresilience deploy/helm \
  --set image.repository=agentresilience \
  --set image.tag=local
```

## Roadmap

- Signed experiment manifests and append-only evidence attestations
- Live MCP proxy for latency, malformed results, timeouts and disconnects
- AWS Step Functions, Lambda, SQS and EventBridge fault adapters
- Kubernetes disruption, pod eviction and dependency-partition experiments
- Elasticsearch and VictoriaLogs trace continuity adapters
- OpenTelemetry spans and dashboards tied to business transaction IDs
- Human approval expiry, revocation and separation-of-duties scenarios
- Refund, access grant, cloud change, evidence collection and incident-response packs
- Statistical repetitions, confidence intervals and calibrated production baselines
- OSCAL control evidence and auditor-ready resilience packets

## Responsible use

Run fault injection only in systems you own or are explicitly authorized to test. Start with synthetic or isolated environments; cap blast radius, value and duration; require abort criteria; and never use the included economics fixture as an external performance claim. Read [SECURITY.md](SECURITY.md) before connecting a real destination.

## Contributing

New workflows are most valuable when they define irreversible effects, approvals, reconciliation authorities, business invariants and negative controls—not only availability checks. See [CONTRIBUTING.md](CONTRIBUTING.md).

MIT licensed. Built by [Ahmed Hassan / A2Z SOC](https://a2zsoc.com).
