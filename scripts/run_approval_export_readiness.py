#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.approval_export_readiness import build_approval_export_readiness


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit accepted source, A/B preview, render, and human approval readiness.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_approval_export_readiness(project_name=args.project_name, output_dir=args.output_dir)
    summary = {
        "status": audit.get("readiness_status"),
        "ready_for_delivery_request": audit.get("ready_for_delivery_request"),
        "ready_for_human_approval_request": audit.get("ready_for_human_approval_request"),
        "blockers": audit.get("blockers", []),
        "warnings": audit.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/approval_export_readiness.json"),
        "report_md": str(args.output_dir / "eval_reports/approval_export_readiness.md"),
        "approval_request_md": str(args.output_dir / "review/final_approval_request.md"),
    }
    if args.verbose:
        summary["audit"] = audit
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_ready or audit.get("ready_for_delivery_request") else 2


if __name__ == "__main__":
    raise SystemExit(main())
