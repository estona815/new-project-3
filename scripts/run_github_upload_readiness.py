#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.harness.github_upload_readiness import build_github_upload_readiness


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run report-only GitHub upload readiness checks for the REAPER AutoMix handoff.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_github_upload_readiness(
        project_name=args.project_name,
        output_dir=args.output_dir,
        workspace_root=args.workspace_root,
    )
    summary = {
        "status": audit.get("status"),
        "passed": audit.get("passed"),
        "readiness": audit.get("readiness", {}),
        "blockers": audit.get("blockers", []),
        "warnings": audit.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/github_upload_readiness.json"),
        "report_md": str(args.output_dir / "eval_reports/github_upload_readiness.md"),
    }
    if args.verbose:
        summary["audit"] = audit
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if audit.get("passed") or not args.require_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
