#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.intent.intent_classifier import build_intent_classification


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify safe AutoMix work intent from scan, plugin, QC, and feedback evidence.")
    parser.add_argument("--project-name", default="project")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--target-profile", default="digicore_hyperpop_hiphop_vocal_forward")
    parser.add_argument("--requested-intent", action="append", default=[])
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_intent_classification(
        project_name=args.project_name,
        output_dir=args.output_dir,
        target_profile=args.target_profile,
        requested_intents=args.requested_intent,
    )
    summary = {
        "status": report.get("status"),
        "recommended_primary_intent": report.get("recommended_primary_intent"),
        "safe_next_mode": report.get("safe_next_mode"),
        "safe_draft_intents": report.get("safe_draft_intents", []),
        "blockers": report.get("blockers", []),
        "warnings": report.get("warnings", []),
        "report_json": str(args.output_dir / "eval_reports/intent_classification.json"),
        "report_md": str(args.output_dir / "eval_reports/intent_classification.md"),
    }
    if args.verbose:
        summary["classification"] = report
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
