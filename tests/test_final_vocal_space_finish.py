from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.final_vocal_space_finish import run_final_vocal_space_finish
from automix.plugins.plugin_adapter_schema import write_json


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_finish_inputs(tmp_path: Path, *, accepted: bool = True, decision: str = "accepted", plugin_ready: bool = True, rejected_later: bool = False) -> Path:
    out = tmp_path / "automix"
    for subdir in ("review", "eval_reports", "rollback"):
        (out / subdir).mkdir(parents=True, exist_ok=True)
    sources = []
    if accepted:
        sources.append(
            {
                "original_track_name": "Lead Vocal Original",
                "original_track_guid": "{ORIG}",
                "accepted_draft_track_name": "Lead Vocal_RECOVERY_DRAFT_v01",
                "accepted_draft_track_guid": "{DRAFT}",
                "decision": decision,
                "fragile_source": decision == "accepted_light",
                "allowed_for_placement": True,
                "allowed_for_pitch_triage": True,
                "allowed_for_final_export": False,
                "provisional_acceptance": False,
                "warnings": [],
            }
        )
    write_json(out / "review" / "accepted_recovery_sources.json", {"schema": "x", "project_name": "unit_project", "accepted_sources": sources, "blocked_sources": []})
    write_json(
        out / "review" / "rejected_recovery_drafts.json",
        {
            "schema": "x",
            "project_name": "unit_project",
            "rejected": [{"draft_track_name": "Lead Vocal_RECOVERY_DRAFT_v01"}] if rejected_later else [],
            "needs_revision": [],
            "manual_cleanup_required": [],
            "stem_required": [],
        },
    )
    (out / "eval_reports" / "recovery_review_report.md").write_text("# review\n", encoding="utf-8")
    write_json(out / "rollback" / "recovery_only_rollback_registry.json", {"schema": "x", "project_name": "unit_project", "entries": [], "all_entries_valid": True})
    write_json(
        out / "eval_reports" / "recovery_only_original_protection_report.json",
        {"schema": "x", "project_name": "unit_project", "safe": True, "pitch_plugin_inserted_anywhere": False},
    )
    write_json(
        out / "eval_reports" / "real_project_plugin_readiness.json",
        {
            "schema": "x",
            "project_name": "unit_project",
            "safe_adapters_count": 4 if plugin_ready else 0,
            "can_run_vocal_placement_safely": plugin_ready,
            "can_run_premaster_draft_safely": plugin_ready,
            "safe_draft_plugin_ready": plugin_ready,
            "warnings": [],
        },
    )
    write_json(
        out / "eval_reports" / "real_project_track_audit.json",
        {
            "schema": "x",
            "project_name": "unit_project",
            "tracks": [
                {"role": "lead_vocal", "track_name": "Lead Vocal_RECOVERY_DRAFT_v01", "source_classification": "raw_vocal", "instrumental_likelihood": 0.0},
                {"role": "instrumental_bus", "track_name": "INSTRUMENTAL BUS", "source_classification": "instrumental_stem", "instrumental_likelihood": 0.8},
                {"role": "backing_vocal", "track_name": "Backing Vocal L/R", "source_classification": "raw_vocal"},
                {"role": "reverb_send", "track_name": "Vocal Verb Return", "source_classification": "unknown"},
                {"role": "delay_send", "track_name": "Vocal Delay Return", "source_classification": "unknown"},
            ],
        },
    )
    return out


def test_missing_accepted_recovery_blocks(tmp_path: Path) -> None:
    out = write_finish_inputs(tmp_path, accepted=False)
    summary = run_final_vocal_space_finish(output_dir=out, make_review_package=True)
    assert summary["preconditions_ok"] is False
    assert "no_accepted_recovery_sources" in summary["blockers"]
    assert summary["placement_draft_created"] is False
    assert read_json(out / "eval_reports/finalizing_blocked_stages.json")["pitch_correction_blocked"] is True


def test_rejected_recovery_source_blocks(tmp_path: Path) -> None:
    out = write_finish_inputs(tmp_path, rejected_later=True)
    summary = run_final_vocal_space_finish(output_dir=out)
    assert "accepted_recovery_source_rejected_later" in summary["blockers"]
    assert summary["placement_draft_created"] is False


def test_accepted_light_uses_fragile_profile_and_blocks_pitch(tmp_path: Path) -> None:
    out = write_finish_inputs(tmp_path, decision="accepted_light")
    summary = run_final_vocal_space_finish(output_dir=out, apply_placement_draft=True, dry_run=False)
    chain = read_json(out / "chain_plans/final_vocal_space_carving_chain_plan.json")
    blocked = read_json(out / "eval_reports/finalizing_blocked_stages.json")
    assert summary["fragile_source"] is True
    assert chain["selected_profile"] == "fragile_ai_vocal_space"
    assert chain["semantic_settings"]["vocal_gain_db"] <= 0.0
    assert blocked["pitch_plugins_inserted"] is False


def test_dry_run_modifies_nothing_and_creates_proposal(tmp_path: Path) -> None:
    out = write_finish_inputs(tmp_path)
    summary = run_final_vocal_space_finish(output_dir=out, apply_placement_draft=True, dry_run=True, generate_review_form=True)
    rollback = read_json(out / "rollback/final_vocal_space_carving_rollback.json")
    assert summary["placement_draft_created"] is False
    assert rollback["created_draft_tracks"] == []
    assert (out / "review/final_vocal_space_review_form.md").exists()


def test_apply_metadata_draft_keeps_originals_and_rollback(tmp_path: Path) -> None:
    out = write_finish_inputs(tmp_path)
    summary = run_final_vocal_space_finish(output_dir=out, apply_placement_draft=True, dry_run=False, strict_protection=True)
    rollback = read_json(out / "rollback/final_vocal_space_carving_rollback.json")
    protection = read_json(out / "eval_reports/final_vocal_space_protection_report.json")
    assert summary["placement_draft_created"] is True
    assert rollback["safe_to_delete_draft"] is True
    assert protection["original_tracks_unchanged"] is True
    assert protection["no_pitch_plugin_inserted"] is True


def test_premaster_blocked_before_placement_review(tmp_path: Path) -> None:
    out = write_finish_inputs(tmp_path)
    summary = run_final_vocal_space_finish(output_dir=out, apply_safe_premaster_draft=True)
    premaster = read_json(out / "chain_plans/final_safe_premaster_chain_plan.json")
    assert summary["premaster_draft_created"] is False
    assert premaster["selected_profile"] == "blocked_until_placement_review"
    assert summary["final_export_created"] is False


def test_premaster_created_only_after_explicit_review_acceptance(tmp_path: Path) -> None:
    out = write_finish_inputs(tmp_path)
    summary = run_final_vocal_space_finish(
        output_dir=out,
        apply_placement_draft=True,
        dry_run=False,
        accept_placement_review=True,
        apply_safe_premaster_draft=True,
    )
    premaster = read_json(out / "chain_plans/final_safe_premaster_chain_plan.json")
    assert summary["premaster_draft_created"] is True
    assert premaster["selected_profile"] == "safe_streaming_premaster"
    assert premaster["final_export_allowed"] is False


def test_ab_missing_never_passes(tmp_path: Path) -> None:
    out = write_finish_inputs(tmp_path)
    summary = run_final_vocal_space_finish(output_dir=out, render_ab=True)
    metrics = read_json(out / "eval_reports/final_vocal_space_eval_metrics.json")
    assert summary["ab_evaluation_passed"] is False
    assert metrics["evaluation_passed"] is False
    assert metrics["renders_created"]["loudness_matched"] is False


def test_review_package_not_final(tmp_path: Path) -> None:
    out = write_finish_inputs(tmp_path)
    summary = run_final_vocal_space_finish(output_dir=out, make_review_package=True, deliverables_root=tmp_path / "deliverables")
    package = Path(summary["review_package_path"])
    manifest = read_json(package / "Manifests/review_package_manifest.json")
    assert package.exists()
    assert "REVIEW_PACKAGE" in package.name
    assert "FINAL" not in package.name
    assert manifest["ready_for_delivery"] is False
    assert Path(summary["review_package_zip"]).exists()


def test_cli_dry_run_creates_report(tmp_path: Path) -> None:
    out = write_finish_inputs(tmp_path, accepted=False)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_final_vocal_space_finish.py"),
            "--output-dir",
            str(out),
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["preconditions_ok"] is False
    assert (out / "eval_reports/finalizing_vocal_space_and_review_package_report.md").exists()


def test_docs_exist() -> None:
    assert (ROOT / "docs/final_vocal_space_finish_workflow.md").exists()
    assert (ROOT / "docs/manual_test_plan_final_vocal_space_finish.md").exists()


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
    print("Final vocal space finish direct tests passed")
