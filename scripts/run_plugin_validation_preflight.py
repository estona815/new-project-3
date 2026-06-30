#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_validation_preflight import build_plugin_validation_preflight


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inventory-only plugin validation preflight.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--reaper-app", type=Path, default=Path("/Applications") / "REAPER.app")
    parser.add_argument("--reaper-resource-dir", type=Path, default=Path.home() / "Library" / "Application Support" / "REAPER")
    parser.add_argument("--plugin-readiness", type=Path, default=None)
    parser.add_argument("--validation-reports-dir", type=Path, default=None)
    parser.add_argument("--extra-plugin-dir", action="append", type=Path, default=[])
    parser.add_argument("--require-safe-write", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    preflight = build_plugin_validation_preflight(
        project_name=args.project_name,
        output_dir=args.output_dir,
        reaper_app=args.reaper_app,
        reaper_resource_dir=args.reaper_resource_dir,
        plugin_readiness_path=args.plugin_readiness,
        validation_reports_dir=args.validation_reports_dir,
        extra_plugin_dirs=args.extra_plugin_dir,
    )
    summary = {
        "status": preflight.get("status"),
        "safe_to_write_parameters": preflight.get("summary", {}).get("safe_to_write_parameters", False),
        "summary": preflight.get("summary", {}),
        "blockers": preflight.get("blockers", []),
        "warnings": preflight.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/plugin_validation_preflight.json"),
        "report_md": str(args.output_dir / "eval_reports/plugin_validation_preflight.md"),
    }
    if args.verbose:
        summary["preflight"] = preflight
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.require_safe_write and not summary["safe_to_write_parameters"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
