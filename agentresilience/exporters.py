from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any


def junit(run: dict[str,Any]) -> str:
    checks=run["result"]["checks"]; suite=ET.Element("testsuite",name=run["experiment_id"],tests=str(len(checks)),failures=str(sum(not v for v in checks.values())))
    for name,passed in checks.items():
        case=ET.SubElement(suite,"testcase",name=name,classname="agentresilience.invariant")
        if not passed: ET.SubElement(case,"failure",message="business invariant violated")
    return ET.tostring(suite,encoding="unicode")


def sarif(run: dict[str,Any]) -> dict[str,Any]:
    failed=run["result"]["failed_invariants"]
    return {"version":"2.1.0","$schema":"https://json.schemastore.org/sarif-2.1.0.json","runs":[{"tool":{"driver":{"name":"AgentResilience"}},"results":[{"ruleId":name,"level":"error","message":{"text":f'Business invariant failed in {run["experiment_id"]}: {name}'}} for name in failed]}]}


def markdown(run: dict[str,Any]) -> str:
    evidence=run["evidence"]; result=run["result"]
    return f"""# Agent resilience experiment: {run['experiment_id']}

**Outcome:** {result['outcome']}<br>
**Passed:** {str(result['passed']).lower()}<br>
**Recovery time:** {evidence['elapsed_ms']:.0f} ms<br>
**Refund attempts/effects:** {evidence['attempts']} / {len(evidence['refunds'])}<br>
**Duplicate attempts contained:** {evidence['duplicate_attempts']}<br>
**Evidence digest:** `{run['evidence_sha256']}`

## Faults

{chr(10).join(f'- {fault}' for fault in run['faults'])}

## Business invariants

{chr(10).join(f'- {"PASS" if passed else "FAIL"}: {name}' for name,passed in result['checks'].items())}

## Evidence boundary

Synthetic controlled experiment; not observed production performance or a guarantee of future recovery.
"""


def dumps(data: Any) -> str: return json.dumps(data,indent=2)+"\n"
