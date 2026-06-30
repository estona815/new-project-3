from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.context.compact_mix_context import build_compact_mix_context, write_compact_mix_context


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def seed_compact_sources(root: Path) -> None:
    output = root / "automix"
    write_json(
        output / "eval_reports/current_state_summary.json",
        {
            "mode": "final_delivery",
            "global_status": "final_delivery_failed",
            "development_status": "blocked_review_required",
            "overall_qc_status": "review_required",
            "safe_to_export": False,
            "stage_status": {"final_export": "blocked"},
            "blockers": ["qc_failure_for_final_delivery"],
            "warnings": ["not_safe_to_write_parameters"],
            "qc": {"critical_blockers": ["qc_failure_for_final_delivery"]},
        },
    )
    write_json(
        output / "eval_reports/mix_master_quality_harness.json",
        {
            "readiness": {
                "ready_for_high_quality_offline_planning": True,
                "ready_for_reaper_dry_run": True,
                "ready_for_applied_mix_or_master_parameter_writes": False,
                "ready_for_delivery_claims": False,
                "render_was_created": False,
            },
            "current_gate_status": {
                "source_ready": False,
                "parameter_write_ready": False,
                "render_qc_ready": False,
                "gates": {
                    "source_acceptance": {
                        "path": "automix/eval_reports/source_acceptance_gate.json",
                        "found": True,
                        "ready": False,
                        "passed": None,
                        "blockers": ["source_acceptance_candidates_missing"],
                    }
                },
            },
            "blockers": ["accepted_source_or_stem_evidence_missing"],
            "warnings": ["render_execution_intentionally_skipped"],
        },
    )
    write_json(
        root / "work/assets/asset_manifest.json",
        {
            "stems_root": "input/stems",
            "reference_root": "input/reference",
            "stem_count": 2,
            "reference_count": 1,
            "unknown_stem_count": 0,
            "source_manifest_hash": "abc123",
        },
    )
    write_json(
        root / "work/traces/plugin_trace.json",
        {
            "slug": "unit_v01",
            "source_full_mix_policy": "muted and master-send disabled",
            "required_main_track": "08 MALE_NONHOOK_CENTER",
            "rows": [
                {
                    "track": "08 MALE_NONHOOK_CENTER",
                    "status": "loaded",
                    "plugin": "JS: Codex Vocal AI Artifact Split Tamer",
                    "fx_index": 0,
                },
                {"track": "MUSIC_BUS", "status": "missing", "plugin": "Optional", "fx_index": 0},
            ],
        },
    )
    write_json(
        root / "work/traces/validation_gates.json",
        {
            "status": "FAIL",
            "gate_checks": {
                "raw_full_mix_not_active": True,
                "full_mix_reference_muted": True,
                "full_mix_reference_master_send_disabled": True,
                "male_main_track_exists": True,
                "male_main_first_fx_is_artifact_split_tamer": True,
                "render_files_exist": False,
                "qc_files_exist": False,
            },
        },
    )
    write_json(
        root / "work/qc/qc_report.json",
        {
            "audio_path": "/tmp/unit.wav",
            "status": "BLOCKED",
            "metrics": {
                "integrated_lufs": {"value": None},
                "true_peak_db_tp": {"value": None},
                "stereo_correlation": {"value": None},
            },
            "summary": "unit unavailable",
        },
    )


def test_compact_context_summarizes_state_without_full_docs(tmp_path: Path) -> None:
    seed_compact_sources(tmp_path)
    context = build_compact_mix_context(project_name="unit", workspace_root=tmp_path, output_dir=Path("automix"))

    assert context["schema"] == "automix-compact-mix-context-v1"
    assert context["current_slug"] == "unit_v01"
    assert context["delivery_status"] == "blocked"
    assert context["safe_to_export"] is False
    assert context["source_stem_approval_status"] == "missing_or_unconfirmed"
    assert context["next_primary_mix_target"] in {
        "vocal_clarity",
        "vocal_center_stability",
        "female_layer_control",
        "low_end_density",
        "instrumental_presence",
        "ai_fizz_reduction",
        "master_cohesion",
        "limiter_pressure_control",
    }
    assert context["latest_qc_headline"]["status"] == "BLOCKED"
    assert context["active_path_safety_status"]["raw_full_mix_not_in_active_path"] is True
    assert context["quality_gate"]["hard_gate"]["source_approval_confirmed"] is False
    assert context["quality_gate"]["hard_gate"]["raw_full_mix_not_in_active_path"] is True
    assert context["claim_boundary"] == "planning_or_review_copy_only"
    assert context["assets"]["stem_count"] == 2
    assert context["plugin_trace"]["required_first_slot_ok"] is True
    assert context["readiness"]["safe_to_export"] is False
    assert "accepted_source_or_stem_evidence_missing" in context["blockers"]
    assert context["recommended_next_actions"]


def test_write_compact_context_outputs_json_and_markdown(tmp_path: Path) -> None:
    seed_compact_sources(tmp_path)
    context = build_compact_mix_context(project_name="unit", workspace_root=tmp_path, output_dir=Path("automix"))
    paths = write_compact_mix_context(context, Path("work/state/RUN_CONTEXT.compact.json"), workspace_root=tmp_path)

    assert Path(paths["json"]).exists()
    assert Path(paths["markdown"]).exists()
    assert Path(paths["quality_gate_json"]).exists()
    assert Path(paths["latest_qc_json"]).exists()
    assert Path(paths["open_blockers_json"]).exists()
    assert Path(paths["read_order_md"]).exists()
    assert Path(paths["token_budget_md"]).exists()
    assert Path(paths["pass_plan_template_json"]).exists()
    assert Path(paths["pass_plan_latest_json"]).exists()
    assert Path(paths["reference_profile_template_json"]).exists()
    saved = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    assert saved["token_policy"]["default_candidate_renders"] == 1
    quality_gate = json.loads(Path(paths["quality_gate_json"]).read_text(encoding="utf-8"))
    assert "hard_gate" in quality_gate
    assert "soft_gate" in quality_gate


def test_compact_context_cli_writes_summary(tmp_path: Path) -> None:
    seed_compact_sources(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_compact_mix_context.py"),
            "--project-name",
            "unit",
            "--workspace-root",
            str(tmp_path),
            "--output-dir",
            "automix",
            "--context-path",
            "work/state/RUN_CONTEXT.compact.json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    summary = json.loads(result.stdout)

    assert result.returncode == 0
    assert summary["status"] == "written"
    assert Path(summary["context_json"]).exists()
    assert summary["claim_boundary"] == "planning_or_review_copy_only"
