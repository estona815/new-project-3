#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.final_render_evidence_gate import build_final_render_evidence_gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate final render evidence before final QC and approval readiness.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--render-manifest", type=Path, default=None)
    parser.add_argument("--final-export-state", type=Path, default=None)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_final_render_evidence_gate(
        project_name=args.project_name,
        output_dir=args.output_dir,
        render_manifest_path=args.render_manifest,
        final_export_state_path=args.final_export_state,
    )
    summary = {
        "status": "ready_for_final_qc" if gate.get("ready_for_final_qc") else "blocked",
        "ready_for_final_qc": gate.get("ready_for_final_qc"),
        "ready_for_approval_readiness": gate.get("ready_for_approval_readiness"),
        "primary_wav_path": gate.get("primary_wav_path", ""),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/final_render_evidence_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/final_render_evidence_gate.md"),
        "template_json": str(args.output_dir / "review/final_render_evidence_manifest_template.json"),
        "request_md": str(args.output_dir / "review/final_render_evidence_request.md"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_ready or gate.get("ready_for_final_qc") else 2


if __name__ == "__main__":
    raise SystemExit(main())
