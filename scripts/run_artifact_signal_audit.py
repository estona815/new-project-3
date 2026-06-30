#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.artifact_signal_audit import build_artifact_signal_audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit whether AI/Suno artifact-focused work has enough evidence to proceed.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--require-established", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_artifact_signal_audit(project_name=args.project_name, output_dir=args.output_dir)
    summary = {
        "status": "established" if audit.get("artifact_signal_established") else "blocked",
        "artifact_signal_established": audit.get("artifact_signal_established", False),
        "safe_to_run_artifact_suppression": audit.get("safe_to_run_artifact_suppression", False),
        "summary": audit.get("summary", {}),
        "blockers": audit.get("blockers", []),
        "warnings": audit.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/artifact_signal_audit.json"),
        "report_md": str(args.output_dir / "eval_reports/artifact_signal_audit.md"),
    }
    if args.verbose:
        summary["audit"] = audit
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.require_established and not audit.get("artifact_signal_established", False):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
