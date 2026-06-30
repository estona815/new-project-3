#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_semantic_validation_runtime_observation_gate import (
    build_plugin_semantic_validation_runtime_observation_gate,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate raw REAPER runtime observations before manual semantic report authoring.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--collector-package", type=Path, default=None)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_plugin_semantic_validation_runtime_observation_gate(
        project_name=args.project_name,
        output_dir=args.output_dir,
        collector_package_path=args.collector_package,
    )
    summary = {
        "status": gate.get("status"),
        "runtime_observations_ready": gate.get("runtime_observations_ready"),
        "ready_for_manual_report_authoring": gate.get("ready_for_manual_report_authoring"),
        "ready_for_runtime_evidence_gate": gate.get("ready_for_runtime_evidence_gate"),
        "collector_jobs_total": gate.get("collector_jobs_total"),
        "accepted_observations_total": gate.get("accepted_observations_total"),
        "blocked_observations_total": gate.get("blocked_observations_total"),
        "blocked_queue_jobs_total": gate.get("blocked_queue_jobs_total"),
        "safe_to_write_parameters": gate.get("safe_to_write_parameters", False),
        "creates_validation_reports": gate.get("creates_validation_reports", False),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/plugin_semantic_validation_runtime_observation_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/plugin_semantic_validation_runtime_observation_gate.md"),
        "observation_request_md": str(args.output_dir / "review/plugin_semantic_validation_runtime_observation_request.md"),
        "report_authoring_request_md": str(args.output_dir / "review/plugin_semantic_validation_runtime_report_authoring_request.md"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_ready or gate.get("runtime_observations_ready", False) else 2


if __name__ == "__main__":
    raise SystemExit(main())
