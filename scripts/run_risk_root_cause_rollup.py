#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.risk_root_cause_rollup import build_risk_root_cause_rollup


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Group open risk register entries into root causes.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--require-clear", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rollup = build_risk_root_cause_rollup(project_name=args.project_name, output_dir=args.output_dir)
    summary = {
        "status": "clear" if rollup.get("passed") else "root_causes_open",
        "passed": rollup.get("passed"),
        "open_risk_total": rollup.get("open_risk_total"),
        "root_cause_total": rollup.get("root_cause_total"),
        "next_root_cause": rollup.get("next_root_cause", {}).get("cause_id", ""),
        "blockers": rollup.get("blockers", []),
        "warnings": rollup.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/risk_root_cause_rollup.json"),
        "report_md": str(args.output_dir / "eval_reports/risk_root_cause_rollup.md"),
    }
    if args.verbose:
        summary["rollup"] = rollup
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_clear or rollup.get("passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
