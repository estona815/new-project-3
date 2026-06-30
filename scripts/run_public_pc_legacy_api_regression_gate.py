#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.harness.public_pc_legacy_api_regression_gate import build_public_pc_legacy_api_regression_gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate public-PC legacy REAPER API risks against current fail-closed policy.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--legacy-fixture-plan-path", type=Path)
    parser.add_argument("--require-passed", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_public_pc_legacy_api_regression_gate(
        project_name=args.project_name,
        output_dir=args.output_dir,
        legacy_fixture_plan_path=args.legacy_fixture_plan_path,
    )
    summary = {
        "status": gate.get("status"),
        "passed": gate.get("passed"),
        "records_total": gate.get("records_total"),
        "policy": gate.get("policy", {}),
        "readiness": gate.get("readiness", {}),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/public_pc_legacy_api_regression_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/public_pc_legacy_api_regression_gate.md"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if gate.get("passed") or not args.require_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
