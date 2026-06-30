#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.real_project.recovery_only_pilot import run_recovery_only_pilot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prompt43 recovery-only safe draft pilot.")
    parser.add_argument("--project", type=Path, default=None)
    parser.add_argument("--from-scan-report", type=Path, default=Path("automix/eval_reports/real_project_scan_only_report.md"))
    parser.add_argument("--apply-drafts", action="store_true")
    parser.add_argument("--render-ab", action="store_true")
    parser.add_argument("--track-filter", default=None)
    parser.add_argument("--allow-source-separated-rescue", action="store_true")
    parser.add_argument("--mute-drafts", action="store_true", default=True)
    parser.add_argument("--unmute-drafts", action="store_false", dest="mute_drafts")
    parser.add_argument("--strict-original-protection", action="store_true", default=True)
    parser.add_argument("--no-strict-original-protection", action="store_false", dest="strict_original_protection")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dry_run = bool(args.dry_run or not args.apply_drafts)
    if args.render_ab and not args.apply_drafts:
        print(json.dumps({"status": "blocked", "reason": "--render-ab requires --apply-drafts"}, indent=2), file=sys.stderr)
        return 2
    summary = run_recovery_only_pilot(
        project_path=args.project,
        from_scan_report=args.from_scan_report,
        apply_drafts=args.apply_drafts,
        render_ab=args.render_ab,
        track_filter=args.track_filter,
        allow_source_separated_rescue=args.allow_source_separated_rescue,
        mute_drafts=args.mute_drafts,
        strict_original_protection=args.strict_original_protection,
        output_dir=args.output_dir,
        dry_run=dry_run,
        verbose=args.verbose,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if summary.get("status") == "blocked" and args.apply_drafts else 0


if __name__ == "__main__":
    raise SystemExit(main())

