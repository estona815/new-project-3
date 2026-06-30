#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.deliverable_package_evidence_gate import build_deliverable_package_evidence_gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate final deliverable package ZIP and manifest evidence.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--package-manifest", type=Path, default=None)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_deliverable_package_evidence_gate(
        project_name=args.project_name,
        output_dir=args.output_dir,
        package_manifest_path=args.package_manifest,
    )
    summary = {
        "status": "ready_for_delivery_package" if gate.get("ready_for_delivery_package") else "blocked",
        "ready_for_delivery_package": gate.get("ready_for_delivery_package"),
        "ready_for_professional_readiness": gate.get("ready_for_professional_readiness"),
        "package_created": gate.get("package_summary", {}).get("package_created"),
        "zip_path": gate.get("package_summary", {}).get("zip_path"),
        "zip_valid": gate.get("zip_status", {}).get("valid_zip"),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/deliverable_package_evidence_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/deliverable_package_evidence_gate.md"),
        "template_json": str(args.output_dir / "review/deliverable_package_evidence_manifest_template.json"),
        "request_md": str(args.output_dir / "review/deliverable_package_evidence_request.md"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_ready or gate.get("ready_for_delivery_package") else 2


if __name__ == "__main__":
    raise SystemExit(main())
