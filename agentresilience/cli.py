from __future__ import annotations

import argparse
import json
from pathlib import Path

from .economics import calculate
from .engine import load_experiment, run
from .exporters import dumps, junit, markdown, sarif
from .metrics import summarize


def write(path: str, content: str) -> None: Path(path).write_text(content)


def main() -> None:
    parser=argparse.ArgumentParser(prog="agentresilience",description="AI agent reliability and operational resilience testing")
    sub=parser.add_subparsers(dest="command",required=True)
    execute=sub.add_parser("run"); execute.add_argument("experiment"); execute.add_argument("--output",required=True); execute.add_argument("--junit"); execute.add_argument("--sarif"); execute.add_argument("--brief"); execute.add_argument("--unsafe-idempotency",action="store_true")
    metrics=sub.add_parser("metrics"); metrics.add_argument("reports",nargs="+"); metrics.add_argument("--output",required=True)
    economics=sub.add_parser("economics"); economics.add_argument("inputs"); economics.add_argument("--output",required=True)
    args=parser.parse_args()
    if args.command=="economics": write(args.output,dumps(calculate(json.loads(Path(args.inputs).read_text())))); return
    if args.command=="metrics": write(args.output,dumps(summarize([json.loads(Path(p).read_text()) for p in args.reports]))); return
    result=run(load_experiment(args.experiment),args.unsafe_idempotency); write(args.output,dumps(result))
    if args.junit: write(args.junit,junit(result)+"\n")
    if args.sarif: write(args.sarif,dumps(sarif(result)))
    if args.brief: write(args.brief,markdown(result))
    if not result["result"]["passed"]: raise SystemExit(2)


if __name__=="__main__": main()
