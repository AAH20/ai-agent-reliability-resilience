# Benchmark methodology

AgentResilience benchmark results are reproducible experiments, not universal model rankings.

## Required disclosure

- Repository commit and runner version
- Experiment files and JSON schema version
- Workflow, destination adapter and authoritative state definition
- Fault types, timing, concurrency and repetitions
- Model, tool and MCP server versions when applicable
- RTO, RPO and financial tolerance
- All failed runs, exclusions and missing telemetry
- Negative-control result
- Hardware and environment where timing is material

## Procedure

1. Freeze the experiment portfolio and classify critical invariants.
2. Run a safe baseline and confirm destination evidence.
3. Run the negative control; it must detect the known unsafe condition.
4. Inject one fault at a time to establish causality.
5. Run compound faults that reflect credible production coupling.
6. Repeat nondeterministic experiments enough to publish confidence intervals.
7. Reconcile every claimed result against destination state.
8. Export immutable raw evidence before calculating portfolio metrics.

The included deterministic fixture is suitable for unit and integration checks. It is not statistically representative. Production comparisons require identical workloads, fault portfolios, controls and evidence boundaries.
