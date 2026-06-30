#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_semantic_validation_collection_plan import build_plugin_semantic_validation_collection_plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a REAPER-observed plugin semantic validation collection plan.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--action-plan", type=Path, default=None)
    parser.add_argument("--semantic-gate", type=Path, default=None)
    parser.add_argument("--decision-gate", type=Path, default=None)
    parser.add_argument("--require-no-open-jobs", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_plugin_semantic_validation_collection_plan(
        project_name=args.project_name,
        output_dir=args.output_dir,
        action_plan_path=args.action_plan,
        semantic_gate_path=args.semantic_gate,
        decision_gate_path=args.decision_gate,
    )
    summary = {
        "status": plan.get("status"),
        "semantic_validation_ready": plan.get("semantic_validation_ready"),
        "open_jobs_total": plan.get("open_jobs_total"),
        "collectable_jobs_total": plan.get("collectable_jobs_total"),
        "decision_blocked_jobs_total": plan.get("decision_blocked_jobs_total"),
        "ready_to_collect_some_in_reaper": plan.get("ready_to_collect_some_in_reaper"),
        "all_jobs_resolved": plan.get("all_jobs_resolved"),
        "next_plugin": (plan.get("next_collection_job") or {}).get("plugin_name", ""),
        "next_collection_action": (plan.get("next_collection_job") or {}).get("collection_action", ""),
        "safe_to_write_parameters": plan.get("safe_to_write_parameters", False),
        "blockers": plan.get("blockers", []),
        "warnings": plan.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/plugin_semantic_validation_collection_plan.json"),
        "report_md": str(args.output_dir / "eval_reports/plugin_semantic_validation_collection_plan.md"),
        "request_md": str(args.output_dir / "review/plugin_semantic_validation_collection_request.md"),
        "manifest_template": str(args.output_dir / "review/plugin_semantic_validation_collection_manifest_template.json"),
    }
    if args.verbose:
        summary["plan"] = plan
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_no_open_jobs or plan.get("all_jobs_resolved", False) else 2


if __name__ == "__main__":
    raise SystemExit(main())
