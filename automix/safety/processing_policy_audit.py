from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, safe_float, write_json


PROCESSING_POLICY_AUDIT_SCHEMA = "automix-processing-policy-audit-v1"

AUDIT_REL_PATH = Path("eval_reports/processing_policy_audit.json")
AUDIT_REPORT_REL_PATH = Path("eval_reports/processing_policy_audit.md")

CHAIN_PLAN_PATTERNS = [
    "chain_plans/*.json",
]

SATURATION_SEMANTICS = {"saturation_amount", "drive", "harmonic_amount", "clipper_drive_db"}
LIMITER_SEMANTICS = {"limiter_max_gain_db", "target_lufs", "clipper_drive_db"}
WIDTH_SEMANTICS = {"stereo_width_change", "side_gain_db", "ms_side_gain_db"}
DRY_WET_SEMANTICS = {"dry_wet", "mix", "amount", "depth"}

DANGEROUS_PLUGIN_TERMS = {
    "ott": "ott_style_processing_blocked_by_default",
    "decapitator": "aggressive_saturation_plugin_blocked_by_default",
    "ozone": "ozone_style_mastering_requires_draft_premaster_only",
    "maximizer": "maximizer_requires_final_qc_and_draft_only",
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _settings_from_item(item: dict[str, Any]) -> dict[str, Any]:
    settings: dict[str, Any] = {}
    for key in ("semantic_settings", "semantic_controls", "settings"):
        value = item.get(key)
        if isinstance(value, dict):
            settings.update(value)
    return settings


def _all_settings(plan: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    top_settings = _settings_from_item(plan)
    if top_settings:
        out.append(("plan", top_settings))
    for index, item in enumerate(plan.get("plugin_chain", []) or []):
        if isinstance(item, dict):
            out.append((f"plugin_chain[{index}]", _settings_from_item(item)))
    for index, fx in enumerate(plan.get("fx_to_insert", []) or []):
        if isinstance(fx, dict):
            settings = {}
            for write in fx.get("parameter_writes", []) or []:
                if isinstance(write, dict) and write.get("semantic"):
                    settings[str(write.get("semantic"))] = write.get("normalized_value", write.get("clamped_value", write.get("value")))
            if settings:
                out.append((f"fx_to_insert[{index}]", settings))
    return out


def _intent_dry_wet_cap(output_dir: Path) -> float:
    intent = _load_json(output_dir / "eval_reports/intent_classification.json")
    caps = [
        safe_float(item.get("max_artifact_focus_dry_wet"), 1.0)
        for item in intent.get("intents", [])
        if item.get("conservative_mode") and item.get("artifact_focus_score", 0) >= 0.25
    ]
    return min(caps) if caps else 0.45


def _plugin_identity(item: dict[str, Any]) -> str:
    return " ".join(str(item.get(key, "")) for key in ("plugin", "plugin_name", "name", "category", "target_role")).lower()


def _flag(blockers: list[str], code: str, context: str) -> None:
    blockers.append(f"{code}:{context}")


def _warn(warnings: list[str], code: str, context: str) -> None:
    warnings.append(f"{code}:{context}")


def _audit_plan(path: Path, plan: dict[str, Any], *, dry_wet_cap: float) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    schema = str(plan.get("schema", ""))
    is_applicator = "applicator-plan" in schema or "applicator_plan" in path.name
    is_proposals = "dry-run-chain-proposals" in schema or "proposals" in plan

    if not plan:
        _flag(blockers, "chain_plan_unreadable_or_invalid_json", path.name)
    if is_proposals:
        for index, proposal in enumerate(plan.get("proposals", []) or []):
            if proposal.get("would_modify_project"):
                _flag(blockers, "dry_run_proposal_would_modify_project", f"{path.name}:proposal[{index}]")
        if not plan.get("warnings"):
            _warn(warnings, "dry_run_proposals_have_no_policy_warning", path.name)
    elif is_applicator:
        if plan.get("apply_allowed") and not plan.get("master_modification_blocked", False):
            _flag(blockers, "applicator_allows_master_modification", path.name)
        if plan.get("apply_allowed") and not plan.get("pitch_correction_blocked", False):
            _flag(blockers, "applicator_allows_pitch_correction", path.name)
        if not plan.get("no_fixed_parameter_indexes", False):
            _flag(blockers, "applicator_may_use_fixed_parameter_indexes", path.name)
        if not plan.get("parameter_writes_require_name_match", False):
            _flag(blockers, "applicator_parameter_name_match_not_required", path.name)
    else:
        if not plan.get("draft_only", False):
            _flag(blockers, "chain_plan_not_draft_only", path.name)
        if plan.get("safe_to_apply") and not (plan.get("original_tracks_must_remain_untouched") or plan.get("original_master_must_remain_untouched")):
            _flag(blockers, "safe_plan_missing_original_protection_flag", path.name)

    if plan.get("contains_reference_audio_content"):
        _flag(blockers, "chain_plan_contains_reference_audio_content", path.name)
    if plan.get("contains_master_limiter_on_original") or plan.get("contains_master_limiter_on_original_master"):
        _flag(blockers, "master_limiter_on_original_master_blocked", path.name)
    if plan.get("contains_master_widening"):
        _flag(blockers, "blind_master_widening_blocked", path.name)
    if plan.get("modifies_original_master") or plan.get("modifies_original_tracks"):
        _flag(blockers, "original_mutation_blocked", path.name)
    if plan.get("no_fixed_parameter_indexes") is False:
        _flag(blockers, "fixed_parameter_indexes_blocked", path.name)

    for index, item in enumerate(plan.get("plugin_chain", []) or []):
        if not isinstance(item, dict):
            continue
        context = f"{path.name}:plugin_chain[{index}]"
        identity = _plugin_identity(item)
        for term, code in DANGEROUS_PLUGIN_TERMS.items():
            if term in identity:
                _flag(blockers, code, context)
        if "saturation" in identity and "aggressive" in identity:
            _flag(blockers, "aggressive_saturation_blocked", context)
        if "widen" in identity or "stereo width" in identity:
            _flag(blockers, "blind_stereo_widening_blocked", context)
        if item.get("safe_to_apply") and item.get("requires_parameter_discovery"):
            _flag(blockers, "safe_to_apply_requires_parameter_discovery", context)
        if item.get("safe_to_apply") and safe_float(item.get("adapter_confidence"), 1.0) < 0.85:
            _flag(blockers, "safe_to_apply_adapter_confidence_low", context)
        if item.get("no_fixed_parameter_indexes") is False:
            _flag(blockers, "fixed_parameter_indexes_blocked", context)

    for context, settings in _all_settings(plan):
        for semantic, raw_value in settings.items():
            name = str(semantic)
            value = safe_float(raw_value, 0.0)
            if name in DRY_WET_SEMANTICS and value > dry_wet_cap:
                _flag(blockers, "dry_wet_exceeds_conservative_cap", f"{path.name}:{context}:{name}={value}")
            if name in SATURATION_SEMANTICS:
                if name == "clipper_drive_db" and value > 2.0:
                    _flag(blockers, "clipper_drive_too_high", f"{path.name}:{context}:{name}={value}")
                elif name != "clipper_drive_db" and value > 0.30:
                    _flag(blockers, "saturation_amount_too_high", f"{path.name}:{context}:{name}={value}")
            if name in LIMITER_SEMANTICS:
                if name == "limiter_max_gain_db" and value > 2.0:
                    _flag(blockers, "limiter_gain_too_high_for_policy", f"{path.name}:{context}:{name}={value}")
                if name == "target_lufs" and value > -7.0:
                    _flag(blockers, "target_lufs_too_hot_for_default_policy", f"{path.name}:{context}:{name}={value}")
            if name in WIDTH_SEMANTICS and value > 0.15:
                _flag(blockers, "stereo_width_change_too_high", f"{path.name}:{context}:{name}={value}")

    if plan.get("safe_to_apply") and blockers:
        _flag(blockers, "safe_to_apply_conflicts_with_policy_blockers", path.name)
    if not blockers and not warnings:
        _warn(warnings, "chain_plan_policy_clean", path.name)

    return {
        "path": str(path),
        "relative_path": str(path),
        "schema": schema,
        "draft_only": bool(plan.get("draft_only", False)),
        "safe_to_apply": bool(plan.get("safe_to_apply") or plan.get("apply_allowed")),
        "plugin_chain_count": len(plan.get("plugin_chain", []) or []),
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "passed": not blockers,
    }


def build_processing_policy_audit(
    *,
    project_name: str,
    output_dir: Path,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    dry_wet_cap = _intent_dry_wet_cap(output_dir)
    paths: list[Path] = []
    for pattern in CHAIN_PLAN_PATTERNS:
        paths.extend(path for path in output_dir.glob(pattern) if path.is_file())
    plan_results = [_audit_plan(path, _load_json(path), dry_wet_cap=dry_wet_cap) for path in sorted(set(paths))]
    blockers = sorted({blocker for result in plan_results for blocker in result.get("blockers", [])})
    warnings = sorted({warning for result in plan_results for warning in result.get("warnings", [])})
    if not plan_results:
        warnings.append("no_chain_plans_found")
    audit = {
        "schema": PROCESSING_POLICY_AUDIT_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "dry_wet_cap": dry_wet_cap,
        "plans_checked": len(plan_results),
        "plan_results": plan_results,
        "blockers": blockers,
        "warnings": warnings,
        "passed": not blockers,
        "safe_to_apply": bool(plan_results) and not blockers,
    }
    target = output_path or output_dir / AUDIT_REL_PATH
    write_json(target, audit)
    write_processing_policy_report(audit, output_dir)
    return audit


def write_processing_policy_report(audit: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Processing Policy Audit",
        "",
        f"- Project: `{audit.get('project_name')}`",
        f"- Created UTC: `{audit.get('created_at')}`",
        f"- Passed: `{audit.get('passed')}`",
        f"- Plans checked: `{audit.get('plans_checked')}`",
        f"- Conservative dry/wet cap: `{audit.get('dry_wet_cap')}`",
        "",
        "This report audits chain plans before automated processing. It does not apply FX or prove audio quality.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in audit.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in audit.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Plans", ""])
    if not audit.get("plan_results"):
        lines.append("- none")
    for result in audit.get("plan_results", []):
        lines.extend(
            [
                f"### {Path(result.get('path', '')).name}",
                "",
                f"- Passed: `{result.get('passed')}`",
                f"- Draft only: `{result.get('draft_only')}`",
                f"- Safe to apply: `{result.get('safe_to_apply')}`",
                f"- Plugin chain count: `{result.get('plugin_chain_count')}`",
                f"- Blockers: `{', '.join(result.get('blockers', [])) or 'none'}`",
                f"- Warnings: `{', '.join(result.get('warnings', [])) or 'none'}`",
                "",
            ]
        )
    path = Path(output_dir) / AUDIT_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
