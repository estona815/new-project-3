#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.harness.local_device_qc import build_local_device_qc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run report-only local device QC for REAPER AutoMix automation readiness.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--reaper-app", type=Path, default=Path("/Applications") / "REAPER.app")
    parser.add_argument("--reaper-resource-dir", type=Path, default=Path.home() / "Library" / "Application Support" / "REAPER")
    parser.add_argument("--require-local-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    qc = build_local_device_qc(
        project_name=args.project_name,
        output_dir=args.output_dir,
        workspace_root=args.workspace_root,
        reaper_app=args.reaper_app,
        reaper_resource_dir=args.reaper_resource_dir,
    )
    summary = {
        "status": qc.get("status"),
        "passed": qc.get("passed"),
        "readiness": qc.get("readiness", {}),
        "blockers": qc.get("blockers", []),
        "warnings": qc.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/local_device_qc.json"),
        "report_md": str(args.output_dir / "eval_reports/local_device_qc.md"),
    }
    if args.verbose:
        summary["qc"] = qc
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if qc.get("passed") or not args.require_local_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
