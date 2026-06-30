#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.reference.genre_target_profiles import DEFAULT_TARGET_PROFILE, get_target_profile
from automix.reference.reference_adjustment_applier import assert_reference_match_draft_safe, create_reference_match_draft_metadata
from automix.reference.reference_adjustment_iteration_engine import build_reference_iteration_history
from automix.reference.reference_adjustment_planner import build_reference_adjustment_plan
from automix.reference.reference_analyzer import analyze_manifest_references
from automix.reference.reference_comparison_engine import compare_current_to_reference_and_target
from automix.reference.reference_evaluation import build_reference_match_matrix, evaluate_reference_match_ab, missing_reference_match_eval
from automix.reference.reference_intake import build_reference_manifest
from automix.reference.reference_report import write_reference_match_report


MODES = {
    "reference_scan_only",
    "target_profile_scan_only",
    "conservative_reference_match_draft",
    "report_only",
    "no_reference_match",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prompt 38 reference matching / genre targeting workflow.")
    parser.add_argument("--project", type=Path, default=None)
    parser.add_argument("--current-mix", type=Path, default=None)
    parser.add_argument("--reference", action="append", type=Path, default=[])
    parser.add_argument("--reference-role", action="append", default=[])
    parser.add_argument("--target-profile", default=DEFAULT_TARGET_PROFILE)
    parser.add_argument("--user-notes", default="")
    parser.add_argument("--mode", default="reference_scan_only", choices=sorted(MODES))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply-draft", action="store_true")
    parser.add_argument("--render-ab", action="store_true")
    parser.add_argument("--reference-match-draft", type=Path, default=None)
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    return parser.parse_args()


def project_name(args: argparse.Namespace) -> str:
    if args.project:
        return args.project.stem
    if args.current_mix:
        return args.current_mix.stem
    return "project"


def reference_pairs(args: argparse.Namespace) -> list[tuple[Path, str]]:
    pairs = []
    for index, path in enumerate(args.reference):
        role = args.reference_role[index] if index < len(args.reference_role) else "primary_reference"
        pairs.append((path, role))
    return pairs


def main() -> int:
    args = parse_args()
    if args.apply_draft and args.mode != "conservative_reference_match_draft":
        print("--apply-draft requires --mode conservative_reference_match_draft")
        return 2
    if args.apply_draft and not args.dry_run:
        print("Python reference matching workflow is fail-closed and writes draft metadata only. Use --dry-run to generate plans, then use a reviewed REAPER applicator explicitly.")
        return 2

    output_dir = args.output_dir
    get_target_profile(args.target_profile)
    refs = [] if args.mode == "target_profile_scan_only" else reference_pairs(args)
    manifest = build_reference_manifest(
        project_name=project_name(args),
        references=refs,
        target_profile=args.target_profile,
        user_notes=args.user_notes,
        output_dir=output_dir,
    )
    reference_analyses, current_analysis = analyze_manifest_references(manifest, output_dir, current_mix_path=args.current_mix)
    comparison = compare_current_to_reference_and_target(
        project_name=project_name(args),
        current_analysis=current_analysis,
        reference_analyses=reference_analyses,
        target_profile_name=args.target_profile,
        output_dir=output_dir,
    )
    plan = build_reference_adjustment_plan(project_name=project_name(args), comparison=comparison, output_dir=output_dir)
    rollback = create_reference_match_draft_metadata(plan, output_dir, apply_draft=args.apply_draft)
    assert_reference_match_draft_safe(plan, rollback)

    if args.render_ab and args.current_mix and args.reference_match_draft:
        eval_metrics = evaluate_reference_match_ab(
            current_mix_path=args.current_mix,
            reference_match_draft_path=args.reference_match_draft,
            reference_analyses=reference_analyses,
            target_profile=args.target_profile,
            project_name=project_name(args),
            output_dir=output_dir,
        )
    else:
        eval_metrics = missing_reference_match_eval(
            {
                "current_mix": str(args.current_mix) if args.current_mix and args.current_mix.exists() else None,
                "reference_match_draft": str(args.reference_match_draft) if args.reference_match_draft and args.reference_match_draft.exists() else None,
            }
        )
        from automix.analyze_ai_pitch_source import write_json

        write_json(output_dir / "eval_reports" / "reference_match_eval_metrics.json", eval_metrics)
    if plan.get("adjustments"):
        iteration_history = build_reference_iteration_history(plan, [eval_metrics] if eval_metrics else [])
    else:
        iteration_history = {
            "schema": "automix-reference-match-iteration-history-v1",
            "max_iterations": 3,
            "iterations": [],
            "final_decision": "target_profile_only_used" if not reference_analyses else "no_reference_match_needed",
            "never_intensify_after_damage": True,
        }
    matrix = build_reference_match_matrix(project_name(args), comparison, plan, eval_metrics, output_dir)
    report = write_reference_match_report(
        output_dir=output_dir,
        manifest=manifest,
        current_analysis=current_analysis,
        reference_analyses=reference_analyses,
        comparison=comparison,
        plan=plan,
        eval_metrics=eval_metrics,
        iteration_history=iteration_history,
    )
    from automix.analyze_ai_pitch_source import write_json

    write_json(output_dir / "eval_reports" / "reference_match_iteration_history.json", iteration_history)
    result = {
        "project_name": project_name(args),
        "mode": args.mode,
        "target_profile": args.target_profile,
        "references_count": len(reference_analyses),
        "safe_match_score": comparison["comparison_summary"]["safe_match_score"],
        "adjustments_count": len(plan.get("adjustments", [])),
        "blocked_adjustments_count": len(plan.get("blocked_adjustments", [])),
        "draft_created": False,
        "evaluation_status": matrix["evaluation_status"],
        "final_recommendation": matrix["final_recommendation"],
        "original_mix_untouched": True,
        "premaster_rerun_required": bool(plan.get("adjustments")),
        "report": str(report),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
