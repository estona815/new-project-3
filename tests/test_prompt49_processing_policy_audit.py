from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.global_qc_aggregator import build_global_qc_summary
from automix.orchestrator.report_index import build_report_index
from automix.plugins.plugin_adapter_schema import write_json
from automix.safety.processing_policy_audit import build_processing_policy_audit


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_intent(out: Path, cap: float = 0.30) -> None:
    write_json(
        out / "eval_reports/intent_classification.json",
        {
            "schema": "automix-intent-classification-v1",
            "project_name": "unit",
            "intents": [
                {
                    "intent": "suno_artifact_suppression",
                    "conservative_mode": True,
                    "artifact_focus_score": 0.8,
                    "max_artifact_focus_dry_wet": cap,
                }
            ],
            "safe_draft_intents": ["suno_artifact_suppression"],
            "status": "safe_draft_intent_available",
        },
    )


def write_safe_chain(out: Path) -> Path:
    path = out / "chain_plans/safe_vocal_cleanup_chain_plan.json"
    write_json(
        path,
        {
            "schema": "automix-safe-vocal-cleanup-chain-plan-v1",
            "project_name": "unit",
            "draft_only": True,
            "safe_to_apply": False,
            "original_tracks_must_remain_untouched": True,
            "contains_pitch_correction": False,
            "contains_master_limiter_on_original": False,
            "contains_master_widening": False,
            "no_fixed_parameter_indexes": True,
            "plugin_chain": [
                {
                    "plugin": "validated dynamic EQ adapter",
                    "category": "dynamic_eq",
                    "adapter_confidence": 0.92,
                    "requires_parameter_discovery": False,
                    "safe_to_apply": False,
                    "no_fixed_parameter_indexes": True,
                    "semantic_settings": {"dry_wet": 0.18, "dynamic_eq_amount": 0.22},
                }
            ],
        },
    )
    return path


def test_processing_policy_audit_passes_conservative_draft_plan(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_intent(out)
    write_safe_chain(out)
    audit = build_processing_policy_audit(project_name="unit", output_dir=out)
    assert audit["passed"] is True
    assert audit["plans_checked"] == 1
    assert audit["blockers"] == []
    assert (out / "eval_reports/processing_policy_audit.json").exists()
    md = (out / "eval_reports/processing_policy_audit.md").read_text(encoding="utf-8")
    assert "Processing Policy Audit" in md
    assert "does not apply FX or prove audio quality" in md


def test_processing_policy_audit_blocks_ott_saturation_widening_and_original_master_limiter(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_intent(out, cap=0.30)
    write_json(
        out / "chain_plans/dangerous_chain_plan.json",
        {
            "schema": "automix-dangerous-chain-plan-v1",
            "project_name": "unit",
            "draft_only": False,
            "safe_to_apply": True,
            "contains_master_limiter_on_original": True,
            "contains_master_widening": True,
            "modifies_original_master": True,
            "no_fixed_parameter_indexes": False,
            "plugin_chain": [
                {
                    "plugin": "Xfer OTT",
                    "category": "ott",
                    "adapter_confidence": 0.40,
                    "requires_parameter_discovery": True,
                    "safe_to_apply": True,
                    "semantic_settings": {"dry_wet": 0.70, "amount": 0.80},
                },
                {
                    "plugin": "Soundtoys Decapitator",
                    "category": "aggressive_saturation",
                    "safe_to_apply": True,
                    "semantic_settings": {"saturation_amount": 0.85},
                },
                {
                    "plugin": "Stereo Widener",
                    "category": "stereo_width",
                    "semantic_settings": {"stereo_width_change": 0.50},
                },
                {
                    "plugin": "Ozone Maximizer",
                    "category": "limiter",
                    "semantic_settings": {"limiter_max_gain_db": 5.0, "target_lufs": -5.5},
                },
            ],
        },
    )
    audit = build_processing_policy_audit(project_name="unit", output_dir=out)
    blockers = "\n".join(audit["blockers"])
    assert audit["passed"] is False
    assert "chain_plan_not_draft_only" in blockers
    assert "master_limiter_on_original_master_blocked" in blockers
    assert "ott_style_processing_blocked_by_default" in blockers
    assert "aggressive_saturation_plugin_blocked_by_default" in blockers
    assert "blind_stereo_widening_blocked" in blockers
    assert "dry_wet_exceeds_conservative_cap" in blockers
    assert "saturation_amount_too_high" in blockers
    assert "limiter_gain_too_high_for_policy" in blockers
    assert "target_lufs_too_hot_for_default_policy" in blockers


def test_processing_policy_cli_returns_nonzero_for_blockers(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_intent(out)
    write_json(out / "chain_plans/bad.json", {"schema": "x", "draft_only": False, "plugin_chain": [{"plugin": "Xfer OTT", "category": "ott"}]})
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_processing_policy_audit.py"),
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
    assert data["status"] == "blocked"
    assert Path(data["report_json"]).exists()
    assert Path(data["report_md"]).exists()


def test_global_qc_blocks_final_delivery_when_processing_policy_fails(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_intent(out)
    write_json(out / "eval_reports/final_qc_metrics.json", {"schema": "x", "qc_passed": True, "warnings": []})
    write_json(out / "chain_plans/bad.json", {"schema": "x", "draft_only": True, "contains_master_limiter_on_original": True, "plugin_chain": []})
    summary = build_global_qc_summary(project_name="unit", output_dir=out, stage_results=[], final_delivery_requested=True)
    assert summary["safe_to_export"] is False
    assert "processing_policy_audit_failed" in summary["critical_blockers"]
    assert summary["processing_policy_audit"]["passed"] is False


def test_report_index_groups_processing_policy_audit(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_intent(out)
    write_safe_chain(out)
    build_processing_policy_audit(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(item["stage"] == "processing safety" and item["summary"] == "processing_policy_audit.json" for item in index["reports"])


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
    print("Prompt49 direct tests passed")
