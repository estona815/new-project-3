#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_availability_operator_decision_package import (
    build_plugin_availability_operator_decision_package,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an operator decision package for unavailable plugin availability choices.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--resolution-plan", type=Path, default=None)
    parser.add_argument("--decision-gate", type=Path, default=None)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package = build_plugin_availability_operator_decision_package(
        project_name=args.project_name,
        output_dir=args.output_dir,
        resolution_plan_path=args.resolution_plan,
        decision_gate_path=args.decision_gate,
    )
    summary = {
        "status": package.get("status"),
        "operator_decision_package_ready": package.get("operator_decision_package_ready"),
        "availability_decisions_ready": package.get("availability_decisions_ready"),
        "required_decisions_total": package.get("required_decisions_total"),
        "accepted_decisions_total": package.get("accepted_decisions_total"),
        "missing_decisions": package.get("missing_decisions", []),
        "safe_to_write_parameters": package.get("safe_to_write_parameters", False),
        "blockers": package.get("blockers", []),
        "warnings": package.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/plugin_availability_operator_decision_package.json"),
        "report_md": str(args.output_dir / "eval_reports/plugin_availability_operator_decision_package.md"),
        "checklist_md": str(args.output_dir / "review/plugin_availability_operator_decision_checklist.md"),
        "candidate_manifest": str(args.output_dir / "review/plugin_availability_disable_manifest_candidate.json"),
        "accepted_manifest": str(args.output_dir / "review/plugin_availability_disable_manifest.json"),
    }
    if args.verbose:
        summary["package"] = package
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_ready or package.get("operator_decision_package_ready", False) else 2


if __name__ == "__main__":
    raise SystemExit(main())
