from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


SCHEMA = "automix-mix-master-quality-harness-v1"
JSON_REL_PATH = Path("eval_reports/mix_master_quality_harness.json")
MD_REL_PATH = Path("eval_reports/mix_master_quality_harness.md")
PLAN_REL_PATH = Path("chain_plans/high_quality_mix_master_readiness_plan.json")

REQUIRED_HANDOFF_FILES = [
    "START_HERE.md",
    "AGENTS.md",
    "PROJECT_SNAPSHOT.json",
    "NEXT_PROMPT.md",
    "core/SOURCE_OF_TRUTH.md",
    "recipes/json/target_mix_recipe.json",
    "recipes/lua/target_mix_recipe.lua",
    "scripts/import_and_mix_stems.lua",
    "scripts/apply_mix_recipe.lua",
    "scripts/apply_revision_actions.lua",
    "scripts/render_setup.lua",
    "tools/analyze_audio.py",
    "tools/compare_audio.py",
    "tools/validate_recipe.py",
    "qc/revision_actions.json",
]

REQUIRED_REAPER_SCRIPTS = [
    "scripts/track_classifier.lua",
    "scripts/routing_builder.lua",
    "scripts/fx_chain_builder.lua",
    "scripts/plugin_registry.lua",
    "scripts/import_and_mix_stems.lua",
    "scripts/apply_revision_actions.lua",
    "scripts/render_setup.lua",
]

GATE_PATHS = {
    "plugin_semantic_validation": Path("eval_reports/plugin_semantic_validation_gate.json"),
    "source_acceptance": Path("eval_reports/source_acceptance_gate.json"),
    "final_render_evidence": Path("eval_reports/final_render_evidence_gate.json"),
    "final_qc_evidence": Path("eval_reports/final_qc_evidence_gate.json"),
    "ab_preview_evidence": Path("eval_reports/ab_preview_evidence_gate.json"),
}


def _load_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, f"missing:{path}"
    except json.JSONDecodeError as exc:
        return {}, f"json_decode_error:{path}:{exc}"
    if not isinstance(data, dict):
        return {}, f"json_type_error:{path}:expected_object"
    return data, None


def _bool_gate(data: dict[str, Any], *keys: str) -> bool:
    return any(bool(data.get(key)) for key in keys)


def _role_has_fx(role: dict[str, Any]) -> bool:
    return bool(role.get("fx_chain")) if isinstance(role, dict) else False


def _has_parameter_policy(role: dict[str, Any]) -> bool:
    for fx in role.get("fx_chain", []) if isinstance(role.get("fx_chain"), list) else []:
        params = fx.get("params", {}) if isinstance(fx, dict) else {}
        if isinstance(params, dict) and "parameter_policy" in params:
            return True
    return False


def build_handoff_summary(handoff_root: Path) -> dict[str, Any]:
    handoff_root = Path(handoff_root)
    files = sorted(path.relative_to(handoff_root).as_posix() for path in handoff_root.rglob("*") if path.is_file()) if handoff_root.exists() else []
    missing = [rel for rel in REQUIRED_HANDOFF_FILES if not (handoff_root / rel).exists()]
    missing_scripts = [rel for rel in REQUIRED_REAPER_SCRIPTS if not (handoff_root / rel).exists()]
    manifest, manifest_error = _load_json(handoff_root / "PACKAGE_MANIFEST.json")
    snapshot, snapshot_error = _load_json(handoff_root / "PROJECT_SNAPSHOT.json")
    recipe, recipe_error = _load_json(handoff_root / "recipes/json/target_mix_recipe.json")
    qc_actions, qc_error = _load_json(handoff_root / "qc/revision_actions.json")
    audio_in_package = [rel for rel in files if Path(rel).suffix.lower() in {".wav", ".mp3", ".flac", ".aif", ".aiff", ".m4a", ".ogg"}]
    return {
        "handoff_root": str(handoff_root),
        "exists": handoff_root.exists(),
        "file_count": len(files),
        "required_files_missing": missing,
        "required_reaper_scripts_missing": missing_scripts,
        "package_name": manifest.get("package_name"),
        "manifest_error": manifest_error,
        "snapshot_error": snapshot_error,
        "recipe_error": recipe_error,
        "qc_actions_error": qc_error,
        "snapshot_known_risks": snapshot.get("known_risks", []),
        "snapshot_next_actions": snapshot.get("next_actions", []),
        "audio_files_in_package": audio_in_package,
        "audio_files_included": bool(audio_in_package),
        "recipe": recipe,
        "qc_actions": qc_actions,
        "valid": handoff_root.exists() and not missing and recipe_error is None and qc_error is None,
    }


def analyze_recipe_quality(recipe: dict[str, Any]) -> dict[str, Any]:
    evidence = recipe.get("evidence", {}) if isinstance(recipe.get("evidence"), dict) else {}
    global_cfg = recipe.get("global", {}) if isinstance(recipe.get("global"), dict) else {}
    roles = recipe.get("track_roles", {}) if isinstance(recipe.get("track_roles"), dict) else {}
    reference = roles.get("reference", {}) if isinstance(roles.get("reference"), dict) else {}
    role_names = sorted(roles)
    roles_with_fx = sorted(name for name, role in roles.items() if isinstance(role, dict) and _role_has_fx(role))
    roles_with_parameter_policy = sorted(name for name, role in roles.items() if isinstance(role, dict) and _has_parameter_policy(role))
    buses = sorted({str(role.get("bus")) for role in roles.values() if isinstance(role, dict) and role.get("bus")})
    sends = sum(len(role.get("sends", [])) for role in roles.values() if isinstance(role, dict) and isinstance(role.get("sends"), list))

    blockers: list[str] = []
    warnings: list[str] = []
    if evidence.get("reference_audio_available") is False and recipe.get("recipe_type") != "genre_based_draft":
        blockers.append("recipe_type_must_remain_genre_based_without_reference_audio")
    if reference and reference.get("bus") != "MASTER_ONLY":
        blockers.append("reference_role_not_master_only")
    if reference and reference.get("master_send") is not True:
        warnings.append("reference_role_master_send_not_explicit_true_for_muted_reference_monitoring")
    if global_cfg.get("mastering_mode") != "pre_master":
        blockers.append("recipe_mastering_mode_not_pre_master")
    if "lead_vocal" not in roles:
        blockers.append("lead_vocal_role_missing")
    if "PREMASTER" not in buses and "PREMASTER BUS" not in buses:
        warnings.append("premaster_bus_not_declared_in_role_buses")
    if len(roles_with_parameter_policy) < max(1, len(roles_with_fx) // 2):
        warnings.append("many_fx_roles_lack_parameter_policy")

    return {
        "recipe_name": recipe.get("recipe_name"),
        "recipe_type": recipe.get("recipe_type"),
        "reference_audio_available": evidence.get("reference_audio_available"),
        "audio_analysis_available": evidence.get("audio_analysis_available"),
        "mastering_mode": global_cfg.get("mastering_mode"),
        "sample_rate": global_cfg.get("sample_rate"),
        "bit_depth": global_cfg.get("bit_depth"),
        "role_count": len(roles),
        "roles": role_names,
        "roles_with_fx": roles_with_fx,
        "roles_with_parameter_policy": roles_with_parameter_policy,
        "buses": buses,
        "send_count": sends,
        "reference_master_only": bool(reference and reference.get("bus") == "MASTER_ONLY"),
        "has_lead_vocal_chain": "lead_vocal" in roles_with_fx,
        "has_premaster_intent": global_cfg.get("mastering_mode") == "pre_master",
        "blockers": blockers,
        "warnings": warnings,
        "usable_for_high_quality_planning": not blockers and "lead_vocal" in roles and bool(roles_with_fx),
    }


def collect_current_gate_status(output_dir: Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    gates: dict[str, Any] = {}
    blockers: list[str] = []
    warnings: list[str] = []
    for name, rel in GATE_PATHS.items():
        path = output_dir / rel
        data, error = _load_json(path)
        if error:
            gates[name] = {"path": str(path), "found": False, "error": error}
            warnings.append(f"{name}_gate_missing_or_unreadable")
            continue
        gates[name] = {
            "path": str(path),
            "found": True,
            "blockers": data.get("blockers", []),
            "warnings": data.get("warnings", []),
            "ready": _bool_gate(
                data,
                "semantic_validation_ready",
                "accepted_export_source_ready",
                "ready_for_final_qc",
                "ready_for_approval_readiness",
                "ready_for_human_ab_review",
                "ready_for_final_approval_request",
            ),
            "passed": bool(data.get("passed")) if "passed" in data else None,
        }
    plugin = gates.get("plugin_semantic_validation", {})
    source = gates.get("source_acceptance", {})
    render = gates.get("final_render_evidence", {})
    qc = gates.get("final_qc_evidence", {})
    ab = gates.get("ab_preview_evidence", {})
    if not plugin.get("ready"):
        blockers.append("plugin_semantic_validation_not_ready_for_parameter_writes")
    if not source.get("ready"):
        blockers.append("accepted_source_or_stem_evidence_missing")
    if not render.get("ready"):
        blockers.append("final_render_evidence_missing_for_delivery_claims")
    if not qc.get("ready"):
        blockers.append("final_qc_evidence_missing_for_delivery_claims")
    if not ab.get("ready"):
        blockers.append("ab_preview_evidence_missing_for_human_review")
    return {
        "gates": gates,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "parameter_write_ready": bool(plugin.get("ready")),
        "source_ready": bool(source.get("ready")),
        "render_qc_ready": bool(render.get("ready") and qc.get("ready") and ab.get("ready")),
    }


def build_action_plan(handoff: dict[str, Any], recipe: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = [
        {
            "step": "restore_validate_handoff",
            "status": "passed" if handoff.get("valid") else "blocked",
            "mode": "offline",
            "reason": "ZIP handoff source-of-truth files, recipes, scripts, and tools must be complete before integration.",
        },
        {
            "step": "recipe_script_consistency_pass",
            "status": "ready" if recipe.get("usable_for_high_quality_planning") else "blocked",
            "mode": "offline",
            "reason": "Use target_mix_recipe plus Lua recipe/scripts as the dry-run mix/master contract.",
        },
        {
            "step": "dry_run_stem_classification_and_routing",
            "status": "ready" if handoff.get("valid") else "blocked",
            "mode": "reaper_dry_run_only",
            "reason": "Classify stems, build role buses, and verify reference/full-mix tracks stay out of PREMASTER/PRINT MASTER.",
        },
        {
            "step": "semantic_plugin_validation",
            "status": "ready" if current.get("parameter_write_ready") else "blocked",
            "mode": "reaper_observed_validation",
            "reason": "High-quality automation must not write FX parameters until controls are semantically validated.",
        },
        {
            "step": "source_acceptance",
            "status": "ready" if current.get("source_ready") else "blocked",
            "mode": "operator_evidence",
            "reason": "Accepted stems/source exports are required before applied mix or premaster claims.",
        },
        {
            "step": "high_quality_mix_plan",
            "status": "planning_ready" if recipe.get("usable_for_high_quality_planning") else "blocked",
            "mode": "offline_plan",
            "reason": "Build vocal-first balance, role-bus routing, conservative FX, send returns, and premaster headroom plan.",
        },
        {
            "step": "premaster_safety_plan",
            "status": "planning_ready",
            "mode": "offline_plan",
            "reason": "Premaster remains draft-only until measured render, A/B, rollback, and final QC evidence exist.",
        },
        {
            "step": "render_qc_ab_delivery_gates",
            "status": "ready" if current.get("render_qc_ready") else "blocked",
            "mode": "post_render_evidence",
            "reason": "Delivery or high-confidence quality claims require final render evidence, QC metrics, and loudness-matched A/B.",
        },
    ]
    return actions


def build_mix_master_quality_harness(
    *,
    project_name: str,
    output_dir: Path,
    handoff_root: Path,
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
    handoff = build_handoff_summary(handoff_root)
    recipe_summary = analyze_recipe_quality(handoff.get("recipe", {}))
    current = collect_current_gate_status(output_dir)
    blockers = sorted(set(handoff.get("required_files_missing", []) + recipe_summary.get("blockers", []) + current.get("blockers", [])))
    warnings = sorted(
        set(
            handoff.get("snapshot_known_risks", [])
            + recipe_summary.get("warnings", [])
            + current.get("warnings", [])
            + [
                "render_execution_intentionally_skipped",
                "no_reference_match_claim_without_lawful_reference_audio_analysis",
            ]
        )
    )
    action_plan = build_action_plan(handoff, recipe_summary, current)
    planning_ready = bool(handoff.get("valid") and recipe_summary.get("usable_for_high_quality_planning"))
    applied_ready = bool(planning_ready and current.get("parameter_write_ready") and current.get("source_ready"))
    payload = {
        "schema": SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "workspace_root": str(workspace_root),
        "handoff": {key: value for key, value in handoff.items() if key not in {"recipe", "qc_actions"}},
        "recipe_quality": recipe_summary,
        "current_gate_status": current,
        "readiness": {
            "ready_for_high_quality_offline_planning": planning_ready,
            "ready_for_reaper_dry_run": bool(handoff.get("valid")),
            "ready_for_applied_mix_or_master_parameter_writes": applied_ready,
            "ready_for_delivery_claims": bool(applied_ready and current.get("render_qc_ready")),
            "render_was_created": False,
        },
        "action_plan": action_plan,
        "blockers": blockers,
        "warnings": warnings,
        "passed": planning_ready,
    }
    write_json(output_dir / JSON_REL_PATH, payload)
    write_json(
        output_dir / PLAN_REL_PATH,
        {
            "schema": "automix-high-quality-mix-master-readiness-plan-v1",
            "project_name": project_name,
            "draft_only": True,
            "safe_to_apply": False,
            "original_tracks_must_remain_untouched": True,
            "original_master_must_remain_untouched": True,
            "contains_reference_audio_content": False,
            "contains_master_limiter_on_original": False,
            "contains_master_widening": False,
            "modifies_original_master": False,
            "modifies_original_tracks": False,
            "no_fixed_parameter_indexes": True,
            "plugin_chain": [],
            "claim_limits": [
                "offline_readiness_plan_only",
                "does_not_apply_fx_or_render_audio",
                "does_not_approve_delivery_or_reference_match_claims",
            ],
            "actions": action_plan,
        },
    )
    write_mix_master_quality_report(payload, output_dir)
    return payload


def write_mix_master_quality_report(payload: dict[str, Any], output_dir: Path) -> Path:
    readiness = payload.get("readiness", {})
    recipe = payload.get("recipe_quality", {})
    lines = [
        "# Mix/Master Quality Harness",
        "",
        f"- Project: `{payload.get('project_name')}`",
        f"- Created UTC: `{payload.get('created_at')}`",
        f"- Handoff valid: `{payload.get('handoff', {}).get('valid')}`",
        f"- Offline high-quality planning ready: `{readiness.get('ready_for_high_quality_offline_planning')}`",
        f"- REAPER dry-run ready: `{readiness.get('ready_for_reaper_dry_run')}`",
        f"- Applied parameter writes ready: `{readiness.get('ready_for_applied_mix_or_master_parameter_writes')}`",
        f"- Delivery claims ready: `{readiness.get('ready_for_delivery_claims')}`",
        f"- Render created by this harness: `{readiness.get('render_was_created')}`",
        "",
        "## Handoff Recipe",
        "",
        f"- Recipe: `{recipe.get('recipe_name')}`",
        f"- Type: `{recipe.get('recipe_type')}`",
        f"- Mastering mode: `{recipe.get('mastering_mode')}`",
        f"- Roles: `{recipe.get('role_count')}`",
        f"- Roles with FX: `{len(recipe.get('roles_with_fx', []))}`",
        f"- Reference master-only: `{recipe.get('reference_master_only')}`",
        "",
        "## Action Plan",
        "",
    ]
    for item in payload.get("action_plan", []):
        lines.append(f"- `{item.get('status')}` `{item.get('step')}`: {item.get('reason')}")
    lines.extend(["", "## Blockers", ""])
    lines.extend([f"- `{item}`" for item in payload.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in payload.get("warnings", [])] or ["- none"])
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- This harness prepares and audits the high-quality mix/master path only.",
            "- It does not render audio, approve delivery, or claim reference matching.",
            "- Applied processing remains blocked until source acceptance and semantic plugin validation are ready.",
        ]
    )
    path = Path(output_dir) / MD_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
