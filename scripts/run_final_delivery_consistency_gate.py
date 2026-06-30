#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.final_delivery_consistency_gate import build_final_delivery_consistency_gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate cross-report consistency for final delivery evidence.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_final_delivery_consistency_gate(project_name=args.project_name, output_dir=args.output_dir)
    summary = {
        "status": "ready_for_delivery_consistency" if gate.get("ready_for_delivery_consistency") else "blocked",
        "ready_for_delivery_consistency": gate.get("ready_for_delivery_consistency"),
        "ready_for_professional_readiness": gate.get("ready_for_professional_readiness"),
        "final_audio_path": gate.get("final_audio_consistency", {}).get("final_audio_path", ""),
        "ab_preview_path": gate.get("ab_preview_consistency", {}).get("preview_output_path", ""),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/final_delivery_consistency_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/final_delivery_consistency_gate.md"),
        "template_json": str(args.output_dir / "review/final_delivery_consistency_manifest_template.json"),
        "request_md": str(args.output_dir / "review/final_delivery_consistency_request.md"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_ready or gate.get("ready_for_delivery_consistency") else 2


if __name__ == "__main__":
    raise SystemExit(main())
