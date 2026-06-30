#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "tests" / "automix_validation" / "fixtures" / "analysis_json"


FIXTURES = [
    ("mock_full_mix_likelihood_090.json", "full mix likelihood 0.90", {"full_mix_likelihood": 0.90}, "requires_stem", "full_mix_unsafe", ["full_mix_detected_for_pitch_correction"], ["full_mix"]),
    ("mock_already_tuned_090.json", "already tuned 0.90", {"already_tuned_score": 0.90}, "skipped", "reject_pitch_correction", ["ALREADY_TUNED_HIGH"], ["already_tuned_ai_vocal"]),
    ("mock_low_pitch_confidence_040.json", "low pitch confidence 0.40", {"pitch_confidence": 0.40}, "skipped", "skip", ["PITCH_CONFIDENCE_LOW"], ["low_confidence_analysis"]),
    ("mock_low_adapter_confidence.json", "low adapter confidence", {"adapter_confidence": 0.40}, "requires_plugin_mapping", "plugin_mapping_required", ["PLUGIN_MAPPING_UNCERTAIN"], ["missing_plugin", "plugin_mapping_uncertain"]),
    ("mock_missing_required_control.json", "missing required semantic control", {"missing_controls": ["dry_wet"]}, "requires_plugin_mapping", "plugin_mapping_required", ["SEMANTIC_CONTROL_MISSING"], ["missing_plugin", "semantic_control_missing"]),
    ("mock_rejected_recovery.json", "rejected recovery", {"recovery_status": "rejected"}, "blocked", "manual_review_required", ["rejected_recovery_but_pitch_requested"], ["human_review", "rejected_revision"]),
    ("mock_rejected_placement.json", "rejected placement", {"placement_status": "rejected"}, "blocked", "manual_review_required", ["rejected_placement_but_premaster_requested"], ["human_review", "rejected_revision"]),
    ("mock_rejected_premaster.json", "rejected premaster", {"premaster_status": "rejected"}, "blocked", "manual_review_required", ["premaster_rejected_but_final_export_requested"], ["human_review", "rejected_revision"]),
    ("mock_final_approval_missing.json", "final approval missing", {"approved": False}, "requires_approval", "final_export_blocked", ["final_approval_missing"], ["human_review", "final_approval"]),
    ("mock_qc_failed.json", "QC failed", {"qc_passed": False}, "blocked", "final_delivery_failed", ["qc_failure_for_final_delivery"], ["qc_failure"]),
    ("mock_safe_draft_pass.json", "safe draft pass", {"all_gates_passed": True, "dry_run": True}, "passed", "drafts_created_review_required", [], ["dry_run", "safe_draft"]),
    ("mock_corrupted_config.json", "corrupted config", {"config_parse_error": True, "config_path": "automix/config/bad.json"}, "blocked", "configuration_repair_required", ["CONFIG_CORRUPTED"], ["corrupted_config"]),
    ("mock_dry_run_required.json", "dry-run required", {"dry_run": True, "would_modify_project": False}, "dry_run_only", "draft_plan_only", [], ["dry_run"]),
    ("mock_rollback_registry_required.json", "rollback registry required", {"rollback_registry_missing": True, "safe_to_apply": False}, "requires_rollback", "rollback_required", ["ROLLBACK_METADATA_MISSING"], ["rollback"]),
    ("mock_render_failure.json", "render failure", {"render_status": "failed", "render_error": "offline render aborted"}, "blocked", "render_failed_manual_review", ["RENDER_FAILED"], ["render_failure"]),
    ("mock_feedback_mapping.json", "feedback mapping", {"feedback": "보컬이 뿌옇고 Suno fizz가 남아 있다.", "dry_run": True}, "mapped_to_draft_actions", "feedback_revision_dry_run", [], ["feedback_mapping", "suno_high_fizz", "dry_run"]),
]


def generate() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for filename, name, inputs, status, decision, blockers, coverage_tags in FIXTURES:
        data = {
            "schema": "prompt41-mock-analysis-fixture-v1",
            "name": name,
            "coverage_tags": coverage_tags,
            "input": inputs,
            "expected_stage_status": status,
            "expected_decision": decision,
            "expected_blockers": blockers,
            "expected_reports": [],
        }
        path = OUT / filename
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(str(path))
    return {"schema": "prompt41-mock-analysis-manifest-v1", "fixtures": written}


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
