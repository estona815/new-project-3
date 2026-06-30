from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.automix_orchestrator import WORKFLOW_MODES
from automix.plugins.plugin_adapter_schema import create_adapter, default_semantic_control, write_json
from automix.real_project.recovery_only_pilot import run_recovery_only_pilot


RECOVERY_CONTROLS = [
    "utility_gain_db",
    "low_cut_hz",
    "mud_dynamic_cut_amount",
    "nasal_dynamic_cut_amount",
    "harshness_dynamic_cut_amount",
    "sibilance_control_amount",
    "high_fizz_control_amount",
    "side_noise_reduction_amount",
    "formant_protection",
    "transient_preserve",
    "body_preserve",
    "body_recovery_amount",
    "output_gain_db",
]


def write_project(tmp_path: Path) -> Path:
    project = tmp_path / "prompt43_project.json"
    write_json(
        project,
        {
            "schema": "prompt43-mock-project-v1",
            "tracks": [
                {"track_index": 1, "name": "Lead Vocal AI", "track_guid": "{LEAD}", "role": "lead_vocal", "media_items": 1, "fx": []},
                {"track_index": 2, "name": "Full Mix Reference", "track_guid": "{FULL}", "role": "full_mix_reference", "media_items": 1, "fx": []},
                {"track_index": 3, "name": "Mystery Track", "track_guid": "{UNK}", "role": "unknown", "media_items": 1, "fx": []},
                {"track_index": 4, "name": "Instrumental Bus", "track_guid": "{INST}", "role": "instrumental_bus", "media_items": 1, "fx": []},
                {"track_index": 5, "name": "Fragile Thin Vocal", "track_guid": "{THIN}", "role": "lead_vocal", "media_items": 1, "fx": []},
            ],
        },
    )
    return project


def write_prompt42_outputs(tmp_path: Path, *, plugin_safe: bool = False, readiness_ready: bool = True, readiness_blockers: list[str] | None = None) -> Path:
    output = tmp_path / "automix"
    project = write_project(tmp_path)
    (output / "eval_reports").mkdir(parents=True, exist_ok=True)
    (output / "analysis_reports").mkdir(parents=True, exist_ok=True)
    (output / "real_project").mkdir(parents=True, exist_ok=True)
    write_json(output / "eval_reports/real_project_scan_only_report.md", {"note": "placeholder"})
    write_json(
        output / "eval_reports/real_project_safe_draft_readiness.json",
        {
            "project_name": "prompt43_project",
            "ready": readiness_ready,
            "blockers": readiness_blockers or [],
            "readiness_breakdown": {
                "prompt41_validation": 1.0,
                "read_only_guard": 1.0,
                "plugin_mapping_readiness": 1.0 if plugin_safe else 0.0,
                "source_quality_readiness": 1.0,
                "stem_availability": 1.0,
                "report_completeness": 1.0,
                "rollback_preparedness": 1.0,
            },
        },
    )
    tracks = [
        {
            "index": 1,
            "track_name": "Lead Vocal AI",
            "track_guid": "{LEAD}",
            "role": "lead_vocal",
            "source_classification": "ai_vocal_stem",
            "vocal_likelihood": 0.86,
            "full_mix_likelihood": 0.12,
            "source_separated_likelihood": 0.18,
            "already_mixed_score": 0.55,
            "already_tuned_score": 0.50,
            "recovery_risk": "medium",
            "warnings": [],
        },
        {
            "index": 2,
            "track_name": "Full Mix Reference",
            "track_guid": "{FULL}",
            "role": "full_mix_reference",
            "source_classification": "full_mix",
            "vocal_likelihood": 0.25,
            "full_mix_likelihood": 0.90,
            "source_separated_likelihood": 0.10,
            "recovery_risk": "unsafe",
            "warnings": [],
        },
        {
            "index": 3,
            "track_name": "Mystery Track",
            "track_guid": "{UNK}",
            "role": "unknown",
            "source_classification": "unknown",
            "vocal_likelihood": 0.20,
            "full_mix_likelihood": 0.10,
            "source_separated_likelihood": 0.0,
            "recovery_risk": "unsafe",
            "warnings": [],
        },
        {
            "index": 4,
            "track_name": "Instrumental Bus",
            "track_guid": "{INST}",
            "role": "instrumental_bus",
            "source_classification": "full_mix",
            "vocal_likelihood": 0.10,
            "full_mix_likelihood": 0.82,
            "source_separated_likelihood": 0.0,
            "recovery_risk": "unsafe",
            "warnings": [],
        },
        {
            "index": 5,
            "track_name": "Fragile Thin Vocal",
            "track_guid": "{THIN}",
            "role": "lead_vocal",
            "source_classification": "ai_vocal_stem",
            "vocal_likelihood": 0.82,
            "full_mix_likelihood": 0.12,
            "source_separated_likelihood": 0.10,
            "already_mixed_score": 0.40,
            "recovery_risk": "medium",
            "warnings": [],
        },
    ]
    write_json(output / "analysis_reports/real_project_track_audit.json", {"project_name": "prompt43_project", "tracks": tracks})
    write_json(
        output / "eval_reports/real_project_source_safety_map.json",
        {
            "project_name": "prompt43_project",
            "summary": {
                "safe_vocal_candidates": 2,
                "ai_or_already_processed_vocals": 2,
                "source_separated_vocals": 0,
                "full_mix_unsafe_tracks": 2,
                "stem_required_tracks": 2,
                "unknown_tracks": 1,
            },
        },
    )
    write_json(
        output / "eval_reports/real_project_plugin_readiness.json",
        {
            "project_name": "prompt43_project",
            "safe_adapters_count": 1 if plugin_safe else 0,
            "provisional_adapters_count": 0,
            "unsafe_unmapped_plugins_count": 0 if plugin_safe else 1,
            "safe_draft_plugin_ready": plugin_safe,
            "can_run_recovery_drafts_safely": plugin_safe,
        },
    )
    write_json(
        output / "real_project/read_only_guard_report.json",
        {
            "project_name": "prompt43_project",
            "safe": True,
            "modified": False,
            "warnings": [],
        },
    )
    write_json(output / "rollback/global_rollback_registry.json", {"project_name": "prompt43_project", "validation": {"passed": True}})
    if plugin_safe:
        write_safe_adapter_and_inventory(output)
    return project


def write_safe_adapter_and_inventory(output: Path) -> None:
    controls = {
        semantic: default_semantic_control(
            semantic,
            target_name=semantic,
            confidence=0.96,
            write_allowed=True,
            validated=True,
            safe_min=-24.0 if semantic.endswith("_db") else 0.0,
            safe_max=240.0 if semantic.endswith("_hz") else 1.0,
            default=0.0,
        )
        for semantic in RECOVERY_CONTROLS
    }
    adapter = create_adapter(
        adapter_id="safe_recovery_adapter",
        plugin_name_patterns=["Safe Recovery"],
        plugin_type="stock_recovery",
        semantic_controls=controls,
        confidence=0.96,
        safe_for_automix=True,
    )
    adapter["validation"] = {"status": "passed", "last_validated_at": "2026-05-31T00:00:00Z"}
    for control in adapter["semantic_controls"].values():
        control["validated"] = True
        control["write_allowed"] = True
        control["writable"] = True
    write_json(output / "plugins/learned_adapters/safe_recovery_adapter.json", adapter)
    write_json(
        output / "analysis_reports/plugin_inventory_audit.json",
        {
            "project_name": "prompt43_project",
            "plugins_detected": [
                {
                    "name": "Safe Recovery",
                    "safe_for_automix": True,
                    "mapping_status": "validated_safe",
                    "confidence": 0.96,
                    "kind": "stock",
                    "capabilities": ["vocal_recovery"],
                }
            ],
            "unsafe_or_unmapped_plugins": [],
            "summary": {"validated_safe_count": 1},
        },
    )


def test_workflow_mode_exists() -> None:
    assert "recovery_only_pilot" in WORKFLOW_MODES


def test_missing_prompt42_blocks_recovery(tmp_path: Path) -> None:
    project = write_project(tmp_path)
    summary = run_recovery_only_pilot(project_path=project, output_dir=tmp_path / "automix", dry_run=True)
    assert summary["status"] == "blocked"
    assert "PROMPT42_OUTPUTS_MISSING" in summary["blockers"]
    assert (tmp_path / "automix/eval_reports/recovery_only_blocker_report.json").exists()


def test_plugin_mapping_blocker_blocks_recovery(tmp_path: Path) -> None:
    project = write_prompt42_outputs(tmp_path, plugin_safe=False, readiness_ready=False, readiness_blockers=["validated_plugin_mapping_required"])
    summary = run_recovery_only_pilot(project_path=project, output_dir=tmp_path / "automix", dry_run=True)
    selection = json.loads((tmp_path / "automix/eval_reports/recovery_only_track_selection.json").read_text(encoding="utf-8"))
    assert summary["status"] == "blocked"
    assert summary["eligible_recovery_tracks"] == 0
    assert any("PLUGIN_MAPPING_UNSAFE" in item["blocked_reason_codes"] for item in selection["blocked_tracks"])
    assert summary["recovery_drafts_created"] == 0


def test_eligible_tracks_and_blocked_tracks_are_visible(tmp_path: Path) -> None:
    project = write_prompt42_outputs(tmp_path, plugin_safe=True)
    summary = run_recovery_only_pilot(project_path=project, output_dir=tmp_path / "automix", dry_run=True)
    selection = json.loads((tmp_path / "automix/eval_reports/recovery_only_track_selection.json").read_text(encoding="utf-8"))
    assert summary["eligible_recovery_tracks"] == 2
    assert {item["track_name"] for item in selection["eligible_tracks"]} == {"Lead Vocal AI", "Fragile Thin Vocal"}
    blocked = {item["track_name"]: item["blocked_reason_codes"] for item in selection["blocked_tracks"]}
    assert "FULL_MIX_UNSAFE_FOR_VOCAL_RECOVERY" in blocked["Full Mix Reference"]
    assert "UNKNOWN_SOURCE_BLOCKED" in blocked["Mystery Track"]
    assert "ROLE_NOT_RECOVERY_ELIGIBLE" in blocked["Instrumental Bus"]


def test_dry_run_creates_no_tracks_but_writes_chain_plan_and_pitch_block(tmp_path: Path) -> None:
    project = write_prompt42_outputs(tmp_path, plugin_safe=True)
    summary = run_recovery_only_pilot(project_path=project, output_dir=tmp_path / "automix", dry_run=True)
    assert summary["dry_run"] is True
    assert summary["recovery_drafts_created"] == 0
    assert summary["pitch_block_status"] is True
    assert (tmp_path / "automix/eval_reports/recovery_only_pitch_block_report.json").exists()
    plans = sorted((tmp_path / "automix/chain_plans").glob("*_recovery_only_chain_plan.json"))
    assert plans
    assert all(json.loads(path.read_text(encoding="utf-8"))["contains_pitch_correction"] is False for path in plans)


def test_apply_drafts_on_json_copy_preserves_original_and_writes_rollback(tmp_path: Path) -> None:
    project = write_prompt42_outputs(tmp_path, plugin_safe=True)
    before = project.read_text(encoding="utf-8")
    summary = run_recovery_only_pilot(project_path=project, output_dir=tmp_path / "automix", apply_drafts=True, dry_run=False)
    after = project.read_text(encoding="utf-8")
    assert before == after
    assert summary["recovery_drafts_created"] == 2
    assert summary["original_protection_safe"] is True
    assert (tmp_path / "automix/real_project/recovery_only_draft_project.json").exists()
    registry = json.loads((tmp_path / "automix/rollback/recovery_only_rollback_registry.json").read_text(encoding="utf-8"))
    assert registry["all_entries_valid"] is True
    assert len(registry["entries"]) == 2


def test_render_disabled_evaluation_cannot_pass(tmp_path: Path) -> None:
    project = write_prompt42_outputs(tmp_path, plugin_safe=True)
    summary = run_recovery_only_pilot(project_path=project, output_dir=tmp_path / "automix", dry_run=True)
    assert summary["ab_render_status"] == "plan_only"
    eval_files = sorted((tmp_path / "automix/eval_reports").glob("*_recovery_only_eval_metrics.json"))
    assert eval_files
    assert all(json.loads(path.read_text(encoding="utf-8"))["evaluation_passed"] is False for path in eval_files)


def test_parameter_log_skips_unknown_or_unmapped_controls(tmp_path: Path) -> None:
    project = write_prompt42_outputs(tmp_path, plugin_safe=True)
    run_recovery_only_pilot(project_path=project, output_dir=tmp_path / "automix", dry_run=True)
    log = json.loads((tmp_path / "automix/logs/recovery_only_parameter_write_log.json").read_text(encoding="utf-8"))
    assert log["fixed_parameter_indexes_used"] is False
    assert log["unknown_parameters_skipped"] is True
    assert log["parameters_written"]


def test_cli_default_is_dry_run_and_no_final_export(tmp_path: Path) -> None:
    project = write_prompt42_outputs(tmp_path, plugin_safe=True)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_recovery_only_pilot.py"),
            "--project",
            str(project),
            "--output-dir",
            str(tmp_path / "automix"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["dry_run"] is True
    assert data["recovery_drafts_created"] == 0
    assert data["pitch_block_status"] is True


def test_docs_exist() -> None:
    assert (ROOT / "docs/recovery_only_pilot.md").exists()
    assert (ROOT / "docs/manual_test_plan_prompt43.md").exists()


if __name__ == "__main__":
    current = globals()
    failures: list[str] = []
    for name in sorted(k for k in current if k.startswith("test_")):
        fn = current[name]
        try:
            if "tmp_path" in fn.__code__.co_varnames:
                with tempfile.TemporaryDirectory() as directory:
                    fn(Path(directory))
            else:
                fn()
        except Exception as exc:  # pragma: no cover
            failures.append(f"{name}: {exc}")
    if failures:
        raise SystemExit("\n".join(failures))
    print("Prompt43 direct tests passed")

