#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.mastering.premaster_policy import (
    build_premaster_chain_plan,
    evaluate_premaster_policy,
    write_premaster_artifacts,
)
from automix.mastering.premaster_safety_analyzer import (
    analyze_premaster_file,
    analyze_premaster_safety,
    build_translation_check,
    evaluate_premaster_ab,
    missing_premaster_eval_metrics,
)


PREMASTER_MODES = {
    "premaster_scan_only",
    "safety_only_premaster",
    "safe_streaming_premaster",
    "loud_but_safe_premaster",
    "already_mastered_safety",
    "skip_premaster",
    "report_only",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prompt 36 premaster safety workflow.")
    parser.add_argument("--project", type=Path, default=None, help="REAPER .rpp project path. Used for naming only; not modified.")
    parser.add_argument("--source-mix", type=Path, default=None, help="Rendered mix WAV to analyze before premaster.")
    parser.add_argument("--premaster-draft", type=Path, default=None, help="Optional rendered premaster draft WAV for A/B evaluation.")
    parser.add_argument("--mode", default="premaster_scan_only", choices=sorted(PREMASTER_MODES))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply-draft", action="store_true")
    parser.add_argument("--render-ab", action="store_true")
    parser.add_argument("--translation-check", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--target-lufs", type=float, default=None)
    parser.add_argument("--adapter-status-json", type=Path, default=None)
    parser.add_argument("--workflow-status-json", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    return parser.parse_args()


def load_json(path: Path | None) -> dict:
    if not path:
        return {}
    if not path.exists():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def project_name(args: argparse.Namespace) -> str:
    if args.project:
        return args.project.stem
    if args.source_mix:
        return args.source_mix.stem
    return "project"


def main() -> int:
    args = parse_args()
    if args.apply_draft and not args.dry_run:
        print(
            "Python premaster workflow is fail-closed and does not modify REAPER directly. "
            "Use --dry-run to create plans, then run the disabled REAPER draft applicator explicitly."
        )
        return 2
    if args.mode == "report_only":
        args.report_only = True

    output_dir = args.output_dir
    if args.source_mix and args.source_mix.exists():
        analysis = analyze_premaster_file(args.source_mix, output_dir, project_name(args))
    else:
        analysis = analyze_premaster_safety(
            None,
            project_name=project_name(args),
            source_mix_path=str(args.source_mix or ""),
            input_stage="missing_source_mix",
        )
        analysis["warnings"] = sorted(set(analysis.get("warnings", []) + ["source mix render missing; analysis is report-only"]))

    adapter_status = load_json(args.adapter_status_json)
    workflow_status = load_json(args.workflow_status_json)
    requested_mode = analysis.get("recommended_premaster_mode")
    if args.mode not in {"premaster_scan_only", "report_only"}:
        requested_mode = args.mode
    if args.report_only:
        requested_mode = "skip_premaster"

    decision = evaluate_premaster_policy(analysis, workflow_status=workflow_status, requested_mode=requested_mode, target_lufs=args.target_lufs)
    chain_plan = build_premaster_chain_plan(
        analysis,
        decision=decision,
        adapter_status=adapter_status,
        output_dir=output_dir,
        target_lufs=args.target_lufs,
    )

    if args.render_ab and args.source_mix and args.premaster_draft:
        eval_metrics = evaluate_premaster_ab(args.source_mix, args.premaster_draft, output_dir)
    else:
        eval_metrics = missing_premaster_eval_metrics(
            {
                "original_mix": str(args.source_mix) if args.source_mix and args.source_mix.exists() else None,
                "premaster_draft": str(args.premaster_draft) if args.premaster_draft and args.premaster_draft.exists() else None,
            }
        )
    translation_check = build_translation_check(analysis, eval_metrics)
    paths = write_premaster_artifacts(output_dir, analysis, decision, chain_plan, eval_metrics, translation_check)

    print(
        json.dumps(
            {
                "mode": args.mode,
                "dry_run": args.dry_run,
                "premaster_action": decision["premaster_action"],
                "safe_to_apply": chain_plan["safe_to_apply"],
                "original_master_must_remain_untouched": True,
                "paths": {key: str(value) for key, value in paths.items()},
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
