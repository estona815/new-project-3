#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_semantic_validation_runtime_evidence_gate import (
    build_plugin_semantic_validation_runtime_evidence_gate,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate runtime evidence for queued plugin semantic validation jobs.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--queue", type=Path, default=None)
    parser.add_argument("--runtime-manifest", type=Path, default=None)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_plugin_semantic_validation_runtime_evidence_gate(
        project_name=args.project_name,
        output_dir=args.output_dir,
        queue_path=args.queue,
        runtime_manifest_path=args.runtime_manifest,
    )
    summary = {
        "status": gate.get("status"),
        "runtime_evidence_ready": gate.get("runtime_evidence_ready"),
        "ready_for_semantic_gate_rerun": gate.get("ready_for_semantic_gate_rerun"),
        "queue_jobs_total": gate.get("queue_jobs_total"),
        "accepted_jobs_total": gate.get("accepted_jobs_total"),
        "blocked_jobs_total": gate.get("blocked_jobs_total"),
        "blocked_queue_jobs_total": gate.get("blocked_queue_jobs_total"),
        "safe_to_write_parameters": gate.get("safe_to_write_parameters", False),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/plugin_semantic_validation_runtime_evidence_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/plugin_semantic_validation_runtime_evidence_gate.md"),
        "request_md": str(args.output_dir / "review/plugin_semantic_validation_runtime_evidence_request.md"),
        "runtime_manifest": str(args.runtime_manifest or args.output_dir / "review/plugin_semantic_validation_runtime_manifest.json"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_ready or gate.get("runtime_evidence_ready", False) else 2


if __name__ == "__main__":
    raise SystemExit(main())
