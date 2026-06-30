#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.harness.public_pc_legacy_fixture_plan import build_public_pc_legacy_fixture_plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a report-only fixture plan from a public-PC REAPER handoff bundle.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--bundle-path", type=Path)
    parser.add_argument("--handoff-audit-path", type=Path)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_public_pc_legacy_fixture_plan(
        project_name=args.project_name,
        output_dir=args.output_dir,
        bundle_path=args.bundle_path,
        handoff_audit_path=args.handoff_audit_path,
    )
    summary = {
        "status": plan.get("status"),
        "passed": plan.get("passed"),
        "summary": plan.get("summary", {}),
        "readiness": plan.get("readiness", {}),
        "blockers": plan.get("blockers", []),
        "warnings": plan.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/public_pc_legacy_fixture_plan.json"),
        "report_md": str(args.output_dir / "eval_reports/public_pc_legacy_fixture_plan.md"),
    }
    if args.verbose:
        summary["plan"] = plan
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if plan.get("passed") or not args.require_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
