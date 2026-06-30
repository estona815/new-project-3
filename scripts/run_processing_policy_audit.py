#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.safety.processing_policy_audit import build_processing_policy_audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit AutoMix chain plans against conservative processing policy.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_processing_policy_audit(project_name=args.project_name, output_dir=args.output_dir)
    summary = {
        "status": "passed" if audit.get("passed") else "blocked",
        "passed": audit.get("passed"),
        "plans_checked": audit.get("plans_checked", 0),
        "blockers": audit.get("blockers", []),
        "warnings": audit.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/processing_policy_audit.json"),
        "report_md": str(args.output_dir / "eval_reports/processing_policy_audit.md"),
    }
    if args.verbose:
        summary["audit"] = audit
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if audit.get("passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
