#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.final_approval_evidence_gate import build_final_approval_evidence_gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate final human approval evidence against A/B, render, and QC gates.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--approval", type=Path, default=None)
    parser.add_argument("--final-export-state", type=Path, default=None)
    parser.add_argument("--ab-preview-evidence", type=Path, default=None)
    parser.add_argument("--final-render-evidence", type=Path, default=None)
    parser.add_argument("--final-qc-evidence", type=Path, default=None)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_final_approval_evidence_gate(
        project_name=args.project_name,
        output_dir=args.output_dir,
        approval_path=args.approval,
        final_export_state_path=args.final_export_state,
        ab_preview_evidence_path=args.ab_preview_evidence,
        final_render_evidence_path=args.final_render_evidence,
        final_qc_evidence_path=args.final_qc_evidence,
    )
    summary = {
        "status": "ready_for_delivery_request" if gate.get("ready_for_delivery_request") else ("approval_pending" if gate.get("approval_pending_only") else "blocked"),
        "ready_for_delivery_request": gate.get("ready_for_delivery_request"),
        "approval_pending_only": gate.get("approval_pending_only"),
        "approved": gate.get("approved"),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/final_approval_evidence_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/final_approval_evidence_gate.md"),
        "template_json": str(args.output_dir / "review/final_approval_evidence_manifest_template.json"),
        "request_md": str(args.output_dir / "review/final_approval_evidence_request.md"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_ready or gate.get("ready_for_delivery_request") else 2


if __name__ == "__main__":
    raise SystemExit(main())
