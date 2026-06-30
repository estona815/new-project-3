#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_availability_operator_decision_firewall_gate import (
    build_plugin_availability_operator_decision_firewall_gate,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit plugin availability operator decision candidate/accepted manifest separation.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--resolution-plan", type=Path)
    parser.add_argument("--operator-decision-package", type=Path)
    parser.add_argument("--decision-gate", type=Path)
    parser.add_argument("--candidate-manifest", type=Path)
    parser.add_argument("--accepted-manifest", type=Path)
    parser.add_argument("--require-passed", action="store_true")
    parser.add_argument("--require-accepted-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_plugin_availability_operator_decision_firewall_gate(
        project_name=args.project_name,
        output_dir=args.output_dir,
        resolution_plan_path=args.resolution_plan,
        operator_decision_package_path=args.operator_decision_package,
        decision_gate_path=args.decision_gate,
        candidate_manifest_path=args.candidate_manifest,
        accepted_manifest_path=args.accepted_manifest,
    )
    readiness = gate.get("readiness", {})
    summary = {
        "status": gate.get("status"),
        "passed": gate.get("passed"),
        "readiness": readiness,
        "counts": gate.get("counts", {}),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/plugin_availability_operator_decision_firewall_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/plugin_availability_operator_decision_firewall_gate.md"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.require_accepted_ready and not readiness.get("accepted_operator_manifest_ready", False):
        return 2
    if args.require_passed and not gate.get("passed", False):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
