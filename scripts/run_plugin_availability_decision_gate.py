#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_availability_decision_gate import build_plugin_availability_decision_gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate operator decisions for unavailable plugin disable/install handling.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--resolution-plan", type=Path, default=None)
    parser.add_argument("--decision-manifest", type=Path, default=None)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_plugin_availability_decision_gate(
        project_name=args.project_name,
        output_dir=args.output_dir,
        resolution_plan_path=args.resolution_plan,
        decision_manifest_path=args.decision_manifest,
    )
    summary = {
        "status": gate.get("status"),
        "availability_decisions_ready": gate.get("availability_decisions_ready"),
        "required_decisions_total": gate.get("required_decisions_total"),
        "missing_decisions": gate.get("missing_decisions", []),
        "safe_to_write_parameters": gate.get("safe_to_write_parameters", False),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/plugin_availability_decision_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/plugin_availability_decision_gate.md"),
        "request_md": str(args.output_dir / "review/plugin_availability_decision_request.md"),
        "decision_manifest": gate.get("decision_manifest", ""),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_ready or gate.get("availability_decisions_ready", False) else 2


if __name__ == "__main__":
    raise SystemExit(main())
