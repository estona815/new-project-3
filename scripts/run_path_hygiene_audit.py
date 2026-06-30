#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.path_hygiene_audit import build_path_hygiene_audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit source and generated reports for hardcoded local paths.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_path_hygiene_audit(project_name=args.project_name, output_dir=args.output_dir, workspace_root=args.workspace_root)
    summary = {
        "status": "passed" if audit.get("passed") else "blocked",
        "passed": audit.get("passed"),
        "finding_counts": audit.get("finding_counts", {}),
        "blockers": audit.get("blockers", []),
        "warnings": audit.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/path_hygiene_audit.json"),
        "report_md": str(args.output_dir / "eval_reports/path_hygiene_audit.md"),
    }
    if args.verbose:
        summary["audit"] = audit
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if audit.get("passed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
