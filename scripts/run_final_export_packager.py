#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.export.ab_preview_montage import generate_ab_preview_montage
from automix.export.deliverable_packager import create_deliverables_folder, package_deliverables, write_plugin_mapping_summary
from automix.export.export_format_profiles import resolve_export_profile
from automix.export.final_export_state_resolver import resolve_final_export_state
from automix.export.final_qc_analyzer import analyze_final_qc, missing_final_qc, write_final_qc_report
from automix.export.final_render_engine import render_final_outputs
from automix.export.human_approval_gate import build_human_approval, evaluate_human_approval
from automix.analyze_ai_pitch_source import write_json
from automix.orchestrator.ab_preview_evidence_gate import build_ab_preview_evidence_gate
from automix.orchestrator.deliverable_package_evidence_gate import build_deliverable_package_evidence_gate
from automix.orchestrator.final_approval_evidence_gate import build_final_approval_evidence_gate
from automix.orchestrator.final_delivery_consistency_gate import build_final_delivery_consistency_gate
from automix.orchestrator.final_render_evidence_gate import build_final_render_evidence_gate
from automix.orchestrator.final_qc_evidence_gate import build_final_qc_evidence_gate
from automix.orchestrator.rollback_evidence_gate import build_rollback_evidence_gate


STAGE_TO_STATE = {
    "accepted_premaster_draft": "premaster",
    "accepted_vocal_placement_draft": "vocal_placement",
    "accepted_pitch_recovery_integrated_draft": "pitch_recovery_integrated",
    "accepted_recovery_draft": "vocal_recovery",
    "original_mix_explicitly_approved": "original_mix",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prompt 37 final export, QC, and deliverable packaging workflow.")
    parser.add_argument("--project", type=Path, default=None)
    parser.add_argument("--source-stage", default="")
    parser.add_argument("--source-audio", type=Path, default=None)
    parser.add_argument("--original-mix", type=Path, default=None)
    parser.add_argument("--profile", default="review_package")
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--approval-notes", default="")
    parser.add_argument("--acknowledge-warnings", action="store_true")
    parser.add_argument("--unsafe-override", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--make-ab-preview", action="store_true")
    parser.add_argument("--qc", action="store_true")
    parser.add_argument("--zip", action="store_true")
    parser.add_argument("--diagnostic-only", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("automix"))
    parser.add_argument("--deliverables-root", type=Path, default=Path("deliverables"))
    return parser.parse_args()


def project_name(args: argparse.Namespace) -> str:
    if args.project:
        return args.project.stem
    if args.source_audio:
        return args.source_audio.stem
    return "project"


def build_workflow_state(args: argparse.Namespace) -> dict:
    if not args.source_audio or not args.source_stage:
        return {}
    stage_key = STAGE_TO_STATE.get(args.source_stage, args.source_stage)
    stage_data = {
        "accepted": args.source_stage.startswith("accepted_") or args.source_stage == "original_mix_explicitly_approved",
        "status": "accepted" if args.source_stage.startswith("accepted_") or args.source_stage == "original_mix_explicitly_approved" else args.source_stage,
        "source_path": str(args.source_audio),
        "source_track_or_bus_guid": "",
        "review_required": False,
        "review_accepted": args.approve,
        "ab_required": False,
        "ab_render_exists": True,
    }
    if stage_key == "original_mix":
        stage_data["explicitly_approved"] = args.approve
    return {stage_key: stage_data}


def primary_wav_from_manifest(render_manifest: dict) -> Path | None:
    for item in render_manifest.get("renders", []):
        if item.get("format") == "wav" and item.get("bit_depth") == 24 and item.get("created"):
            return Path(item["path"])
    for item in render_manifest.get("renders", []):
        if item.get("format") == "wav" and item.get("created"):
            return Path(item["path"])
    return None


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    profile = resolve_export_profile("diagnostic_only" if args.diagnostic_only else args.profile)
    name = project_name(args)

    state = resolve_final_export_state(
        project_name=name,
        workflow_state=build_workflow_state(args),
        explicit_original_approval=args.approve and args.source_stage == "original_mix_explicitly_approved",
        output_dir=output_dir,
        output_path=output_dir / "export" / "final_export_state.json",
    )
    approval = build_human_approval(
        approved=args.approve,
        approved_stage=args.source_stage,
        approved_source=str(args.source_audio or ""),
        notes=args.approval_notes,
        warnings_acknowledged=["all"] if args.acknowledge_warnings else [],
        unsafe_override=args.unsafe_override,
        output_path=output_dir / "review" / "final_human_approval.json",
    )
    approval_eval = evaluate_human_approval(state, approval, diagnostic_only=args.diagnostic_only, report_only=profile.get("final_audio") is False, warnings=state.get("warnings", []))
    deliverables_dir = create_deliverables_folder(args.deliverables_root, name, unsafe_override=args.unsafe_override)

    render_manifest = render_final_outputs(
        project_name=name,
        export_profile=profile,
        export_state=state,
        approval_eval=approval_eval,
        deliverables_dir=deliverables_dir,
        output_dir=output_dir,
        render=args.render,
        diagnostic_only=args.diagnostic_only,
    )
    final_render_evidence_gate = build_final_render_evidence_gate(project_name=name, output_dir=output_dir)
    rollback_evidence_gate = build_rollback_evidence_gate(project_name=name, output_dir=output_dir)

    ab_manifest = {}
    primary_wav = primary_wav_from_manifest(render_manifest)
    if args.make_ab_preview and primary_wav and args.original_mix:
        ab_manifest = generate_ab_preview_montage(
            project_name=name,
            original_mix_path=args.original_mix,
            final_audio_path=primary_wav,
            output_dir=output_dir,
            deliverables_dir=deliverables_dir,
            export_state=state if approval_eval.get("approved_for_export") else {**state, "safe_to_export": False},
        )
    else:
        ab_manifest = {
            "schema": "automix-final-ab-preview-v1",
            "source_original": str(args.original_mix or ""),
            "source_final": str(primary_wav or ""),
            "segments": [],
            "loudness_matched": False,
            "output_path": "",
            "created": False,
            "warnings": ["ab_preview_not_requested_or_missing_sources"],
        }
        write_json(output_dir / "eval_reports" / "final_ab_preview_manifest.json", ab_manifest)
    ab_evidence_gate = build_ab_preview_evidence_gate(project_name=name, output_dir=output_dir)

    if args.qc and primary_wav:
        qc_metrics = analyze_final_qc(primary_wav, output_dir=output_dir, export_state=state, expected_sample_rate=48000, expected_bit_depth=24)
    else:
        qc_metrics = missing_final_qc(primary_wav or Path(""), "qc_not_requested_or_primary_wav_missing")
        write_json(output_dir / "eval_reports" / "final_qc_metrics.json", qc_metrics)
    final_qc_evidence_gate = build_final_qc_evidence_gate(project_name=name, output_dir=output_dir)
    final_approval_evidence_gate = build_final_approval_evidence_gate(project_name=name, output_dir=output_dir)

    plugin_summary = write_plugin_mapping_summary(output_dir)
    write_final_qc_report(
        output_dir=output_dir,
        project_name=name,
        export_profile=profile,
        export_state=state,
        approval=approval,
        approval_eval=approval_eval,
        render_manifest=render_manifest,
        qc_metrics=qc_metrics,
        ab_preview_manifest=ab_manifest,
        package_manifest={},
        included_reports={
            "premaster report": str(output_dir / "eval_reports" / "project_premaster_report.md"),
            "translation check": str(output_dir / "eval_reports" / "project_translation_check.json"),
            "chain plans": str(output_dir / "chain_plans"),
            "rollback metadata": str(output_dir / "rollback"),
        },
    )
    package_manifest = package_deliverables(
        project_name=name,
        deliverables_dir=deliverables_dir,
        output_dir=output_dir,
        export_state=state,
        render_manifest=render_manifest,
        qc_metrics=qc_metrics,
        ab_preview_manifest=ab_manifest,
        create_zip=args.zip,
        unsafe_override=args.unsafe_override,
    )
    qc_report = write_final_qc_report(
        output_dir=output_dir,
        project_name=name,
        export_profile=profile,
        export_state=state,
        approval=approval,
        approval_eval=approval_eval,
        render_manifest=render_manifest,
        qc_metrics=qc_metrics,
        ab_preview_manifest=ab_manifest,
        package_manifest=package_manifest,
        included_reports={
            "premaster report": str(output_dir / "eval_reports" / "project_premaster_report.md"),
            "translation check": str(output_dir / "eval_reports" / "project_translation_check.json"),
            "chain plans": str(output_dir / "chain_plans"),
            "rollback metadata": str(output_dir / "rollback"),
        },
    )
    deliverable_package_evidence_gate = build_deliverable_package_evidence_gate(project_name=name, output_dir=output_dir)
    final_delivery_consistency_gate = build_final_delivery_consistency_gate(project_name=name, output_dir=output_dir)

    result = {
        "project_name": name,
        "profile": profile["profile_name"],
        "safe_to_export": state["safe_to_export"],
        "approval": approval_eval,
        "deliverables_dir": str(deliverables_dir),
        "render_manifest": str(output_dir / "export" / "final_render_manifest.json"),
        "final_render_evidence_ready": final_render_evidence_gate.get("ready_for_final_qc", False),
        "rollback_evidence_ready": rollback_evidence_gate.get("ready_for_delivery_readiness", False),
        "ab_preview_created": ab_manifest.get("created", False),
        "ab_preview_evidence_ready": ab_evidence_gate.get("ready_for_human_ab_review", False),
        "qc_passed": qc_metrics.get("qc_passed", False),
        "final_qc_evidence_ready": final_qc_evidence_gate.get("ready_for_delivery_qc", False),
        "final_approval_evidence_ready": final_approval_evidence_gate.get("ready_for_delivery_request", False),
        "deliverable_package_evidence_ready": deliverable_package_evidence_gate.get("ready_for_delivery_package", False),
        "final_delivery_consistency_ready": final_delivery_consistency_gate.get("ready_for_delivery_consistency", False),
        "qc_report": str(qc_report),
        "zip_package": package_manifest.get("zip_path"),
        "package_created": package_manifest.get("package_created"),
        "plugin_mapping_summary": str(plugin_summary),
        "export_blocked": not state["safe_to_export"] and not approval_eval.get("unsafe_override"),
        "warnings_acknowledged": bool(args.acknowledge_warnings),
    }
    print(json.dumps(result, indent=2))
    return 0 if args.diagnostic_only or approval_eval.get("approved_for_export") or not args.render else 2


if __name__ == "__main__":
    raise SystemExit(main())
