#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.harness.mix_master_quality_harness import build_mix_master_quality_harness


def default_handoff_root() -> Path:
    configured = os.environ.get("REAPER_AUTOMIX_HANDOFF_ROOT")
    if configured:
        return Path(configured)
    return ROOT / "reaper-auto-mix-handoff"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a non-render high-quality mix/master readiness harness from the REAPER handoff package.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument(
        "--handoff-root",
        type=Path,
        default=default_handoff_root(),
        help="Extracted package root. Defaults to REAPER_AUTOMIX_HANDOFF_ROOT or ./reaper-auto-mix-handoff.",
    )
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_mix_master_quality_harness(
        project_name=args.project_name,
        output_dir=args.output_dir,
        handoff_root=args.handoff_root,
        workspace_root=args.workspace_root,
    )
    summary = {
        "status": "planning_ready" if audit.get("passed") else "blocked",
        "passed": audit.get("passed"),
        "ready_for_high_quality_offline_planning": audit.get("readiness", {}).get("ready_for_high_quality_offline_planning"),
        "ready_for_reaper_dry_run": audit.get("readiness", {}).get("ready_for_reaper_dry_run"),
        "ready_for_applied_mix_or_master_parameter_writes": audit.get("readiness", {}).get(
            "ready_for_applied_mix_or_master_parameter_writes"
        ),
        "ready_for_delivery_claims": audit.get("readiness", {}).get("ready_for_delivery_claims"),
        "blockers": audit.get("blockers", []),
        "warnings": audit.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/mix_master_quality_harness.json"),
        "report_md": str(args.output_dir / "eval_reports/mix_master_quality_harness.md"),
        "plan_json": str(args.output_dir / "chain_plans/high_quality_mix_master_readiness_plan.json"),
    }
    if args.verbose:
        summary["audit"] = audit
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if audit.get("passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
