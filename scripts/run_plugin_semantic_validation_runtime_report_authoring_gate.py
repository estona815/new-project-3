#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_semantic_validation_runtime_report_authoring_gate import (
    build_plugin_semantic_validation_runtime_report_authoring_gate,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate review-only authored plugin validation report candidates before operator promotion.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--authoring-package", type=Path, default=None)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_plugin_semantic_validation_runtime_report_authoring_gate(
        project_name=args.project_name,
        output_dir=args.output_dir,
        authoring_package_path=args.authoring_package,
    )
    summary = {
        "status": gate.get("status"),
        "authoring_candidates_ready": gate.get("authoring_candidates_ready"),
        "ready_for_operator_promotion": gate.get("ready_for_operator_promotion"),
        "ready_for_runtime_evidence_gate": gate.get("ready_for_runtime_evidence_gate"),
        "templates_total": gate.get("templates_total"),
        "candidate_reports_total": gate.get("candidate_reports_total"),
        "accepted_candidates_total": gate.get("accepted_candidates_total"),
        "blocked_candidates_total": gate.get("blocked_candidates_total"),
        "safe_to_write_parameters": gate.get("safe_to_write_parameters", False),
        "writes_analysis_reports": gate.get("writes_analysis_reports", False),
        "candidate_reports_are_validation_evidence": gate.get("candidate_reports_are_validation_evidence", False),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/plugin_semantic_validation_runtime_report_authoring_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/plugin_semantic_validation_runtime_report_authoring_gate.md"),
        "promotion_checklist_md": str(args.output_dir / "review/plugin_semantic_validation_runtime_report_promotion_checklist.md"),
        "promotion_request_md": str(args.output_dir / "review/plugin_semantic_validation_runtime_report_promotion_request.md"),
        "manifest_candidate": str(args.output_dir / "review/plugin_semantic_validation_runtime_manifest_candidate_from_authoring.json"),
        "candidate_dir": str(args.output_dir / "review/plugin_semantic_validation_runtime_report_authoring_candidates"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_ready or gate.get("authoring_candidates_ready", False) else 2


if __name__ == "__main__":
    raise SystemExit(main())
