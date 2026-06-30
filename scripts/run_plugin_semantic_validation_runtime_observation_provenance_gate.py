#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_semantic_validation_runtime_observation_provenance_gate import (
    build_plugin_semantic_validation_runtime_observation_provenance_gate,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit runtime observation provenance against the current collector packet.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--collector-package", type=Path)
    parser.add_argument("--handoff-packet", type=Path)
    parser.add_argument("--observation-gate", type=Path)
    parser.add_argument("--local-device-qc", type=Path)
    parser.add_argument("--safety-audit", type=Path)
    parser.add_argument("--require-packet-ready", action="store_true")
    parser.add_argument("--require-passed", action="store_true", help="Alias for --require-packet-ready.")
    parser.add_argument("--require-observed-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_plugin_semantic_validation_runtime_observation_provenance_gate(
        project_name=args.project_name,
        output_dir=args.output_dir,
        collector_package_path=args.collector_package,
        handoff_packet_path=args.handoff_packet,
        observation_gate_path=args.observation_gate,
        local_device_qc_path=args.local_device_qc,
        safety_audit_path=args.safety_audit,
    )
    readiness = gate.get("readiness", {})
    summary = {
        "status": gate.get("status"),
        "passed": gate.get("passed"),
        "readiness": readiness,
        "counts": gate.get("counts", {}),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.md"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.require_observed_ready and not readiness.get("observed_runtime_provenance_ready", False):
        return 2
    if (args.require_packet_ready or args.require_passed) and not readiness.get(
        "expected_observation_provenance_packet_ready", False
    ):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
