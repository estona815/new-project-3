#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_semantic_validation_runtime_collection_package import (
    build_plugin_semantic_validation_runtime_collection_package,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a REAPER runtime collection package for queued plugin semantic validation jobs.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--queue", type=Path, default=None)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package = build_plugin_semantic_validation_runtime_collection_package(
        project_name=args.project_name,
        output_dir=args.output_dir,
        queue_path=args.queue,
    )
    summary = {
        "status": package.get("status"),
        "ready_for_runtime_collection": package.get("ready_for_runtime_collection"),
        "ready_for_runtime_evidence_gate": package.get("ready_for_runtime_evidence_gate"),
        "collection_jobs_total": package.get("collection_jobs_total"),
        "target_reports_existing_total": package.get("target_reports_existing_total"),
        "target_reports_missing_total": package.get("target_reports_missing_total"),
        "blocked_queue_jobs_total": package.get("blocked_queue_jobs_total"),
        "safe_to_write_parameters": package.get("safe_to_write_parameters", False),
        "blockers": package.get("blockers", []),
        "warnings": package.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/plugin_semantic_validation_runtime_collection_package.json"),
        "report_md": str(args.output_dir / "eval_reports/plugin_semantic_validation_runtime_collection_package.md"),
        "checklist_md": str(args.output_dir / "review/plugin_semantic_validation_runtime_collection_checklist.md"),
        "manifest_candidate": str(args.output_dir / "review/plugin_semantic_validation_runtime_manifest_candidate.json"),
        "report_template_dir": str(args.output_dir / "review/plugin_semantic_validation_runtime_report_templates"),
    }
    if args.verbose:
        summary["package"] = package
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_ready or package.get("ready_for_runtime_collection", False) else 2


if __name__ == "__main__":
    raise SystemExit(main())
