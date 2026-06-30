from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.open_risk_register import build_open_risk_register
from automix.orchestrator.report_index import build_report_index
from automix.plugins.plugin_adapter_schema import write_json


def write_clean_reports(out: Path) -> None:
    write_json(out / "eval_reports/intent_classification.json", {"schema": "x", "status": "safe_draft_intent_available", "safe_next_mode": "safe_draft_no_pitch", "safe_draft_intents": ["vocal_rescue"], "blockers": [], "warnings": []})
    write_json(out / "eval_reports/real_project_source_safety_map.json", {"schema": "x", "summary": {"stem_required_tracks": 0, "unknown_tracks": 0, "full_mix_unsafe_tracks": 0}, "high_risk_tracks": [], "warnings": []})
    write_json(out / "eval_reports/real_project_plugin_readiness.json", {"schema": "x", "safe_draft_plugin_ready": True, "missing_or_unsafe_mappings": [], "warnings": []})
    write_json(out / "eval_reports/global_qc_summary.json", {"schema": "x", "critical_blockers": [], "warnings": []})
    write_json(out / "eval_reports/processing_policy_audit.json", {"schema": "x", "passed": True, "blockers": [], "warnings": []})
    write_json(out / "eval_reports/fixture_coverage_audit.json", {"schema": "x", "passed": True, "blockers": [], "warnings": []})
    write_json(out / "eval_reports/requirements_traceability_audit.json", {"schema": "x", "passed": True, "blockers": [], "warnings": [], "incomplete_requirement_ids": []})
    write_json(out / "eval_reports/professional_readiness_audit.json", {"schema": "x", "ready_for_delivery": False, "blockers": [], "warnings": []})
    write_json(out / "eval_reports/claim_language_guard.json", {"schema": "x", "passed": True, "blockers": [], "warnings": []})
    write_json(out / "export/final_export_state.json", {"schema": "x", "safe_to_export": True, "blocked_reasons": [], "warnings": []})
    write_json(out / "export/final_render_manifest.json", {"schema": "x", "failures": [], "warnings": []})
    write_json(out / "export/deliverable_package_manifest.json", {"schema": "x", "package_created": True, "zip_path": str(out / "deliverables/unit.zip"), "package_size_bytes": 12, "files_missing": [], "warnings": []})
    write_json(out / "eval_reports/deliverable_package_evidence_gate.json", {"schema": "x", "ready_for_delivery_package": True, "blockers": [], "warnings": []})
    write_json(out / "export/project_state_manifest.json", {"schema": "x", "original_tracks_protected": True, "master_unchanged": True, "warnings": []})
    write_json(out / "rollback/global_rollback_registry.json", {"schema": "x", "validation": {"passed": True, "failures": []}, "warnings": []})


def test_open_risk_register_passes_with_clean_report_set(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_clean_reports(out)
    register = build_open_risk_register(project_name="unit", output_dir=out)
    assert register["passed"] is True
    assert register["risk_counts"]["blocker"] == 0
    assert (out / "eval_reports/open_risk_register.json").exists()
    md = (out / "eval_reports/open_risk_register.md").read_text(encoding="utf-8")
    assert "Open Risk Register" in md
    assert "does not prove audio quality" in md


def test_open_risk_register_collects_source_plugin_and_final_export_risks(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_clean_reports(out)
    write_json(
        out / "eval_reports/intent_classification.json",
        {
            "schema": "x",
            "status": "review_required",
            "safe_next_mode": "validate_plugin_mappings",
            "safe_draft_intents": [],
            "blockers": ["validated_plugin_mapping_required"],
            "warnings": ["no_validated_safe_plugin_adapters"],
        },
    )
    write_json(
        out / "eval_reports/real_project_source_safety_map.json",
        {
            "schema": "x",
            "summary": {"stem_required_tracks": 1, "unknown_tracks": 1, "full_mix_unsafe_tracks": 1},
            "high_risk_tracks": [
                {
                    "track_name": "SOURCE full mix reference muted",
                    "role": "full_mix_reference",
                    "source_classification": "full_mix",
                    "pitch_risk": "unsafe",
                    "recovery_risk": "unsafe",
                    "recommended_next_action": "provide_isolated_stems",
                    "warnings": ["full_mix_unsafe_for_pitch_correction"],
                }
            ],
            "warnings": ["unknown_tracks_are_not_eligible_for_automatic_processing"],
        },
    )
    write_json(
        out / "eval_reports/real_project_plugin_readiness.json",
        {
            "schema": "x",
            "safe_draft_plugin_ready": False,
            "missing_or_unsafe_mappings": ["OTT (Xfer Records)"],
            "warnings": ["no_validated_safe_plugin_adapters"],
        },
    )
    write_json(out / "export/final_export_state.json", {"schema": "x", "safe_to_export": False, "blocked_reasons": ["no_accepted_export_source"], "warnings": []})

    register = build_open_risk_register(project_name="unit", output_dir=out)
    codes = "\n".join(risk["code"] for risk in register["open_risks"])
    assert register["passed"] is False
    assert register["risk_counts"]["blocker"] >= 5
    assert "validated_plugin_mapping_required" in codes
    assert "stem_required_tracks:1" in codes
    assert "missing_or_unsafe_plugin_mapping:OTT (Xfer Records)" in codes
    assert "no_accepted_export_source" in codes
    assert any("provide isolated stems" in risk["recommended_next_action"] for risk in register["open_risks"])


def test_open_risk_register_cli_returns_nonzero_for_open_blockers(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_clean_reports(out)
    write_json(out / "export/final_export_state.json", {"schema": "x", "safe_to_export": False, "blocked_reasons": ["no_accepted_export_source"], "warnings": []})
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_open_risk_register.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert result.returncode == 2
    assert data["status"] == "open_blockers"
    assert "no_accepted_export_source" in data["blockers"]
    assert Path(data["report_json"]).exists()
    assert Path(data["report_md"]).exists()


def test_report_index_groups_open_risk_register(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_clean_reports(out)
    build_open_risk_register(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(item["stage"] == "delivery readiness" and item["summary"] == "open_risk_register.json" for item in index["reports"])


if __name__ == "__main__":
    current = globals()
    failures: list[str] = []
    for name in sorted(k for k in current if k.startswith("test_")):
        fn = current[name]
        try:
            with tempfile.TemporaryDirectory() as directory:
                fn(Path(directory))
        except Exception as exc:  # pragma: no cover
            failures.append(f"{name}: {exc}")
    if failures:
        raise SystemExit("\n".join(failures))
    print("Prompt52 direct tests passed")
