#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.reaper_runtime_collector_safety_audit import (
    build_reaper_runtime_collector_safety_audit,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Static safety audit for the generated REAPER runtime collector Lua package.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--lua-collector", type=Path, default=None)
    parser.add_argument("--queue-payload", type=Path, default=None)
    parser.add_argument("--collector-package", type=Path, default=None)
    parser.add_argument("--require-passed", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_reaper_runtime_collector_safety_audit(
        project_name=args.project_name,
        output_dir=args.output_dir,
        lua_collector_path=args.lua_collector,
        queue_payload_path=args.queue_payload,
        collector_package_path=args.collector_package,
    )
    summary = {
        "status": audit.get("status"),
        "passed": audit.get("passed"),
        "safe_for_operator_runtime_collection": audit.get("safe_for_operator_runtime_collection"),
        "mutation_model": audit.get("mutation_model", {}),
        "disallowed_reaper_calls": audit.get("disallowed_reaper_calls", []),
        "blockers": audit.get("blockers", []),
        "warnings": audit.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/reaper_runtime_collector_safety_audit.json"),
        "report_md": str(args.output_dir / "eval_reports/reaper_runtime_collector_safety_audit.md"),
    }
    if args.verbose:
        summary["audit"] = audit
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_passed or audit.get("passed", False) else 2


if __name__ == "__main__":
    raise SystemExit(main())
