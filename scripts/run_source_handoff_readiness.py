#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.source_handoff_readiness import build_source_handoff_readiness


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a source/stem handoff readiness report without processing audio.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--source-safety-map", type=Path, default=None)
    parser.add_argument("--final-export-state", type=Path, default=None)
    parser.add_argument("--project-state", type=Path, default=None)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    readiness = build_source_handoff_readiness(
        project_name=args.project_name,
        output_dir=args.output_dir,
        source_safety_path=args.source_safety_map,
        final_export_state_path=args.final_export_state,
        project_state_path=args.project_state,
    )
    summary = {
        "status": "ready" if not readiness.get("blockers") else "blocked",
        "summary": readiness.get("summary", {}),
        "blockers": readiness.get("blockers", []),
        "warnings": readiness.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/source_handoff_readiness.json"),
        "report_md": str(args.output_dir / "eval_reports/source_handoff_readiness.md"),
        "handoff_request": str(args.output_dir / "review/source_stem_handoff_request.md"),
    }
    if args.verbose:
        summary["readiness"] = readiness
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.require_ready and readiness.get("blockers"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
