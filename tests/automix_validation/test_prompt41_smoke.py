from __future__ import annotations

import json
from pathlib import Path

from automix.plugins.adapter_confidence_gate import evaluate_adapter_confidence
from automix.plugins.plugin_inventory_audit import audit_plugin_inventory, write_plugin_capability_report
from automix.plugins.safe_parameter_writer import safe_parameter_write_operation
from automix.plugins.plugin_adapter_schema import create_adapter, default_semantic_control

from tests.automix_validation.prompt41_validation_common import FIXTURES, ensure_prompt41_fixtures, output_dir
from tests.automix_validation.scripts.mock_render_validation import build_mock_render_manifest


def test_prompt41_fixture_generation_creates_required_assets(tmp_path: Path) -> None:
    manifests = ensure_prompt41_fixtures()
    assert len(manifests["audio"]["fixtures"]) == 14
    assert len(manifests["analysis"]["fixtures"]) == 16
    assert len(manifests["projects"]["projects"]) == 4
    first_audio = Path(manifests["audio"]["fixtures"][0]["path"])
    assert (first_audio if first_audio.is_absolute() else FIXTURES / first_audio).exists()
    audio_tags = {tag for fixture in manifests["audio"]["fixtures"] for tag in fixture.get("coverage_tags", [])}
    analysis_paths = [Path(path) for path in manifests["analysis"]["fixtures"]]
    analysis_tags = set()
    for path in analysis_paths:
        analysis_tags.update(json.loads(path.read_text(encoding="utf-8")).get("coverage_tags", []))
    assert {"muddy_vocal", "phase_issue", "over_limited_master"}.issubset(audio_tags)
    assert {"corrupted_config", "render_failure", "feedback_mapping"}.issubset(analysis_tags)


def test_plugin_intelligence_runs_without_third_party_plugins(tmp_path: Path) -> None:
    out = output_dir(tmp_path)
    audit = audit_plugin_inventory({"detected_plugins": [], "reaper": {"version": "mock", "project_name": "prompt41"}}, output_dir=out, adapters=[])
    report = write_plugin_capability_report(audit, out)
    assert audit["summary"]["validated_safe_count"] == 0
    assert any(item["plugin"] == "MAutoPitch" and item["normal"] for item in audit["missing_expected_plugins"])
    assert report.exists()


def test_unmapped_third_party_plugin_is_unsafe(tmp_path: Path) -> None:
    out = output_dir(tmp_path)
    audit = audit_plugin_inventory(
        {"detected_plugins": [{"name": "VST3: Soundtoys Decapitator", "capabilities": ["saturator"], "confidence": 0.92}]},
        output_dir=out,
        adapters=[],
    )
    assert audit["unsafe_or_unmapped_plugins"][0]["name"] == "Soundtoys Decapitator"
    assert audit["unsafe_or_unmapped_plugins"][0]["mapping_status"] == "unmapped"


def test_adapter_gate_blocks_low_confidence_mapping() -> None:
    low = create_adapter(
        adapter_id="low_adapter",
        plugin_name_patterns=["Low Confidence Plugin"],
        semantic_controls={"gain_db": default_semantic_control("gain_db", target_name="Gain", confidence=0.30)},
        confidence=0.30,
    )
    gate = evaluate_adapter_confidence(
        desired_semantic_controls=["gain_db"],
        adapter=low,
        plugin_name="Low Confidence Plugin",
        plugin_detected=True,
        workflow_stage="premaster",
    )
    assert gate["allowed"] is False
    assert "ADAPTER_CONFIDENCE_LOW" in gate["reason_codes"]


def test_safe_parameter_writer_skips_unknown_controls(tmp_path: Path) -> None:
    adapter = create_adapter(
        adapter_id="blocked_adapter",
        plugin_name_patterns=["Blocked"],
        semantic_controls={"gain_db": default_semantic_control("gain_db", target_name="Gain", confidence=0.80)},
        confidence=0.80,
    )
    log = safe_parameter_write_operation(
        operation="prompt41_smoke",
        plugin_name="Blocked",
        track_name="Lead",
        semantic_settings={"unknown": 0.5, "gain_db": 4.0},
        adapter=adapter,
        output_dir=output_dir(tmp_path),
        dry_run=True,
    )
    reasons = {item["reason"] for item in log["skipped"]}
    assert "UNKNOWN_PLUGIN_PARAMETER" in reasons
    assert "SEMANTIC_CONTROL_NOT_WRITE_ALLOWED" in reasons
    assert "TrackFX_SetParam" not in json.dumps(log)


def test_mock_render_missing_cannot_pass(tmp_path: Path) -> None:
    manifest = build_mock_render_manifest(output_dir(tmp_path), missing_render=True)
    assert manifest["evaluation_passed"] is False
    assert manifest["renders"][0]["reason"] == "render_file_missing"
