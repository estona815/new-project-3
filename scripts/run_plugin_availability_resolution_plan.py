#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_availability_resolution_plan import build_plugin_availability_resolution_plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create operator resolution requests for unavailable plugins.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--action-plan", type=Path, default=None)
    parser.add_argument("--capability-catalog", type=Path, default=None)
    parser.add_argument("--require-resolved", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_plugin_availability_resolution_plan(
        project_name=args.project_name,
        output_dir=args.output_dir,
        action_plan_path=args.action_plan,
        catalog_path=args.capability_catalog,
    )
    summary = {
        "status": plan.get("status"),
        "unavailable_plugins_total": plan.get("unavailable_plugins_total"),
        "pending_operator_decisions": plan.get("pending_operator_decisions", []),
        "blockers": plan.get("blockers", []),
        "warnings": plan.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/plugin_availability_resolution_plan.json"),
        "report_md": str(args.output_dir / "eval_reports/plugin_availability_resolution_plan.md"),
        "request_md": str(args.output_dir / "review/plugin_availability_resolution_request.md"),
        "disable_manifest_template": str(args.output_dir / "review/plugin_availability_disable_manifest_template.json"),
    }
    if args.verbose:
        summary["plan"] = plan
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    resolved = not plan.get("pending_operator_decisions") and not plan.get("blockers")
    return 0 if not args.require_resolved or resolved else 2


if __name__ == "__main__":
    raise SystemExit(main())
