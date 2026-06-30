#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_semantic_validation_queue import build_plugin_semantic_validation_queue


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package collectable plugin semantic validation jobs into a REAPER runtime queue.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--collection-plan", type=Path, default=None)
    parser.add_argument("--require-queue-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    queue = build_plugin_semantic_validation_queue(
        project_name=args.project_name,
        output_dir=args.output_dir,
        collection_plan_path=args.collection_plan,
    )
    summary = {
        "status": queue.get("status"),
        "ready_to_run_reaper_collection": queue.get("ready_to_run_reaper_collection"),
        "queue_jobs_total": queue.get("queue_jobs_total"),
        "blocked_jobs_total": queue.get("blocked_jobs_total"),
        "next_job_id": (queue.get("next_queue_job") or {}).get("job_id", ""),
        "next_plugin": (queue.get("next_queue_job") or {}).get("plugin_name", ""),
        "safe_to_write_parameters": queue.get("safe_to_write_parameters", False),
        "blockers": queue.get("blockers", []),
        "warnings": queue.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/plugin_semantic_validation_queue.json"),
        "report_md": str(args.output_dir / "eval_reports/plugin_semantic_validation_queue.md"),
        "request_md": str(args.output_dir / "review/plugin_semantic_validation_queue_request.md"),
        "runtime_manifest_template": str(args.output_dir / "review/plugin_semantic_validation_runtime_manifest_template.json"),
    }
    if args.verbose:
        summary["queue"] = queue
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_queue_ready or queue.get("ready_to_run_reaper_collection", False) else 2


if __name__ == "__main__":
    raise SystemExit(main())
