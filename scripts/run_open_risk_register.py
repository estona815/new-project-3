#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.open_risk_register import build_open_risk_register


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an open risk register from AutoMix reports.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    register = build_open_risk_register(project_name=args.project_name, output_dir=args.output_dir)
    summary = {
        "status": "passed" if register.get("passed") else "open_blockers",
        "passed": register.get("passed"),
        "risk_counts": register.get("risk_counts", {}),
        "blockers": register.get("blockers", []),
        "warnings": register.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/open_risk_register.json"),
        "report_md": str(args.output_dir / "eval_reports/open_risk_register.md"),
    }
    if args.verbose:
        summary["register"] = register
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if register.get("passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
