# KPIs and unit economics

## Measurement contract

Every KPI must have a named owner, fixed denominator, evidence source, target, guardrail and review cadence before it is used for incentives or external claims.

| KPI | Numerator / denominator | Evidence source | Suggested initial target | Guardrail |
|---|---|---|---|---|
| Recovery Integrity Score | 100 if zero critical invariant failures; otherwise 0 | Destination and approval evidence | 100% release gate | No averaging across integrity failures |
| Safe Recovery Rate | Safe outcomes / completed experiments | Signed run reports | ≥99% after baseline | Report fault mix beside rate |
| Duplicate Side-Effect Rate | Duplicate-effect runs / completed experiments | Destination ledger | 0% | Any failure blocks release |
| Unauthorized Side-Effect Rate | Approval-breaking runs / completed experiments | Approval + destination evidence | 0% | Any failure blocks release |
| Trace Reconstruction Rate | Reconstructable runs / telemetry-outage runs | Buffered and primary trace | 100% | Sample trace completeness manually |
| RTO Attainment | Runs inside RTO / applicable runs | Monotonic runner duration | ≥99% | Publish p50/p95/p99 too |
| RPO Attainment | Runs inside transaction-loss objective / applicable runs | Destination reconciliation | 100% for financial writes | Preserve value-weighted loss |
| Manual Reconciliation Rate | Human-reconciled runs / completed runs | Case records | Declining from baseline | Never suppress necessary escalation |
| Fault Detection Coverage | Implemented and verified failure modes / prioritized failure modes | Risk register + experiment catalog | ≥80% of critical modes | Coverage is not effectiveness |

The reference `metrics` command reports a portfolio subset. Targets above are proposed starting points, not performance claims.

## Cost model

```text
Engineering cost = engineering hours × loaded hourly cost
Review cost = review hours × loaded hourly cost
Total program cost = engineering + review + infrastructure + model cost
Cost per experiment = total program cost / completed experiments
Cost per recovered transaction = total program cost / recovered transactions
Gross resilience value = expected loss reduction + recovery labor savings
                       + downtime value protected + recognized revenue
Net resilience value = gross resilience value - total program cost
ROI % = net resilience value / total program cost × 100
Benefit-cost ratio = gross resilience value / total program cost
Modeled payback months = total program cost / gross resilience value
                       × analysis-period months
```

Use marginal cost for scale decisions and fully loaded cost for investment decisions. Do not combine them without labeling the view.

## Risk value

```text
Baseline expected disruption loss
  = annual failure frequency × baseline integrity-failure probability × probable impact

Residual expected disruption loss
  = annual failure frequency × residual integrity-failure probability × probable impact

Expected loss reduction
  = baseline expected disruption loss - residual expected disruption loss
```

Probabilities should come from observed incidents, calibrated expert elicitation or a documented comparable—not aspiration. Run low/base/high sensitivity cases before approval.

## Revenue enablement without double counting

| Class | Recognition test | Included in net value? |
|---|---|---|
| Direct revenue enabled | Named signed/renewed contract, dated gating requirement, evidence accepted by decision owner | Yes |
| Contributory revenue | Resilience was one documented factor; approved attribution percentage applied | At attributed value only |
| Capacity-enabled pipeline | Extra reviews × qualification rate × average contract value | No; disclose separately |
| Marketing influence | Page views, stars, leads or general credibility | No |

For each recognized contract store the contract identifier, value basis, control/resilience requirement, baseline decision date, evidence acceptance date, counterfactual, attribution owner and finance sign-off. Never recognize the same value in risk reduction, downtime protection and revenue enablement without a documented reason.

## Decision rules

- Release only when critical integrity rates are zero in the declared fault portfolio.
- Expand blast radius only after the negative control proves the detector catches unsafe behavior.
- Fund the next increment when conservative expected benefit exceeds incremental cost and integrity guardrails remain satisfied.
- Rebaseline after workflow, model, MCP server, identity, queue or destination changes.
- Keep capacity pipeline outside ROI until a contract passes the recognition test.

The fixture is illustrative. Its output must be labeled modeled, with assumptions and attribution visible beside every executive chart.
