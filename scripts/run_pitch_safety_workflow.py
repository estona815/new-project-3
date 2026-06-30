#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.analyze_ai_pitch_source import run_analysis


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run Prompt 32 pitch safety workflow.")
    parser.add_argument("--project", type=Path, default=None, help="Optional REAPER project path for report context only.")
    parser.add_argument("--track", required=True, help="Track name used for report output.")
    parser.add_argument("--input", type=Path, required=True, help="User-owned WAV file to classify/analyze.")
    parser.add_argument("--mode", default="default_conservative", choices=[
        "default_conservative",
        "no_pitch_correction",
        "allow_light_pitch_draft",
        "allow_full_mix_pitch_experiment",
        "creative_robotic_autotune",
    ])
    parser.add_argument("--adapter-status-json", type=Path, default=None)
    parser.add_argument("--processed", type=Path, default=None, help="Optional processed pitch draft WAV for evaluation.")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--dry-run", action="store_true", help="Required for now. Does not modify a REAPER project.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.dry_run:
        print("This workflow is fail-closed: use --dry-run. REAPER modification is handled only by the draft Lua applicator.")
        return 2

    paths = run_analysis(
        input_path=args.input,
        output_dir=args.output_dir,
        track_name=args.track,
        adapter_status_path=args.adapter_status_json,
        processed_path=args.processed,
        override_mode=args.mode,
        force_full_mix_experiment=args.mode == "allow_full_mix_pitch_experiment",
        user_goal_allows_pitch=args.mode != "no_pitch_correction",
    )
    plan = json.loads(paths["chain_plan"].read_text(encoding="utf-8"))
    print(json.dumps({
        "dry_run": True,
        "project": str(args.project) if args.project else None,
        "track": args.track,
        "mode": args.mode,
        "pitch_would_apply_to_draft": plan["apply"],
        "safety_gate_decision": plan["safety_gate"]["decision"],
        "reason_codes": plan["safety_gate"]["reason_codes"],
        "chain_plan": str(paths["chain_plan"]),
        "human_report": str(paths["human_report"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
