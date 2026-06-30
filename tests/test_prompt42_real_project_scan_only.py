from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.automix_orchestrator import WORKFLOW_MODES, AutoMixOrchestrator
from automix.real_project.read_only_project_guard import compare_project_snapshots, snapshot_project_state
from automix.real_project.real_project_scan_only import run_real_project_scan_only


def write_project(tmp_path: Path) -> Path:
    project = tmp_path / "prompt42_mock_real_project.json"
    project.write_text(
        json.dumps(
            {
                "schema": "prompt42-mock-project-v1",
                "project_name": "prompt42_mock_real_project",
                "tracks": [
                    {"track_index": 1, "name": "Lead Vocal Raw", "track_guid": "{LEAD}", "role": "lead_vocal", "media_items": 1, "fx": []},
                    {"track_index": 2, "name": "Lead Vocal AI Tuned", "track_guid": "{TUNED}", "role": "lead_vocal", "media_items": 1, "fx": []},
                    {"track_index": 3, "name": "Watery Separated Vocal", "track_guid": "{SEP}", "role": "lead_vocal", "media_items": 1, "fx": []},
                    {"track_index": 4, "name": "Full Mix Reference", "track_guid": "{FULL}", "role": "full_mix_reference", "media_items": 1, "fx": []},
                    {"track_index": 5, "name": "Mystery Track", "track_guid": "{UNK}", "role": "unknown", "media_items": 0, "fx": []},
                    {"track_index": 6, "name": "Instrumental Bus", "track_guid": "{INST}", "role": "instrumental_bus", "media_items": 1, "fx": []},
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return project


def write_prompt41_pass(output: Path) -> None:
    report_dir = output / "validation_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "prompt41_validation_summary.json").write_text(
        json.dumps({"schema": "prompt41-validation-summary-v1", "final_validation_status": "PROMPT41_VALIDATION_PASS"}) + "\n",
        encoding="utf-8",
    )
    (report_dir / "prompt41_validation_summary.md").write_text("`PROMPT41_VALIDATION_PASS`\n", encoding="utf-8")


def run_scan(tmp_path: Path, prompt41: bool = True) -> dict:
    project = write_project(tmp_path)
    output = tmp_path / "automix"
    if prompt41:
        write_prompt41_pass(output)
    return run_real_project_scan_only(
        project_path=project,
        output_dir=output,
        target_profile="digicore_hyperpop_hiphop_vocal_forward",
        check_prompt41=True,
        strict_read_only=True,
        dry_run=True,
    )


def test_workflow_mode_exists_and_is_dry_run(tmp_path: Path) -> None:
    assert "real_project_scan_only" in WORKFLOW_MODES
    project = write_project(tmp_path)
    orchestrator = AutoMixOrchestrator({"mode": "real_project_scan_only", "project_path": str(project), "output_dir": str(tmp_path / "automix")})
    assert orchestrator.mode == "real_project_scan_only"
    assert orchestrator.config["dry_run"] is True
    assert orchestrator.config["strict_read_only"] is True


def test_read_only_guard_detects_no_change_and_field_changes(tmp_path: Path) -> None:
    project = write_project(tmp_path)
    before = snapshot_project_state(project)
    after = snapshot_project_state(project)
    assert compare_project_snapshots(before, after)["safe"] is True
    mutated = json.loads(json.dumps(after))
    mutated["fx_counts_per_track"][0] += 1
    assert compare_project_snapshots(before, mutated)["modified"] is True
    mutated = json.loads(json.dumps(after))
    mutated["send_counts"][0] += 1
    assert compare_project_snapshots(before, mutated)["modified"] is True
    mutated = json.loads(json.dumps(after))
    mutated["master_fx_count"] += 1
    assert compare_project_snapshots(before, mutated)["modified"] is True
    mutated = json.loads(json.dumps(after))
    mutated["media_item_counts"][0] += 1
    assert compare_project_snapshots(before, mutated)["modified"] is True


def test_scan_only_creates_all_real_project_reports_and_modifies_nothing(tmp_path: Path) -> None:
    summary = run_scan(tmp_path)
    output = tmp_path / "automix"
    assert summary["status"] == "real_project_scan_only_complete"
    assert summary["read_only_guard_safe"] is True
    assert summary["project_modified"] is False
    assert summary["tracks_scanned"] == 6
    assert (output / "real_project/read_only_guard_report.json").exists()
    assert (output / "analysis_reports/real_project_track_audit.json").exists()
    assert (output / "eval_reports/real_project_source_safety_map.json").exists()
    assert (output / "eval_reports/real_project_plugin_readiness.json").exists()
    assert (output / "chain_plans/real_project_dry_run_chain_proposals.json").exists()
    assert (output / "eval_reports/real_project_stem_request_plan.md").exists()
    assert (output / "eval_reports/real_project_safe_draft_readiness.json").exists()
    assert (output / "eval_reports/real_project_scan_only_report.md").exists()


def test_prompt41_missing_warns_but_scan_continues(tmp_path: Path) -> None:
    summary = run_scan(tmp_path, prompt41=False)
    readiness = json.loads((tmp_path / "automix/eval_reports/real_project_safe_draft_readiness.json").read_text(encoding="utf-8"))
    assert summary["prompt41_validation_status"] == "missing"
    assert summary["real_project_pilot_risk"] == "elevated"
    assert readiness["ready"] is False
    assert readiness["recommended_next_mode"] == "run_prompt41_validation"


def test_prompt41_fail_blocks_safe_draft_readiness(tmp_path: Path) -> None:
    project = write_project(tmp_path)
    output = tmp_path / "automix"
    write_prompt41_pass(output)
    (output / "validation_reports/prompt41_validation_summary.json").write_text(
        json.dumps({"schema": "prompt41-validation-summary-v1", "final_validation_status": "PROMPT41_VALIDATION_FAIL"}) + "\n",
        encoding="utf-8",
    )
    summary = run_real_project_scan_only(project_path=project, output_dir=output, check_prompt41=True)
    readiness = json.loads((output / "eval_reports/real_project_safe_draft_readiness.json").read_text(encoding="utf-8"))
    assert summary["prompt41_validation_status"] == "FAIL"
    assert readiness["ready"] is False
    assert "prompt41_validation_required_before_safe_draft" in readiness["blockers"]


def test_source_safety_and_proposals_fail_closed(tmp_path: Path) -> None:
    run_scan(tmp_path)
    output = tmp_path / "automix"
    source_map = json.loads((output / "eval_reports/real_project_source_safety_map.json").read_text(encoding="utf-8"))
    proposals = json.loads((output / "chain_plans/real_project_dry_run_chain_proposals.json").read_text(encoding="utf-8"))
    assert source_map["summary"]["full_mix_unsafe_tracks"] >= 2
    assert source_map["summary"]["source_separated_vocals"] >= 1
    assert source_map["summary"]["stem_required_tracks"] >= 1
    pitch = [proposal for proposal in proposals["proposals"] if proposal["stage"] == "pitch_correction"]
    assert any("full_mix_pitch_blocked" in proposal["blockers"] for proposal in pitch)
    assert any("already_tuned_skip_strong_correction" in proposal["blockers"] for proposal in pitch)
    assert any("validated_plugin_mapping_required" in proposal["blockers"] for proposal in pitch)
    assert all(proposal["would_modify_project"] is False for proposal in proposals["proposals"])


def test_plugin_readiness_and_recommendation_are_explicit(tmp_path: Path) -> None:
    summary = run_scan(tmp_path)
    output = tmp_path / "automix"
    plugin = json.loads((output / "eval_reports/real_project_plugin_readiness.json").read_text(encoding="utf-8"))
    readiness = json.loads((output / "eval_reports/real_project_safe_draft_readiness.json").read_text(encoding="utf-8"))
    assert plugin["safe_draft_plugin_ready"] is False
    assert plugin["safe_adapters_count"] == 0
    assert readiness["ready"] is False
    assert readiness["recommended_next_mode"] in {
        "run_prompt41_validation",
        "validate_plugin_mappings",
        "provide_isolated_stems",
        "scan_only_again",
        "safe_draft_recovery_only",
        "safe_draft_no_pitch",
        "safe_draft_full_pipeline",
        "manual_mix_required",
    }
    assert summary["recommended_next_mode"] == readiness["recommended_next_mode"]


def test_cli_defaults_strict_read_only_and_dry_run(tmp_path: Path) -> None:
    project = write_project(tmp_path)
    output = tmp_path / "automix"
    write_prompt41_pass(output)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_real_project_scan_only.py"),
            "--project",
            str(project),
            "--output-dir",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["mode"] == "real_project_scan_only"
    assert data["dry_run"] is True
    assert data["strict_read_only"] is True
    assert data["project_modified"] is False


def test_documentation_exists() -> None:
    assert (ROOT / "docs/real_project_scan_only_pilot.md").exists()
    assert (ROOT / "docs/manual_test_plan_prompt42.md").exists()


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
    print("Prompt42 direct tests passed")

