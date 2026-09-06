from __future__ import annotations

from typing import Any


def calculate(data: dict[str,Any]) -> dict[str,Any]:
    experiments=max(1,float(data["completed_experiments"])); recovered=max(1,float(data["recovered_transactions"])); hourly=float(data["loaded_hourly_cost"])
    engineering=float(data["engineering_hours"])*hourly; review=float(data["review_hours"])*hourly; infra=float(data["infrastructure_cost"]); model=float(data["model_cost"]); total=engineering+review+infra+model
    baseline=float(data["annual_failure_frequency"])*float(data["integrity_failure_probability_baseline"])*float(data["probable_impact"])
    residual=float(data["annual_failure_frequency"])*float(data["integrity_failure_probability_residual"])*float(data["probable_impact"])
    risk_reduction=baseline-residual
    recovery_savings=float(data["manual_reconciliation_hours_avoided"])*hourly
    downtime=float(data["value_per_minute"])*float(data["downtime_minutes_avoided"])*float(data.get("downtime_attribution_factor",1))
    direct=float(data.get("direct_revenue_enabled",0)); contributory=float(data.get("contributory_revenue",0))*float(data.get("attribution_factor",0))
    capacity=float(data.get("additional_reviews",0))*float(data.get("qualification_rate",0))*float(data.get("average_contract_value",0))
    gross=risk_reduction+recovery_savings+downtime+direct+contributory
    net=gross-total
    analysis_months=float(data.get("analysis_period_months",12))
    return {
        "total_program_cost":round(total,2),
        "cost_per_resilience_experiment":round(total/experiments,2),"cost_per_recovered_transaction":round(total/recovered,2),
        "baseline_expected_disruption_loss":round(baseline,2),"residual_expected_disruption_loss":round(residual,2),"expected_loss_reduction":round(risk_reduction,2),
        "recovery_labor_savings":round(recovery_savings,2),"downtime_value_protected":round(downtime,2),
        "direct_revenue_enabled":round(direct,2),"contributory_revenue_attributed":round(contributory,2),"capacity_enabled_pipeline":round(capacity,2),
        "gross_resilience_value":round(gross,2),"net_resilience_value":round(net,2),
        "resilience_roi_pct":round(net/total*100,1) if total else 0,
        "benefit_cost_ratio":round(gross/total,3) if total else 0,
        "modeled_payback_months":round(total/gross*analysis_months,2) if gross else None,
        "analysis_period_months":analysis_months,
        "disclaimer":"Illustrative decision support. Capacity pipeline is excluded from net value and is not booked revenue."
    }
