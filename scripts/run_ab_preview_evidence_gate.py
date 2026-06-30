#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.ab_preview_evidence_gate import build_ab_preview_evidence_gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate loudness-matched A/B preview evidence before final approval.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--allow-legacy-loudness-flag", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_ab_preview_evidence_gate(
        project_name=args.project_name,
        output_dir=args.output_dir,
        manifest_path=args.manifest,
        allow_legacy_loudness_flag=args.allow_legacy_loudness_flag,
    )
    summary = {
        "status": "ready_for_human_ab_review" if gate.get("ready_for_human_ab_review") else "blocked",
        "ready_for_human_ab_review": gate.get("ready_for_human_ab_review"),
        "ready_for_final_approval_request": gate.get("ready_for_final_approval_request"),
        "human_ab_review_recorded": gate.get("human_ab_review_recorded"),
        "loudness_match_status": gate.get("loudness_match_status", {}),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/ab_preview_evidence_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/ab_preview_evidence_gate.md"),
        "template_json": str(args.output_dir / "review/ab_preview_review_manifest_template.json"),
        "request_md": str(args.output_dir / "review/ab_preview_review_request.md"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_ready or gate.get("ready_for_human_ab_review") else 2


if __name__ == "__main__":
    raise SystemExit(main())
