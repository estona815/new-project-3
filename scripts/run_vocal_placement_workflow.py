#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.batch.batch_pitch_triage import run_batch_triage


PLACEMENT_MODES = {
    "placement_scan_only",
    "conservative_placement_draft",
    "report_only",
    "no_placement",
    "force_review",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prompt 35 vocal-forward placement workflow.")
    parser.add_argument("--project", type=Path, default=None, help="REAPER .rpp project path. Parsed read-only.")
    parser.add_argument("--track-manifest", type=Path, default=None, help="Optional offline JSON manifest.")
    parser.add_argument("--lead-vocal-track", default=None)
    parser.add_argument("--instrumental-bus", default=None)
    parser.add_argument("--mode", default="placement_scan_only", choices=sorted(PLACEMENT_MODES))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply-draft", action="store_true")
    parser.add_argument("--render-ab", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--target-section", default=None)
    parser.add_argument("--adapter-status-json", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.mode == "conservative_placement_draft" and not args.apply_draft:
        print("conservative_placement_draft requires explicit --apply-draft.")
        return 2
    if args.apply_draft and not args.dry_run:
        print("Python vocal placement workflow is fail-closed and does not modify REAPER directly. Use --dry-run to create plans, then run a REAPER draft applicator explicitly.")
        return 2

    batch_mode = "report_only" if args.mode == "report_only" or args.report_only else "conservative_scan_only"
    if args.mode == "no_placement":
        batch_mode = "no_pitch_correction"
    paths = run_batch_triage(
        project_path=args.project,
        output_dir=args.output_dir,
        mode=batch_mode,
        track_filter=args.lead_vocal_track,
        apply_drafts=False,
        render_ab=args.render_ab,
        report_only=args.report_only,
        adapter_status_path=args.adapter_status_json,
        track_manifest_path=args.track_manifest,
    )
    print(json.dumps({key: str(value) for key, value in paths.items() if key in {"placement_matrix", "batch_report", "role_map"}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
