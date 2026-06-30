#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_semantic_validation_runtime_handoff_packet_gate import (
    build_plugin_semantic_validation_runtime_handoff_packet_gate,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit the REAPER runtime semantic validation operator handoff packet.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--local-device-qc", type=Path)
    parser.add_argument("--queue", type=Path)
    parser.add_argument("--collection-package", type=Path)
    parser.add_argument("--collector-package", type=Path)
    parser.add_argument("--safety-audit", type=Path)
    parser.add_argument("--operator-readiness", type=Path)
    parser.add_argument("--availability-decision", type=Path)
    parser.add_argument("--runtime-evidence-gate", type=Path)
    parser.add_argument("--require-partial-ready", action="store_true")
    parser.add_argument("--require-complete-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_plugin_semantic_validation_runtime_handoff_packet_gate(
        project_name=args.project_name,
        output_dir=args.output_dir,
        local_device_qc_path=args.local_device_qc,
        queue_path=args.queue,
        collection_package_path=args.collection_package,
        collector_package_path=args.collector_package,
        safety_audit_path=args.safety_audit,
        operator_readiness_path=args.operator_readiness,
        availability_decision_path=args.availability_decision,
        runtime_evidence_gate_path=args.runtime_evidence_gate,
    )
    readiness = gate.get("readiness", {})
    summary = {
        "status": gate.get("status"),
        "passed": gate.get("passed"),
        "readiness": readiness,
        "counts": gate.get("counts", {}),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/plugin_semantic_validation_runtime_handoff_packet_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/plugin_semantic_validation_runtime_handoff_packet_gate.md"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.require_complete_ready and not readiness.get("complete_operator_runtime_handoff_packet_ready", False):
        return 2
    if args.require_partial_ready and not readiness.get("operator_runtime_handoff_packet_ready", False):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
