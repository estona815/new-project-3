#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.batch.batch_pitch_triage import BATCH_MODES, run_batch_triage


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prompt 33 batch pitch triage.")
    parser.add_argument("--project", type=Path, default=None, help="REAPER .rpp project path. Parsed read-only.")
    parser.add_argument("--track-manifest", type=Path, default=None, help="Optional JSON track manifest for tests/offline dry-runs.")
    parser.add_argument("--mode", default="conservative_scan_only", choices=sorted(BATCH_MODES))
    parser.add_argument("--track-filter", default=None)
    parser.add_argument("--apply-drafts", action="store_true", help="Only creates apply/rollback plan in Python; REAPER draft creation remains explicit.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--render-ab", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--allow-experimental-full-mix", action="store_true")
    parser.add_argument("--adapter-status-json", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.mode == "conservative_apply_drafts" and not args.apply_drafts:
        print("conservative_apply_drafts requires explicit --apply-drafts.")
        return 2
    if args.allow_experimental_full_mix and args.mode != "experimental_full_mix_drafts":
        print("--allow-experimental-full-mix requires --mode experimental_full_mix_drafts.")
        return 2
    if args.apply_drafts and not args.dry_run:
        print("Python batch triage is fail-closed and does not modify REAPER directly. Use --dry-run to create plans, then run the REAPER draft applicator explicitly.")
        return 2

    paths = run_batch_triage(
        project_path=args.project,
        output_dir=args.output_dir,
        mode=args.mode,
        track_filter=args.track_filter,
        apply_drafts=args.apply_drafts,
        render_ab=args.render_ab,
        report_only=args.report_only,
        allow_experimental_full_mix=args.allow_experimental_full_mix,
        adapter_status_path=args.adapter_status_json,
        track_manifest_path=args.track_manifest,
    )
    print(json.dumps({key: str(value) for key, value in paths.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
