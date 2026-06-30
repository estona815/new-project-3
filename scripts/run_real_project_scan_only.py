#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.real_project.real_project_scan_only import run_real_project_scan_only


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prompt42 real project scan-only non-destructive audit.")
    parser.add_argument("--project", type=Path, default=None, help="REAPER .rpp path or mock project JSON path.")
    parser.add_argument("--target-profile", default="digicore_hyperpop_hiphop_vocal_forward")
    parser.add_argument("--reference", action="append", default=[])
    parser.add_argument("--reference-role", action="append", default=[])
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--check-prompt41", action="store_true", default=True)
    parser.add_argument("--no-check-prompt41", action="store_false", dest="check_prompt41")
    parser.add_argument("--strict-read-only", action="store_true", default=True)
    parser.add_argument("--no-strict-read-only", action="store_false", dest="strict_read_only")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_real_project_scan_only(
        project_path=args.project,
        target_profile=args.target_profile,
        references=[str(path) for path in args.reference],
        reference_roles=list(args.reference_role),
        output_dir=args.output_dir,
        check_prompt41=args.check_prompt41,
        strict_read_only=args.strict_read_only,
        dry_run=True,
        verbose=args.verbose,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if summary.get("status") == "read_only_guard_failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())

