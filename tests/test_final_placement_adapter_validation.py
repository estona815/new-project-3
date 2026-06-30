from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.final_placement_adapter_mapping import validate_final_placement_adapters
from automix.plugins.plugin_adapter_schema import default_semantic_control, write_json


REQUIRED_CONTROLS = [
    "vocal_gain_db",
    "instrumental_duck_amount_db",
    "presence_duck_amount_db",
    "low_mid_duck_amount_db",
    "sibilance_conflict_duck_db",
    "duck_attack_ms",
    "duck_release_ms",
    "ms_mid_cleanup_amount",
    "ms_side_cleanup_amount",
    "backing_duck_amount_db",
    "send_duck_amount_db",
    "harshness_guard_amount",
    "sibilance_control_amount",
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_chain_plan(out: Path) -> Path:
    path = out / "chain_plans/final_vocal_space_carving_chain_plan.json"
    write_json(
        path,
        {
            "schema": "automix-final-vocal-space-carving-chain-plan-v1",
            "project_name": "unit_project",
            "draft_only": True,
            "contains_pitch_correction": False,
            "contains_master_limiter": False,
            "original_tracks_must_remain_untouched": True,
            "plugin_chain": [
                {"target_role": "lead_vocal", "category": "utility_gain", "plugin": "Safe Placement Processor", "semantic_settings": {"vocal_gain_db": 0.30}},
                {
                    "target_role": "instrumental_bus",
                    "category": "sidechain_dynamic_eq",
                    "plugin": "Safe Placement Processor",
                    "semantic_settings": {
                        "instrumental_duck_db": -0.6,
                        "presence_duck_db": -0.8,
                        "low_mid_duck_db": -0.5,
                        "sibilance_conflict_duck_db": -0.2,
                        "duck_attack_ms": 0.25,
                        "duck_release_ms": 0.55,
                    },
                },
                {"target_role": "instrumental_bus", "category": "ms_cleanup", "plugin": "Safe Placement Processor", "semantic_settings": {"ms_mid_cleanup": 0.10, "ms_side_cleanup": 0.05}},
                {"target_role": "backing_vocals", "category": "sidechain_ducker", "plugin": "Safe Placement Processor", "semantic_settings": {"backing_vocal_duck_db": -0.7, "duck_attack_ms": 0.25, "duck_release_ms": 0.55}},
                {"target_role": "send_returns", "category": "send_return_ducker", "plugin": "Safe Placement Processor", "semantic_settings": {"send_duck_db": -0.4, "duck_attack_ms": 0.25, "duck_release_ms": 0.55}},
                {"target_role": "lead_vocal", "category": "harshness_guard", "plugin": "Safe Placement Processor", "semantic_settings": {"vocal_harshness_guard": 0.10, "vocal_sibilance_guard": 0.08}},
                {"target_role": "lead_vocal", "category": "output_gain", "plugin": "Safe Placement Processor", "semantic_settings": {"vocal_gain_db": 0.30}},
            ],
        },
    )
    return path


def write_inventory(out: Path, plugin_name: str = "Safe Placement Processor") -> Path:
    path = out / "plugin_inventory.json"
    write_json(
        path,
        {
            "schema": "inventory",
            "scan_date_utc": "2026-05-31T00:00:00Z",
            "reaper": {"version": "mock", "project_name": "unit_project"},
            "detected_plugins": [{"name": plugin_name, "confidence": 0.95}],
            "insertable_plugins": [{"name": plugin_name, "confidence": 0.95, "insertable": True}],
        },
    )
    return path


def write_valid_adapter(out: Path, plugin_name: str = "Safe Placement Processor") -> Path:
    controls = {}
    for semantic in REQUIRED_CONTROLS:
        control = default_semantic_control(
            semantic,
            target_name=semantic.replace("_", " ").title(),
            confidence=0.96,
            write_allowed=True,
            validated=True,
            safe_min=-2.0 if semantic.endswith("_db") or "duck" in semantic else 0.0,
            safe_max=1.0,
        )
        control["normalization"] = "normalized_0_1"
        controls[semantic] = control
    adapter = {
        "schema": "automix-plugin-adapter-v1",
        "adapter_id": "safe_placement_processor_adapter",
        "plugin_name_patterns": [plugin_name],
        "normalized_plugin_name_patterns": [],
        "plugin_type": "test",
        "manufacturer": "unit",
        "version": "1",
        "platform": "test",
        "semantic_controls": controls,
        "confidence": 0.96,
        "safe_for_automix": True,
        "validation": {"status": "passed", "last_validated_at": "2026-05-31T00:00:00Z"},
        "warnings": [],
    }
    path = out / "plugins/learned_adapters/safe_placement_processor_adapter.json"
    write_json(path, adapter)
    return path


def test_no_validated_adapter_blocks(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    chain = write_chain_plan(out)
    inventory = write_inventory(out)
    report = validate_final_placement_adapters(output_dir=out, chain_plan_path=chain, inventory_path=inventory)
    assert report["apply_allowed"] is False
    assert any(reason.endswith("_adapter_not_validated") for reason in report["blocked_reasons"])
    assert (out / "chain_plans/final_vocal_space_applicator_plan.lua").exists()
    plan = read_json(out / "chain_plans/final_vocal_space_applicator_plan.json")
    assert plan["apply_allowed"] is False


def test_validated_adapter_allows_applicator_plan(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    chain = write_chain_plan(out)
    inventory = write_inventory(out)
    write_valid_adapter(out)
    report = validate_final_placement_adapters(output_dir=out, chain_plan_path=chain, inventory_path=inventory)
    assert report["apply_allowed"] is True
    assert report["all_required_categories_safe"] is True
    plan = read_json(out / "chain_plans/final_vocal_space_applicator_plan.json")
    assert plan["apply_allowed"] is True
    assert plan["fx_to_insert"]
    assert any(fx["parameter_writes"] for fx in plan["fx_to_insert"])
    assert plan["pitch_correction_blocked"] is True
    assert "mautopitch" not in json.dumps(plan).lower()


def test_disallowed_pitch_or_hype_plugin_name_blocks(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    chain = write_chain_plan(out)
    inventory = write_inventory(out, plugin_name="MAutoPitch")
    write_valid_adapter(out, plugin_name="MAutoPitch")
    report = validate_final_placement_adapters(output_dir=out, chain_plan_path=chain, inventory_path=inventory)
    assert report["apply_allowed"] is False
    assert any("DISALLOWED_PLUGIN_FOR_FINISHING_STAGE" in item["gate"]["reason_codes"] for item in report["category_results"])


def test_cli_writes_configured_applicator_enabled_only_when_safe(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    chain = write_chain_plan(out)
    inventory = write_inventory(out)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_final_placement_adapter_validation.py"),
            "--output-dir",
            str(out),
            "--chain-plan",
            str(chain),
            "--inventory",
            str(inventory),
            "--write-configured-applicator",
            "--enable-configured-applicator",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["apply_allowed"] is False
    assert data["configured_applicator_enabled"] is False
    configured = Path(data["configured_applicator"])
    assert configured.exists()
    assert "allow_final_vocal_space_placement = false" in configured.read_text(encoding="utf-8")

    write_valid_adapter(out)
    result2 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_final_placement_adapter_validation.py"),
            "--output-dir",
            str(out),
            "--chain-plan",
            str(chain),
            "--inventory",
            str(inventory),
            "--write-configured-applicator",
            "--enable-configured-applicator",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data2 = json.loads(result2.stdout)
    assert data2["apply_allowed"] is True
    assert data2["configured_applicator_enabled"] is True
    assert "allow_final_vocal_space_placement = true" in Path(data2["configured_applicator"]).read_text(encoding="utf-8")


def test_lua_applicator_is_disabled_and_blocks_final_export_paths() -> None:
    script = (ROOT / "automix/apply_final_vocal_space_placement_draft.lua").read_text(encoding="utf-8")
    assert "allow_final_vocal_space_placement = false" in script
    assert "TrackFX_SetParam" in script
    assert "TrackFX_GetParamName" in script
    assert "Main_SaveProject" not in script
    assert "RenderFileSection" not in script
    assert "pitch_correction_blocked" in script


def test_docs_exist() -> None:
    assert (ROOT / "docs/final_placement_adapter_validation.md").exists()
    assert (ROOT / "docs/manual_test_plan_final_placement_adapter_validation.md").exists()


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
    print("Final placement adapter validation direct tests passed")
