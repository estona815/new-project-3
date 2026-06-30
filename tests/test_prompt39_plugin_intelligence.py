from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.adapter_confidence_gate import evaluate_adapter_confidence
from automix.plugins.plugin_adapter_schema import create_adapter, default_semantic_control, validate_adapter_schema
from automix.plugins.plugin_inventory_audit import audit_plugin_inventory
from automix.plugins.plugin_parameter_learner import learn_adapter_from_parameter_list
from automix.plugins.plugin_parameter_validator import validate_adapter
from automix.plugins.preset_safety import generate_safe_preset
from automix.plugins.safe_parameter_writer import safe_parameter_write_operation
from automix.plugins.third_party_plugin_policy import evaluate_third_party_policy


def validated_adapter(plugin_name: str = "Safe Gain") -> dict:
    controls = {
        "gain_db": default_semantic_control(
            "gain_db",
            target_name="Gain",
            confidence=0.96,
            write_allowed=True,
            safe_min=-6.0,
            safe_max=3.0,
        ),
        "dry_wet": default_semantic_control(
            "dry_wet",
            target_name="Mix",
            confidence=0.96,
            write_allowed=True,
            safe_min=0.0,
            safe_max=1.0,
        ),
    }
    adapter = create_adapter(
        adapter_id="safe_gain_adapter",
        plugin_name_patterns=[plugin_name],
        semantic_controls=controls,
        confidence=0.96,
        safe_for_automix=True,
    )
    adapter["validation"] = {"status": "passed", "last_validated_at": "2026-05-31T00:00:00Z"}
    for control in adapter["semantic_controls"].values():
        control["validated"] = True
        control["write_allowed"] = True
        control["writable"] = True
    adapter["safe_for_automix"] = True
    return adapter


def test_adapter_schema_requires_validation_before_writes() -> None:
    adapter = create_adapter(
        adapter_id="provisional",
        plugin_name_patterns=["Unknown EQ"],
        semantic_controls={"gain_db": default_semantic_control("gain_db", target_name="Gain", confidence=0.80)},
        confidence=0.80,
    )
    assert adapter["safe_for_automix"] is False
    assert adapter["semantic_controls"]["gain_db"]["write_allowed"] is False
    assert validate_adapter_schema(adapter) == []


def test_parameter_learner_creates_provisional_write_blocked_adapter(tmp_path: Path) -> None:
    adapter = learn_adapter_from_parameter_list(
        "MeldaProduction MAutoPitch",
        [
            {"index": 0, "name": "Correction Amount"},
            {"index": 1, "name": "Dry/Wet"},
            {"index": 2, "name": "Preset"},
            {"index": 3, "name": "Unclear Secret Param"},
        ],
        output_dir=tmp_path / "automix",
    )
    assert adapter["safe_for_automix"] is False
    assert adapter["semantic_controls"]["correction_amount"]["write_allowed"] is False
    assert adapter["do_not_touch_parameters"][0]["name"] == "Preset"
    assert adapter["unknown_parameters"][0]["name"] == "Unclear Secret Param"
    assert (tmp_path / "automix/plugins/learned_adapters/meldaproduction_mautopitch_adapter.json").exists()


def test_validator_does_not_fake_success_without_plugin_runtime(tmp_path: Path) -> None:
    adapter = learn_adapter_from_parameter_list("ReaEQ", ["Gain"], output_dir=None)
    updated, report = validate_adapter(adapter, output_dir=tmp_path / "automix", plugin_available=False)
    assert report["status"] == "validation_unavailable"
    assert updated["safe_for_automix"] is False
    assert updated["semantic_controls"]["gain_db"]["write_allowed"] is False
    assert report["no_fake_success"] is True


def test_validator_enables_only_observed_semantic_controls() -> None:
    adapter = learn_adapter_from_parameter_list("Utility", ["Gain", "Mix"], output_dir=None)
    updated, report = validate_adapter(
        adapter,
        plugin_available=True,
        validation_observations={"controls": {"gain_db": {"passed": True, "confidence": 0.93}}},
    )
    assert report["status"] == "passed"
    assert updated["semantic_controls"]["gain_db"]["write_allowed"] is True
    assert updated["semantic_controls"]["dry_wet"]["write_allowed"] is False


def test_third_party_policy_blocks_unvalidated_or_dangerous_plugins() -> None:
    assert evaluate_third_party_policy("Soundtoys Decapitator", None)["allowed"] is False
    assert "ADAPTER_MISSING" in evaluate_third_party_policy("TDR Nova", None)["reason_codes"]
    ott = validated_adapter("Xfer OTT")
    ott["semantic_controls"]["amount"] = default_semantic_control("amount", target_name="Amount", confidence=0.96, write_allowed=True)
    ott["semantic_controls"]["depth"] = default_semantic_control("depth", target_name="Depth", confidence=0.96, write_allowed=True)
    ott["semantic_controls"]["output_gain"] = default_semantic_control("output_gain", target_name="Output", confidence=0.96, write_allowed=True)
    for control in ott["semantic_controls"].values():
        control["validated"] = True
        control["write_allowed"] = True
        control["writable"] = True
    decision = evaluate_third_party_policy("Xfer OTT", ott, source_context={"compressed_source": True})
    assert decision["allowed"] is False
    assert "SOURCE_ALREADY_COMPRESSED" in decision["reason_codes"]


def test_adapter_confidence_gate_fails_closed_and_allows_validated_adapter() -> None:
    closed = evaluate_adapter_confidence(
        desired_semantic_controls=["gain_db"],
        adapter=None,
        plugin_name="Unknown",
        plugin_detected=False,
        workflow_stage="premaster",
    )
    assert closed["allowed"] is False
    assert "ADAPTER_MISSING" in closed["reason_codes"]
    open_gate = evaluate_adapter_confidence(
        desired_semantic_controls=["gain_db"],
        adapter=validated_adapter(),
        plugin_name="Safe Gain",
        plugin_detected=True,
        workflow_stage="vocal_recovery",
    )
    assert open_gate["allowed"] is True
    assert open_gate["controls_allowed"]["gain_db"]["safe_max"] == 3.0


def test_safe_parameter_writer_clamps_skips_unknown_and_logs(tmp_path: Path) -> None:
    adapter = validated_adapter()
    log = safe_parameter_write_operation(
        operation="unit_test",
        plugin_name="Safe Gain",
        track_name="Lead",
        semantic_settings={"gain_db": 9.0, "unknown_control": 0.5},
        adapter=adapter,
        output_dir=tmp_path / "automix",
        dry_run=True,
    )
    assert log["written"][0]["clamped_value"] == 3.0
    assert log["written"][0]["written"] is False
    assert log["skipped"][0]["reason"] == "UNKNOWN_PLUGIN_PARAMETER"
    assert Path(log["path"]).exists()


def test_generated_presets_stay_under_automix_generated_presets(tmp_path: Path) -> None:
    preset = generate_safe_preset(
        plugin_name="Safe Gain",
        adapter=validated_adapter(),
        preset_type="safe_draft",
        semantic_controls={"gain_db": -2.0},
        workflow_stage="unit_test",
        output_dir=tmp_path / "automix",
    )
    path = Path(preset["path"])
    assert "generated_presets" in path.parts
    assert path.exists()
    assert preset["user_preset_overwrite_allowed"] is False


def test_inventory_audit_marks_unmapped_plugins_unsafe(tmp_path: Path) -> None:
    inventory = {
        "scan_date_utc": "2026-05-31T00:00:00Z",
        "reaper": {"version": "7.x", "project_name": "unit"},
        "detected_plugins": [
            {"name": "VST3: TDR Nova", "capabilities": ["dynamic_eq"], "confidence": 0.90},
            {"name": "Mystery Enhancer", "capabilities": ["unknown"], "confidence": 0.20},
        ],
    }
    audit = audit_plugin_inventory(inventory, output_dir=tmp_path / "automix", adapters=[])
    assert audit["summary"]["detected_count"] == 2
    assert audit["summary"]["validated_safe_count"] == 0
    assert {item["name"] for item in audit["unsafe_or_unmapped_plugins"]} == {"TDR Nova", "Mystery Enhancer"}
    assert (tmp_path / "automix/analysis_reports/plugin_inventory_audit.json").exists()


def test_cli_writes_audit_and_report(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_intelligence_audit.py"),
            "--scan",
            "--report",
            "--dry-run",
            "--output-dir",
            str(tmp_path / "automix"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout)["status"] == "ok"
    assert (tmp_path / "automix/analysis_reports/plugin_inventory_audit.json").exists()
    assert (tmp_path / "automix/eval_reports/plugin_capability_report.md").exists()


def test_docs_and_builtin_adapters_exist() -> None:
    assert (ROOT / "docs/plugin_intelligence_and_adapter_safety.md").exists()
    assert (ROOT / "automix/plugins/builtin_adapters/reaeq_adapter.json").exists()
    assert (ROOT / "automix/plugins/builtin_adapters/reacomp_adapter.json").exists()


if __name__ == "__main__":
    current = globals()
    failures: list[str] = []
    for name in sorted(k for k in current if k.startswith("test_")):
        fn = current[name]
        try:
            if "tmp_path" in getattr(fn, "__annotations__", {}) or "tmp_path" in fn.__code__.co_varnames:
                with tempfile.TemporaryDirectory() as directory:
                    fn(Path(directory))
            else:
                fn()
        except Exception as exc:  # pragma: no cover - direct runner diagnostics
            failures.append(f"{name}: {exc}")
    if failures:
        raise SystemExit("\n".join(failures))
    print("Prompt39 direct tests passed")
