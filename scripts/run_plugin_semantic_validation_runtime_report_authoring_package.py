#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_semantic_validation_runtime_report_authoring_package import (
    build_plugin_semantic_validation_runtime_report_authoring_package,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build review-only report authoring templates from accepted raw runtime observations.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--observation-gate", type=Path, default=None)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package = build_plugin_semantic_validation_runtime_report_authoring_package(
        project_name=args.project_name,
        output_dir=args.output_dir,
        observation_gate_path=args.observation_gate,
    )
    summary = {
        "status": package.get("status"),
        "runtime_report_authoring_package_ready": package.get("runtime_report_authoring_package_ready"),
        "ready_for_manual_report_authoring": package.get("ready_for_manual_report_authoring"),
        "ready_for_runtime_evidence_gate": package.get("ready_for_runtime_evidence_gate"),
        "accepted_observations_total": package.get("accepted_observations_total"),
        "templates_total": package.get("templates_total"),
        "safe_to_write_parameters": package.get("safe_to_write_parameters", False),
        "creates_validation_reports": package.get("creates_validation_reports", False),
        "writes_analysis_reports": package.get("writes_analysis_reports", False),
        "blockers": package.get("blockers", []),
        "warnings": package.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/plugin_semantic_validation_runtime_report_authoring_package.json"),
        "report_md": str(args.output_dir / "eval_reports/plugin_semantic_validation_runtime_report_authoring_package.md"),
        "checklist_md": str(args.output_dir / "review/plugin_semantic_validation_runtime_report_authoring_checklist.md"),
        "request_md": str(args.output_dir / "review/plugin_semantic_validation_runtime_report_authoring_package_request.md"),
        "template_dir": str(args.output_dir / "review/plugin_semantic_validation_runtime_report_authoring_templates"),
    }
    if args.verbose:
        summary["package"] = package
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_ready or package.get("runtime_report_authoring_package_ready", False) else 2


if __name__ == "__main__":
    raise SystemExit(main())
