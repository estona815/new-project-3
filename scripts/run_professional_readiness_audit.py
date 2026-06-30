#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.professional_readiness_audit import build_professional_readiness_audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a fail-closed professional delivery readiness audit.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--final-delivery-requested", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_professional_readiness_audit(
        project_name=args.project_name,
        output_dir=args.output_dir,
        workspace_root=args.workspace_root,
        final_delivery_requested=args.final_delivery_requested,
    )
    summary = {
        "status": audit.get("readiness_status"),
        "ready_for_delivery": audit.get("ready_for_delivery"),
        "blockers": audit.get("blockers", []),
        "warnings": audit.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports" / "professional_readiness_audit.json"),
        "report_md": str(args.output_dir / "eval_reports" / "professional_readiness_audit.md"),
    }
    if args.verbose:
        summary["audit"] = audit
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if audit.get("ready_for_delivery") or not args.final_delivery_requested else 2


if __name__ == "__main__":
    raise SystemExit(main())
