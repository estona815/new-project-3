from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.export.final_export_state_resolver import resolve_final_export_state
from automix.orchestrator.automix_orchestrator import AutoMixOrchestrator, WORKFLOW_MODES
from automix.orchestrator.stage_status import StageStatus
from automix.plugins.plugin_adapter_schema import write_json
from automix.review.recovery_review_gate import run_recovery_review_gate


def write_prompt43_outputs(tmp_path: Path, *, drafts: bool = True, protection_safe: bool = True, pitch_ok: bool = True, eval_passed: bool | None = None) -> Path:
    out = tmp_path / "automix"
    (out / "eval_reports").mkdir(parents=True, exist_ok=True)
    (out / "rollback").mkdir(parents=True, exist_ok=True)
    (out / "real_project").mkdir(parents=True, exist_ok=True)
    (out / "eval_reports/recovery_only_pilot_report.md").write_text("# Recovery-Only Pilot Report\n", encoding="utf-8")
    write_json(out / "eval_reports/recovery_only_track_selection.json", {"project_name": "prompt44_project"})
    entries = []
    if drafts:
        entries = [
            {
                "original_track_name": "Lead Vocal",
                "original_track_guid": "{LEAD}",
                "draft_track_name": "Lead Vocal_RECOVERY_DRAFT_v01",
                "draft_track_guid": "{DRAFT1}",
                "rollback_file": "automix/rollback/lead_recovery_only_rollback.json",
                "safe_to_rollback": True,
            },
            {
                "original_track_name": "Backing Vocal",
                "original_track_guid": "{BACK}",
                "draft_track_name": "Backing Vocal_RECOVERY_DRAFT_v01",
                "draft_track_guid": "{DRAFT2}",
                "rollback_file": "automix/rollback/backing_recovery_only_rollback.json",
                "safe_to_rollback": True,
            },
        ]
    write_json(out / "rollback/recovery_only_rollback_registry.json", {"project_name": "prompt44_project", "entries": entries, "all_entries_valid": True})
    write_json(
        out / "eval_reports/recovery_only_original_protection_report.json",
        {"project_name": "prompt44_project", "safe": protection_safe, "original_tracks_modified": not protection_safe},
    )
    write_json(
        out / "eval_reports/recovery_only_pitch_block_report.json",
        {
            "pitch_stage_blocked": pitch_ok,
            "pitch_plugins_inserted": not pitch_ok,
            "pitch_parameters_written": False,
            "blocked_controls": [],
        },
    )
    write_json(
        out / "eval_reports/recovery_only_ab_render_plan.json",
        {
            "project_name": "prompt44_project",
            "render_enabled": False,
            "tracks_to_render": [],
            "tracks_not_rendered": [
                {"original_track_name": item["original_track_name"], "draft_track_name": item["draft_track_name"], "reason": "A/B render required for acceptance"}
                for item in entries
            ],
        },
    )
    if eval_passed is not None and drafts:
        for entry in entries:
            write_json(
                out / "eval_reports" / f"{entry['original_track_name']}_recovery_only_eval_metrics.json",
                {
                    "track_name": entry["original_track_name"],
                    "renders_created": {
                        "original": True,
                        "recovery_draft": True,
                        "loudness_matched": True,
                        "difference": True,
                    },
                    "evaluation_passed": eval_passed,
                    "recommended_action": "accept" if eval_passed else "manual_review_required",
                    "warnings": [] if eval_passed else ["damage_detected"],
                },
            )
    return out


def write_decisions(path: Path, decisions: list[dict]) -> Path:
    write_json(path, {"reviewer": "user", "decisions": decisions})
    return path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_workflow_modes_exist() -> None:
    assert "recovery_review" in WORKFLOW_MODES
    assert "recovery_review_form_only" in WORKFLOW_MODES


def test_orchestrator_recovery_review_blocks_without_prompt43(tmp_path: Path) -> None:
    manifest = AutoMixOrchestrator({"mode": "recovery_review_form_only", "output_dir": str(tmp_path / "automix"), "dry_run": True}).run()
    statuses = {item["stage"]: item for item in manifest["stage_results"]}
    review = statuses["recovery_review_gate"]
    assert review["status"] == StageStatus.BLOCKED.value
    assert "PROMPT43_OUTPUTS_MISSING" in review["blockers"]
    assert review["manual_action_type"] == "review_recovery_drafts"


def test_missing_prompt43_blocks_acceptance(tmp_path: Path) -> None:
    summary = run_recovery_review_gate(output_dir=tmp_path / "automix", accept_draft="x", decision="accepted", acknowledge_warnings=True)
    assert summary["prompt43_precondition_ok"] is False
    assert "PROMPT43_OUTPUTS_MISSING" in summary["prompt43_blockers"]
    assert summary["decisions_imported"] == 0
    assert (tmp_path / "automix/review/recovery_review_blocker_report.json").exists()


def test_no_drafts_creates_no_recovery_recommendation(tmp_path: Path) -> None:
    out = write_prompt43_outputs(tmp_path, drafts=False)
    summary = run_recovery_review_gate(output_dir=out)
    assert summary["drafts_to_review"] == 0
    assert summary["final_recommendation"] == "no_recovery_drafts_to_review"
    state = read_json(out / "review/recovery_review_state.json")
    assert state["global_downstream_allowed"] is False


def test_default_needs_review_blocks_downstream(tmp_path: Path) -> None:
    out = write_prompt43_outputs(tmp_path)
    summary = run_recovery_review_gate(output_dir=out, generate_form=True)
    state = read_json(out / "review/recovery_review_state.json")
    gate = read_json(out / "orchestrator/downstream_recovery_gate.json")
    assert summary["decisions_imported"] == 0
    assert all(item["decision"] == "needs_review" for item in state["drafts"])
    assert gate["accepted_sources_available"] is False
    assert "final_export" in gate["blocked_downstream_stages"]
    assert (out / "review/recovery_review_form.md").exists()


def test_accept_without_ab_requires_provisional_flag_and_ack(tmp_path: Path) -> None:
    out = write_prompt43_outputs(tmp_path)
    decisions = write_decisions(
        out / "review_decisions.json",
        [
            {
                "draft_track_name": "Lead Vocal_RECOVERY_DRAFT_v01",
                "decision": "accepted",
                "notes": "Sounds better at rough check",
                "warnings_acknowledged": ["A/B render required before final use"],
            }
        ],
    )
    blocked = run_recovery_review_gate(output_dir=out, input_decisions=decisions, acknowledge_warnings=True)
    assert blocked["decisions_imported"] == 0
    assert any("AB_REVIEW_REQUIRED_FOR_ACCEPTANCE" in err for err in blocked["errors"])
    accepted = run_recovery_review_gate(output_dir=out, input_decisions=decisions, acknowledge_warnings=True, allow_provisional_without_ab=True)
    assert accepted["decisions_imported"] == 1
    sources = read_json(out / "review/accepted_recovery_sources.json")
    assert sources["accepted_sources"][0]["provisional_acceptance"] is True
    assert sources["accepted_sources"][0]["allowed_for_final_export"] is False


def test_accepted_light_marks_fragile_and_pitch_caution(tmp_path: Path) -> None:
    out = write_prompt43_outputs(tmp_path)
    decisions = write_decisions(
        out / "review_decisions.json",
        [
            {
                "draft_track_name": "Lead Vocal_RECOVERY_DRAFT_v01",
                "decision": "accepted_light",
                "notes": "Cleaner but fragile",
                "warnings_acknowledged": ["A/B render required before final use"],
            }
        ],
    )
    summary = run_recovery_review_gate(output_dir=out, input_decisions=decisions, acknowledge_warnings=True, allow_provisional_without_ab=True)
    sources = read_json(out / "review/accepted_recovery_sources.json")
    assert summary["accepted_drafts"] == 1
    assert sources["accepted_sources"][0]["fragile_source"] is True
    assert sources["accepted_sources"][0]["pitch_extra_caution"] is True
    assert "pitch_triage" in read_json(out / "orchestrator/downstream_recovery_gate.json")["allowed_downstream_stages"]


def test_rejected_needs_revision_stem_and_manual_cleanup_are_grouped(tmp_path: Path) -> None:
    out = write_prompt43_outputs(tmp_path)
    decisions = write_decisions(
        out / "review_decisions.json",
        [
            {"draft_track_name": "Lead Vocal_RECOVERY_DRAFT_v01", "decision": "rejected", "notes": "Dull", "warnings_acknowledged": ["x"]},
            {"draft_track_name": "Backing Vocal_RECOVERY_DRAFT_v01", "decision": "needs_revision", "notes": "Too lispy", "warnings_acknowledged": ["x"]},
        ],
    )
    summary = run_recovery_review_gate(output_dir=out, input_decisions=decisions, acknowledge_warnings=True)
    rejected = read_json(out / "review/rejected_recovery_drafts.json")
    assert summary["rejected_drafts"] == 1
    assert summary["revision_requests"] == 1
    assert rejected["rejected"][0]["recommended_action"] == "rollback_or_keep_muted"
    assert "Too lispy" in (out / "review/recovery_revision_request.md").read_text(encoding="utf-8")


def test_existing_decision_not_overwritten_without_update(tmp_path: Path) -> None:
    out = write_prompt43_outputs(tmp_path)
    first = write_decisions(out / "first.json", [{"draft_track_name": "Lead Vocal_RECOVERY_DRAFT_v01", "decision": "rejected", "notes": "Bad", "warnings_acknowledged": ["x"]}])
    second = write_decisions(out / "second.json", [{"draft_track_name": "Lead Vocal_RECOVERY_DRAFT_v01", "decision": "accepted", "notes": "Changed", "warnings_acknowledged": ["x"]}])
    run_recovery_review_gate(output_dir=out, input_decisions=first, acknowledge_warnings=True)
    summary = run_recovery_review_gate(output_dir=out, input_decisions=second, acknowledge_warnings=True, allow_provisional_without_ab=True)
    state = read_json(out / "review/recovery_review_state.json")
    lead = next(item for item in state["drafts"] if item["draft_track_name"] == "Lead Vocal_RECOVERY_DRAFT_v01")
    assert lead["decision"] == "rejected"
    assert any("decision_exists_requires_update" in err for err in summary["errors"])
    run_recovery_review_gate(output_dir=out, input_decisions=second, acknowledge_warnings=True, allow_provisional_without_ab=True, update=True)
    state = read_json(out / "review/recovery_review_state.json")
    lead = next(item for item in state["drafts"] if item["draft_track_name"] == "Lead Vocal_RECOVERY_DRAFT_v01")
    assert lead["decision"] == "accepted"


def test_failed_protection_or_pitch_block_prevents_import(tmp_path: Path) -> None:
    out = write_prompt43_outputs(tmp_path, protection_safe=False)
    decisions = write_decisions(out / "d.json", [{"draft_track_name": "Lead Vocal_RECOVERY_DRAFT_v01", "decision": "accepted", "warnings_acknowledged": ["x"]}])
    summary = run_recovery_review_gate(output_dir=out, input_decisions=decisions, acknowledge_warnings=True, allow_provisional_without_ab=True)
    assert "ORIGINAL_PROTECTION_FAILED" in summary["prompt43_blockers"]
    assert summary["decisions_imported"] == 0
    out2 = write_prompt43_outputs(tmp_path / "p2", pitch_ok=False)
    decisions2 = write_decisions(out2 / "d.json", [{"draft_track_name": "Lead Vocal_RECOVERY_DRAFT_v01", "decision": "accepted", "warnings_acknowledged": ["x"]}])
    summary2 = run_recovery_review_gate(output_dir=out2, input_decisions=decisions2, acknowledge_warnings=True, allow_provisional_without_ab=True)
    assert "PITCH_BLOCK_FAILED" in summary2["prompt43_blockers"]
    assert summary2["decisions_imported"] == 0


def test_ab_complete_and_eval_passed_allows_normal_acceptance(tmp_path: Path) -> None:
    out = write_prompt43_outputs(tmp_path, eval_passed=True)
    decisions = write_decisions(out / "d.json", [{"draft_track_name": "Lead Vocal_RECOVERY_DRAFT_v01", "decision": "accepted", "notes": "Pass", "warnings_acknowledged": ["reviewed"]}])
    summary = run_recovery_review_gate(output_dir=out, input_decisions=decisions, acknowledge_warnings=True)
    sources = read_json(out / "review/accepted_recovery_sources.json")
    assert summary["decisions_imported"] == 1
    assert sources["accepted_sources"][0]["provisional_acceptance"] is False


def test_final_export_resolver_blocks_unreviewed_recovery() -> None:
    state = resolve_final_export_state(
        project_name="unit",
        workflow_state={"recovery_review": {"recovery_review_required": True, "review_status": "pending", "accepted_sources_available": False}},
    )
    assert state["safe_to_export"] is False
    assert "recovery_draft_human_review_required" in state["blocked_reasons"]


def test_cli_generates_form_and_imports_one_decision(tmp_path: Path) -> None:
    out = write_prompt43_outputs(tmp_path)
    decisions = write_decisions(
        out / "review_decisions.json",
        [{"draft_track_name": "Lead Vocal_RECOVERY_DRAFT_v01", "decision": "accepted_light", "notes": "Fragile", "warnings_acknowledged": ["x"]}],
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_recovery_review_gate.py"),
            "--output-dir",
            str(out),
            "--input-decisions",
            str(decisions),
            "--acknowledge-warnings",
            "--allow-provisional-without-ab",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["decisions_imported"] == 1
    assert (out / "review/recovery_review_form.md").exists()


def test_docs_exist() -> None:
    assert (ROOT / "docs/recovery_draft_human_review.md").exists()
    assert (ROOT / "docs/manual_test_plan_prompt44.md").exists()


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
    print("Prompt44 direct tests passed")
