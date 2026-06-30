#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.final_qc_evidence_gate import build_final_qc_evidence_gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate measured final QC evidence against final render evidence.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--qc-metrics", type=Path, default=None)
    parser.add_argument("--final-render-evidence", type=Path, default=None)
    parser.add_argument("--render-manifest", type=Path, default=None)
    parser.add_argument("--true-peak-ceiling-dbTP", type=float, default=-1.0)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_final_qc_evidence_gate(
        project_name=args.project_name,
        output_dir=args.output_dir,
        qc_metrics_path=args.qc_metrics,
        final_render_evidence_path=args.final_render_evidence,
        render_manifest_path=args.render_manifest,
        true_peak_ceiling_dbTP=args.true_peak_ceiling_dbTP,
    )
    summary = {
        "status": "ready_for_delivery_qc" if gate.get("ready_for_delivery_qc") else "blocked",
        "ready_for_delivery_qc": gate.get("ready_for_delivery_qc"),
        "ready_for_approval_readiness": gate.get("ready_for_approval_readiness"),
        "final_audio_path": gate.get("final_audio_path", ""),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/final_qc_evidence_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/final_qc_evidence_gate.md"),
        "template_json": str(args.output_dir / "review/final_qc_evidence_manifest_template.json"),
        "request_md": str(args.output_dir / "review/final_qc_evidence_request.md"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_ready or gate.get("ready_for_delivery_qc") else 2


if __name__ == "__main__":
    raise SystemExit(main())
