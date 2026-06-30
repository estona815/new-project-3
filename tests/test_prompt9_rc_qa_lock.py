from __future__ import annotations

import json
import os
from pathlib import Path

from VOCAL_CLARITY_REPAIR_SYSTEM.eval.preset_policy import load_factory_presets, sanitize_preset_values
from VOCAL_CLARITY_REPAIR_SYSTEM.eval.rc_qa import (
    JSFX,
    RC_METADATA,
    installed_jsfx_check,
    load_rc_metadata,
    parameter_freeze_rows,
    realtime_static_audit,
    run_synthetic_release_matrix,
    validate_parameter_freeze,
    validate_version_metadata,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM" / "scripts" / "run_rc_qa.sh"
PARAMETER_TABLE = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM" / "docs" / "parameter_freeze_table.md"
DAW_CHECKLIST = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM" / "docs" / "daw_compatibility_checklist.md"
RELEASE_NOTES = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM" / "docs" / "release_notes_rc1.md"
FINAL_REPORT = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM" / "reports" / "prompt9_final_rc_qa_report.md"


MANDATORY_IDS = {
    "Amount",
    "DryWet",
    "MaxSuppressionDb",
    "MaskStrength",
    "VocalPreserve",
    "ClarityPreserve",
    "AirPreserve",
    "TransientPreserve",
    "HarmonicPreserve",
    "MultibandEnabled",
    "MSEnabled",
    "MidAmount",
    "SideAmount",
    "SurgicalArtifactReduction",
    "ResidualMonitor",
    "MultibandMode",
    "Bypass",
}


def test_rc_metadata_is_explicit_and_not_claiming_unbuilt_formats() -> None:
    metadata = load_rc_metadata()

    assert RC_METADATA.exists()
    assert validate_version_metadata(metadata) == []
    assert metadata["plugin_version"] == "0.9.0-rc-lock"
    assert metadata["factory_preset_version"] == "codex-vocal-factory-presets-v1"
    assert metadata["parameter_schema_version"] == "codex-vocal-parameter-schema-v1"
    assert metadata["model"]["model_version"] == "none"
    assert metadata["latency"]["reported_latency_samples"] == 0
    assert metadata["supported_plugin_formats"] == ["REAPER JSFX"]
    assert "VST3" in metadata["unvalidated_plugin_formats"]
    assert metadata["current_release_state"] == "qa_lock_ready_not_rc_approved"


def test_parameter_freeze_rows_cover_mandatory_parameters_and_defaults() -> None:
    rows = parameter_freeze_rows()
    ids = {row["id"] for row in rows}

    assert MANDATORY_IDS <= ids
    assert validate_parameter_freeze() == []
    assert len(rows) >= 29
    amount = next(row for row in rows if row["id"] == "Amount")
    assert amount["mapping"] == "pow(userAmount, 1.6)"
    assert amount["default"] == 30.0
    strong_mode = next(row for row in rows if row["id"] == "MultibandMode")
    assert strong_mode["default"] == 0.0


def test_legacy_preset_states_migrate_to_safe_clamped_values() -> None:
    policy = load_factory_presets()
    old_missing_new = {"slider1": 44, "slider2": 44, "slider6": 65, "slider8": 0}
    old_aggressive = {"slider9": 95, "slider10": 99, "slider14": 3.0, "slider22": 9}
    old_no_preserve = {"slider16": None, "slider17": None, "slider18": None, "slider19": None}
    corrupted = {"slider9": "not-a-number", "slider10": float("inf"), "slider27": -100}

    migrated_missing = sanitize_preset_values(old_missing_new, policy)
    migrated_aggressive = sanitize_preset_values(old_aggressive, policy)
    migrated_no_preserve = sanitize_preset_values(old_no_preserve, policy)
    migrated_corrupted = sanitize_preset_values(corrupted, policy)

    assert migrated_missing["slider1"] == 44
    assert migrated_missing["slider9"] == policy["parameter_definitions"]["slider9"]["default"]
    assert migrated_aggressive["slider10"] == 24
    assert migrated_aggressive["slider14"] == 1
    assert migrated_aggressive["slider22"] == 3
    assert migrated_no_preserve["slider16"] == policy["parameter_definitions"]["slider16"]["default"]
    assert migrated_no_preserve["slider18"] == policy["parameter_definitions"]["slider18"]["default"]
    assert migrated_corrupted["slider9"] == policy["parameter_definitions"]["slider9"]["default"]
    assert migrated_corrupted["slider27"] == 0


def test_realtime_static_audit_and_installed_jsfx_sync_are_locked() -> None:
    audit = realtime_static_audit()
    installed = installed_jsfx_check()

    assert JSFX.exists()
    assert audit["status"] == "pass"
    assert audit["forbidden_hits"] == []
    assert installed["status"] in {"pass", "warning"}


def test_prompt9_quick_synthetic_matrix_covers_block_and_sample_rates(tmp_path: Path) -> None:
    result = run_synthetic_release_matrix(tmp_path, quick=True)

    assert result["release_gate"]["status"] == "pass"
    assert result["release_gate"]["blockers"] == []
    assert {entry["block_size"] for entry in result["block_size_results"]} == {1, 256, 4096}
    assert {entry["sample_rate"] for entry in result["sample_rate_results"]} == {44100, 48000}


def test_final_qa_script_exists_and_invokes_rc_qa_module() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert SCRIPT.exists()
    assert os.access(SCRIPT, os.X_OK)
    assert "VOCAL_CLARITY_REPAIR_SYSTEM.eval.rc_qa" in text
    assert "CODEX_VOCAL_RC_QA_DIR" in text


def test_prompt9_docs_and_reports_contain_ship_blockers() -> None:
    parameter_table = PARAMETER_TABLE.read_text(encoding="utf-8")
    daw = DAW_CHECKLIST.read_text(encoding="utf-8")
    notes = RELEASE_NOTES.read_text(encoding="utf-8")
    report = FINAL_REPORT.read_text(encoding="utf-8")

    assert "Do not rename existing IDs" in parameter_table
    assert "REAPER JSFX" in daw
    assert "unsupported/unclaimed" in daw
    assert "not a final shipping approval" in notes
    assert "not approved for shipping yet" in report
    assert "Do not ship if Preserve sounds cleaner but lower fidelity" in report


def test_rc_metadata_json_is_parseable_from_disk() -> None:
    parsed = json.loads(RC_METADATA.read_text(encoding="utf-8"))

    assert parsed["schema"] == "codex-vocal-rc-metadata-v1"
