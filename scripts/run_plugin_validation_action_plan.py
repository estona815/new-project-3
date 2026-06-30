#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_validation_action_plan import build_plugin_validation_action_plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create plugin-level next actions from validation preflight and semantic gate evidence.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--preflight", type=Path, default=None)
    parser.add_argument("--semantic-gate", type=Path, default=None)
    parser.add_argument("--require-safe-write", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_plugin_validation_action_plan(
        project_name=args.project_name,
        output_dir=args.output_dir,
        preflight_path=args.preflight,
        semantic_gate_path=args.semantic_gate,
    )
    summary = {
        "status": plan.get("status"),
        "safe_to_write_parameters": plan.get("summary", {}).get("safe_to_write_parameters", False),
        "required_plugins_total": plan.get("required_plugins_total"),
        "plugin_actions_total": plan.get("plugin_actions_total"),
        "next_plugin_action": plan.get("next_plugin_action", {}).get("action_id", ""),
        "next_plugin": plan.get("next_plugin_action", {}).get("plugin_name", ""),
        "blockers": plan.get("blockers", []),
        "warnings": plan.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/plugin_validation_action_plan.json"),
        "report_md": str(args.output_dir / "eval_reports/plugin_validation_action_plan.md"),
        "request_md": str(args.output_dir / "review/plugin_validation_action_request.md"),
    }
    if args.verbose:
        summary["plan"] = plan
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_safe_write or summary["safe_to_write_parameters"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
