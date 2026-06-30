#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_semantic_validation_runtime_collector_package import (
    build_plugin_semantic_validation_runtime_collector_package,
)
from automix.plugins.reaper_runtime_collector_safety_audit import (
    build_reaper_runtime_collector_safety_audit,
)
from automix.plugins.reaper_runtime_collection_operator_readiness_gate import (
    build_reaper_runtime_collection_operator_readiness_gate,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a REAPER Lua raw-observation collector for queued plugin semantic validation jobs.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--collection-package", type=Path, default=None)
    parser.add_argument("--queue", type=Path, default=None)
    parser.add_argument("--skip-safety-audit", action="store_true")
    parser.add_argument("--skip-operator-readiness", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package = build_plugin_semantic_validation_runtime_collector_package(
        project_name=args.project_name,
        output_dir=args.output_dir,
        collection_package_path=args.collection_package,
        queue_path=args.queue,
    )
    safety_audit = None
    if not args.skip_safety_audit:
        safety_audit = build_reaper_runtime_collector_safety_audit(
            project_name=args.project_name,
            output_dir=args.output_dir,
            lua_collector_path=Path(package.get("lua_collector_script_path", "")),
            queue_payload_path=Path(package.get("queue_payload_path", "")),
            collector_package_path=args.output_dir / "eval_reports/plugin_semantic_validation_runtime_collector_package.json",
        )
    operator_readiness = None
    if not args.skip_operator_readiness:
        operator_readiness = build_reaper_runtime_collection_operator_readiness_gate(
            project_name=args.project_name,
            output_dir=args.output_dir,
        )
    summary = {
        "status": package.get("status"),
        "ready_for_reaper_runtime_collection": package.get("ready_for_reaper_runtime_collection"),
        "ready_for_runtime_evidence_gate": package.get("ready_for_runtime_evidence_gate"),
        "collector_jobs_total": package.get("collector_jobs_total"),
        "blocked_queue_jobs_total": package.get("blocked_queue_jobs_total"),
        "safe_to_write_parameters": package.get("safe_to_write_parameters", False),
        "creates_validation_reports": package.get("creates_validation_reports", False),
        "requires_collector_safety_audit": package.get("requires_collector_safety_audit", True),
        "collector_safety_audit_passed": safety_audit.get("passed") if safety_audit else None,
        "safe_for_operator_runtime_collection": safety_audit.get("safe_for_operator_runtime_collection") if safety_audit else None,
        "operator_readiness_status": operator_readiness.get("status") if operator_readiness else None,
        "ready_for_partial_operator_runtime_collection": operator_readiness.get("ready_for_partial_operator_runtime_collection") if operator_readiness else None,
        "ready_for_complete_operator_runtime_collection": operator_readiness.get("ready_for_complete_operator_runtime_collection") if operator_readiness else None,
        "blockers": package.get("blockers", []),
        "warnings": package.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/plugin_semantic_validation_runtime_collector_package.json"),
        "report_md": str(args.output_dir / "eval_reports/plugin_semantic_validation_runtime_collector_package.md"),
        "lua_collector": str(args.output_dir / "reaper_scripts/collect_plugin_semantic_validation_runtime.lua"),
        "queue_payload": str(args.output_dir / "reaper_scripts/plugin_semantic_validation_runtime_queue.json"),
        "observation_template": str(args.output_dir / "reaper_scripts/plugin_semantic_validation_runtime_observations_template.json"),
        "operator_runbook": str(args.output_dir / "review/plugin_semantic_validation_runtime_collector_operator_runbook.md"),
        "safety_audit_json": str(args.output_dir / "eval_reports/reaper_runtime_collector_safety_audit.json"),
        "safety_audit_md": str(args.output_dir / "eval_reports/reaper_runtime_collector_safety_audit.md"),
        "operator_readiness_json": str(args.output_dir / "eval_reports/reaper_runtime_collection_operator_readiness.json"),
        "operator_readiness_md": str(args.output_dir / "eval_reports/reaper_runtime_collection_operator_readiness.md"),
    }
    if args.verbose:
        summary["package"] = package
        if safety_audit:
            summary["safety_audit"] = safety_audit
        if operator_readiness:
            summary["operator_readiness"] = operator_readiness
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_ready or package.get("ready_for_reaper_runtime_collection", False) else 2


if __name__ == "__main__":
    raise SystemExit(main())
