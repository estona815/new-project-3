#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.reaper_runtime_collection_operator_readiness_gate import (
    build_reaper_runtime_collection_operator_readiness_gate,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the pre-run REAPER runtime collection operator readiness gate.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--local-device-qc", type=Path, default=None)
    parser.add_argument("--collector-package", type=Path, default=None)
    parser.add_argument("--safety-audit", type=Path, default=None)
    parser.add_argument("--availability-decision", type=Path, default=None)
    parser.add_argument("--queue-payload", type=Path, default=None)
    parser.add_argument("--require-partial-ready", action="store_true")
    parser.add_argument("--require-complete-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_reaper_runtime_collection_operator_readiness_gate(
        project_name=args.project_name,
        output_dir=args.output_dir,
        local_device_qc_path=args.local_device_qc,
        collector_package_path=args.collector_package,
        safety_audit_path=args.safety_audit,
        availability_decision_path=args.availability_decision,
        queue_payload_path=args.queue_payload,
    )
    summary = {
        "status": gate.get("status"),
        "passed": gate.get("passed"),
        "ready_for_partial_operator_runtime_collection": gate.get("ready_for_partial_operator_runtime_collection"),
        "ready_for_complete_operator_runtime_collection": gate.get("ready_for_complete_operator_runtime_collection"),
        "safe_to_run_lua_collector": gate.get("safe_to_run_lua_collector"),
        "safe_to_write_parameters": gate.get("safe_to_write_parameters", False),
        "collector_jobs_total": gate.get("collector_jobs_total"),
        "blocked_queue_jobs_total": gate.get("blocked_queue_jobs_total"),
        "availability_missing_decisions": gate.get("availability_missing_decisions", []),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/reaper_runtime_collection_operator_readiness.json"),
        "report_md": str(args.output_dir / "eval_reports/reaper_runtime_collection_operator_readiness.md"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.require_complete_ready and not gate.get("ready_for_complete_operator_runtime_collection", False):
        return 2
    if args.require_partial_ready and not gate.get("ready_for_partial_operator_runtime_collection", False):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
