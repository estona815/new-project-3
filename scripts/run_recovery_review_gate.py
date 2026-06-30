#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.review.recovery_review_gate import run_recovery_review_gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prompt44 recovery draft human review gate.")
    parser.add_argument("--project", type=Path, default=None)
    parser.add_argument("--generate-form", action="store_true")
    parser.add_argument("--input-decisions", type=Path, default=None)
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--accept-draft", default=None)
    parser.add_argument("--reject-draft", default=None)
    parser.add_argument("--decision", default=None)
    parser.add_argument("--notes", default="")
    parser.add_argument("--acknowledge-warnings", action="store_true")
    parser.add_argument("--allow-provisional-without-ab", action="store_true")
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--mute-rejected", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    draft = args.accept_draft or args.reject_draft
    decision = args.decision
    if args.reject_draft and not decision:
        decision = "rejected"
    summary = run_recovery_review_gate(
        project_path=args.project,
        output_dir=args.output_dir,
        generate_form=args.generate_form,
        input_decisions=args.input_decisions,
        accept_draft=draft,
        decision=decision,
        notes=args.notes,
        acknowledge_warnings=args.acknowledge_warnings,
        allow_provisional_without_ab=args.allow_provisional_without_ab,
        update=args.update,
        mute_rejected=args.mute_rejected,
        interactive=args.interactive,
        verbose=args.verbose,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if summary.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())

