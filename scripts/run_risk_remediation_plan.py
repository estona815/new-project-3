#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.risk_remediation_planner import build_risk_remediation_plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a dry-run remediation plan from the open risk register.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_risk_remediation_plan(project_name=args.project_name, output_dir=args.output_dir)
    summary = {
        "status": plan.get("status"),
        "dry_run_only": plan.get("dry_run_only"),
        "open_risk_total": plan.get("open_risk_total"),
        "actions_total": plan.get("actions_total"),
        "blockers": plan.get("blockers", []),
        "warnings": plan.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/risk_remediation_plan.json"),
        "report_md": str(args.output_dir / "eval_reports/risk_remediation_plan.md"),
    }
    if args.verbose:
        summary["plan"] = plan
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not plan.get("blockers") else 2


if __name__ == "__main__":
    raise SystemExit(main())
