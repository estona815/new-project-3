#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.source_acceptance_gate import FINAL_EXPORT_INTENT, build_source_acceptance_gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate source/stem acceptance evidence before final export packaging.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--source-audio", type=Path, default=None)
    parser.add_argument("--source-stage", default="")
    parser.add_argument("--source-role", default="")
    parser.add_argument("--source-classification", default="")
    parser.add_argument("--intended-use", default=FINAL_EXPORT_INTENT)
    parser.add_argument("--human-accepted", action="store_true")
    parser.add_argument("--notes", default="")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_source_acceptance_gate(
        project_name=args.project_name,
        output_dir=args.output_dir,
        manifest_path=args.manifest,
        source_audio=args.source_audio,
        source_stage=args.source_stage,
        source_role=args.source_role,
        source_classification=args.source_classification,
        intended_use=args.intended_use,
        human_accepted=args.human_accepted,
        notes=args.notes,
    )
    summary = {
        "status": "ready" if gate.get("accepted_export_source_ready") and not gate.get("blockers") else "blocked",
        "accepted_export_source_ready": gate.get("accepted_export_source_ready"),
        "accepted_stem_sources_total": gate.get("accepted_stem_sources_total"),
        "candidate_sources_total": gate.get("candidate_sources_total"),
        "blockers": gate.get("blockers", []),
        "warnings": gate.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/source_acceptance_gate.json"),
        "report_md": str(args.output_dir / "eval_reports/source_acceptance_gate.md"),
        "template_json": str(args.output_dir / "review/source_acceptance_manifest_template.json"),
        "request_md": str(args.output_dir / "review/source_acceptance_request.md"),
    }
    if args.verbose:
        summary["gate"] = gate
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not args.require_ready or (gate.get("accepted_export_source_ready") and not gate.get("blockers")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
