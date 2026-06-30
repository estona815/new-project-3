from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.harness.mix_master_quality_harness import build_mix_master_quality_harness


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_handoff(root: Path, *, bad_reference_bus: bool = False) -> Path:
    handoff = root / "reaper-auto-mix-handoff"
    for rel in [
        "START_HERE.md",
        "AGENTS.md",
        "NEXT_PROMPT.md",
        "core/SOURCE_OF_TRUTH.md",
        "recipes/lua/target_mix_recipe.lua",
        "scripts/track_classifier.lua",
        "scripts/routing_builder.lua",
        "scripts/fx_chain_builder.lua",
        "scripts/plugin_registry.lua",
        "scripts/import_and_mix_stems.lua",
        "scripts/apply_mix_recipe.lua",
        "scripts/apply_revision_actions.lua",
        "scripts/render_setup.lua",
        "tools/analyze_audio.py",
        "tools/compare_audio.py",
        "tools/validate_recipe.py",
    ]:
        path = handoff / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {rel}\n", encoding="utf-8")
    write_json(
        handoff / "PROJECT_SNAPSHOT.json",
        {
            "project_name": "reaper-auto-mix",
            "known_risks": ["No audio/reference/renders included"],
            "next_actions": ["Run dry-run stem classification"],
        },
    )
    write_json(
        handoff / "PACKAGE_MANIFEST.json",
        {
            "package_name": "unit-handoff.zip",
            "included_files": [],
            "audio_files_included": [],
        },
    )
    write_json(
        handoff / "recipes/json/target_mix_recipe.json",
        {
            "recipe_name": "unit_recipe",
            "recipe_type": "genre_based_draft",
            "target": {"genres": ["hyperpop"]},
            "evidence": {"reference_audio_available": False, "audio_analysis_available": False},
            "global": {"sample_rate": 48000, "bit_depth": 24, "mastering_mode": "pre_master"},
            "track_roles": {
                "reference": {
                    "bus": "PREMASTER" if bad_reference_bus else "MASTER_ONLY",
                    "master_send": True,
                    "fx_chain": [],
                    "sends": [],
                },
                "lead_vocal": {
                    "bus": "VOX BUS",
                    "master_send": False,
                    "fx_chain": [
                        {
                            "plugin": "ReaEQ",
                            "params": {"parameter_policy": "Use helper APIs only."},
                        }
                    ],
                    "sends": [{"target": "VOCAL REVERB", "send_db": -20}],
                },
                "premaster": {
                    "bus": "PREMASTER",
                    "master_send": False,
                    "fx_chain": [
                        {
                            "plugin": "ReaLimit",
                            "params": {"parameter_policy": "Name discovery only."},
                        }
                    ],
                    "sends": [],
                },
            },
        },
    )
    write_json(
        handoff / "qc/revision_actions.json",
        {
            "qc_status": "needs_render",
            "confidence": "low",
            "render_file": "",
            "measured": {},
            "issues": [],
        },
    )
    return handoff


def write_ready_gates(output: Path) -> None:
    write_json(
        output / "eval_reports/plugin_semantic_validation_gate.json",
        {"semantic_validation_ready": True, "blockers": [], "warnings": []},
    )
    write_json(
        output / "eval_reports/source_acceptance_gate.json",
        {"accepted_export_source_ready": True, "blockers": [], "warnings": []},
    )
    write_json(
        output / "eval_reports/final_render_evidence_gate.json",
        {"ready_for_final_qc": True, "blockers": [], "warnings": []},
    )
    write_json(
        output / "eval_reports/final_qc_evidence_gate.json",
        {"ready_for_approval_readiness": True, "blockers": [], "warnings": []},
    )
    write_json(
        output / "eval_reports/ab_preview_evidence_gate.json",
        {"ready_for_human_ab_review": True, "blockers": [], "warnings": []},
    )


def test_handoff_recipe_builds_planning_ready_harness_without_render(tmp_path: Path) -> None:
    handoff = make_handoff(tmp_path)
    output = tmp_path / "automix"
    audit = build_mix_master_quality_harness(project_name="unit", output_dir=output, handoff_root=handoff)

    assert audit["passed"] is True
    assert audit["readiness"]["ready_for_high_quality_offline_planning"] is True
    assert audit["readiness"]["ready_for_reaper_dry_run"] is True
    assert audit["readiness"]["ready_for_applied_mix_or_master_parameter_writes"] is False
    assert audit["readiness"]["render_was_created"] is False
    assert "plugin_semantic_validation_not_ready_for_parameter_writes" in audit["blockers"]
    assert (output / "eval_reports/mix_master_quality_harness.md").exists()
    assert (output / "chain_plans/high_quality_mix_master_readiness_plan.json").exists()
    plan = read_json(output / "chain_plans/high_quality_mix_master_readiness_plan.json")
    assert plan["draft_only"] is True
    assert plan["safe_to_apply"] is False
    assert plan["original_tracks_must_remain_untouched"] is True
    assert "does_not_approve_delivery_or_reference_match_claims" in plan["claim_limits"]


def test_ready_gates_allow_applied_processing_but_not_render_creation(tmp_path: Path) -> None:
    handoff = make_handoff(tmp_path)
    output = tmp_path / "automix"
    write_ready_gates(output)
    audit = build_mix_master_quality_harness(project_name="unit", output_dir=output, handoff_root=handoff)

    assert audit["readiness"]["ready_for_applied_mix_or_master_parameter_writes"] is True
    assert audit["readiness"]["ready_for_delivery_claims"] is True
    assert audit["readiness"]["render_was_created"] is False


def test_bad_reference_routing_blocks_handoff_quality_harness(tmp_path: Path) -> None:
    handoff = make_handoff(tmp_path, bad_reference_bus=True)
    audit = build_mix_master_quality_harness(project_name="unit", output_dir=tmp_path / "automix", handoff_root=handoff)

    assert audit["passed"] is False
    assert "reference_role_not_master_only" in audit["blockers"]


def test_mix_master_quality_harness_cli_writes_reports(tmp_path: Path) -> None:
    handoff = make_handoff(tmp_path)
    output = tmp_path / "automix"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_mix_master_quality_harness.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(output),
            "--handoff-root",
            str(handoff),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)

    assert result.returncode == 0
    assert data["status"] == "planning_ready"
    assert Path(data["report_json"]).exists()
    assert Path(data["report_md"]).exists()
    assert Path(data["plan_json"]).exists()
