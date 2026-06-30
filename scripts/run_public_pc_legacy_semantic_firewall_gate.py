#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.harness.public_pc_legacy_semantic_firewall_gate import (
    build_public_pc_legacy_semantic_firewall_gate,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ensure public-PC legacy fixtures cannot become plugin semantic validation evidence."
    )
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--legacy-fixture-plan-path", type=Path)
    parser.add_argument("--legacy-api-regression-gate-path", type=Path)
    parser.add_argument("--semantic-report-path", type=Path, action="append", default=None)
    parser.add_argument("--validation-reports-dir", type=Path)
    parser.add_argument("--require-passed", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_public_pc_legacy_semantic_firewall_gate(
        project_name=args.project_name,
        output_dir=args.output_dir,
        legacy_fixture_plan_path=args.legacy_fixture_plan_path,
        legacy_api_regression_gate_path=args.legacy_api_regression_gate_path,
        semantic_report_paths=args.semantic_report_path,
        validation_reports_dir=args.validation_reports_dir,
    )
    summary = {
        "status": gate.get("status"),
        "passed": gate.get("passed"),
        "legacy_records_total": gate.get("legacy_records_total"),
        "legacy_negative_records_total": gate.get("legacy_negative_records_total"),
        "semantic_reports_scanned_total": gate.get("semantic_reports_scanned_total"),
        "readiness": gate.get("readiness", {}),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/public_pc_legacy_semantic_firewall_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/public_pc_legacy_semantic_firewall_gate.md"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if gate.get("passed") or not args.require_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
