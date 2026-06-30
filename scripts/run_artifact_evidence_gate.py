#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.artifact_evidence_gate import build_artifact_evidence_gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate artifact evidence before artifact-focused processing.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--require-measured", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_artifact_evidence_gate(project_name=args.project_name, output_dir=args.output_dir, manifest_path=args.manifest)
    summary = {
        "status": "ready_for_artifact_review" if gate.get("ready_for_artifact_review") else "blocked",
        "artifact_evidence_established": gate.get("artifact_evidence_established"),
        "measured_artifact_metrics_established": gate.get("measured_artifact_metrics_established"),
        "ready_for_artifact_review": gate.get("ready_for_artifact_review"),
        "safe_to_run_artifact_suppression": gate.get("safe_to_run_artifact_suppression"),
        "summary": gate.get("summary", {}),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/artifact_evidence_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/artifact_evidence_gate.md"),
        "template_json": str(args.output_dir / "review/artifact_evidence_manifest_template.json"),
        "request_md": str(args.output_dir / "review/artifact_evidence_request.md"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_measured or gate.get("measured_artifact_metrics_established") else 2


if __name__ == "__main__":
    raise SystemExit(main())
