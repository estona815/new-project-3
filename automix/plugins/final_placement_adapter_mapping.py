from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.adapter_confidence_gate import evaluate_adapter_confidence
from automix.plugins.plugin_adapter_schema import adapter_matches_plugin, clamp_semantic_value, now_utc, safe_float, slugify, write_json
from automix.plugins.plugin_inventory_audit import load_adapters, load_inventory, audit_plugin_inventory


REPORT_SCHEMA = "automix-final-placement-adapter-mapping-v1"
APPLICATOR_PLAN_SCHEMA = "automix-final-vocal-space-applicator-plan-v1"

SEMANTIC_ALIASES = {
    "instrumental_duck_db": "instrumental_duck_amount_db",
    "presence_duck_db": "presence_duck_amount_db",
    "low_mid_duck_db": "low_mid_duck_amount_db",
    "backing_vocal_duck_db": "backing_duck_amount_db",
    "send_duck_db": "send_duck_amount_db",
    "melody_duck_db": "presence_duck_amount_db",
    "ms_mid_cleanup": "ms_mid_cleanup_amount",
    "ms_side_cleanup": "ms_side_cleanup_amount",
    "vocal_harshness_guard": "harshness_guard_amount",
    "vocal_sibilance_guard": "sibilance_control_amount",
}

CATEGORY_REQUIRED_CONTROLS = {
    "utility_gain": ["vocal_gain_db"],
    "output_gain": ["vocal_gain_db"],
    "sidechain_dynamic_eq": [
        "instrumental_duck_amount_db",
        "presence_duck_amount_db",
        "low_mid_duck_amount_db",
        "sibilance_conflict_duck_db",
        "duck_attack_ms",
        "duck_release_ms",
    ],
    "multiband_ducker": ["instrumental_duck_amount_db", "duck_attack_ms", "duck_release_ms"],
    "ms_cleanup": ["ms_mid_cleanup_amount", "ms_side_cleanup_amount"],
    "sidechain_ducker": ["backing_duck_amount_db", "duck_attack_ms", "duck_release_ms"],
    "send_return_ducker": ["send_duck_amount_db", "duck_attack_ms", "duck_release_ms"],
    "narrow_melody_duck": ["presence_duck_amount_db", "duck_attack_ms", "duck_release_ms"],
    "harshness_guard": ["harshness_guard_amount", "sibilance_control_amount"],
}

DISALLOWED_PLUGIN_TERMS = (
    "mautopitch",
    "autotune",
    "auto-tune",
    "melodyne",
    "reapitch",
    "reatune",
    "graillon",
    "ott",
    "ozone",
    "decapitator",
    "saturn",
    "valhalla",
)


def _read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def _detected_plugin_names(plugin_audit: dict[str, Any], inventory: dict[str, Any]) -> list[str]:
    names = [str(item.get("name")) for item in plugin_audit.get("plugins_detected", []) if item.get("name")]
    for key in ("detected_plugins", "insertable_plugins", "installed_plugins", "plugins_detected"):
        for item in inventory.get(key, []) or []:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict):
                name = item.get("name") or item.get("display_name") or item.get("plugin") or item.get("detected_name")
                if name:
                    names.append(str(name))
    return sorted(set(names))


def _canonical_settings(semantic_settings: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for semantic, value in (semantic_settings or {}).items():
        out[SEMANTIC_ALIASES.get(semantic, semantic)] = value
    return out


def _category_items(chain_plan: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for item in chain_plan.get("plugin_chain", []) or []:
        settings = _canonical_settings(item.get("semantic_settings", {}))
        category = item.get("category", "unknown")
        required = [control for control in CATEGORY_REQUIRED_CONTROLS.get(category, list(settings)) if control in settings or category in CATEGORY_REQUIRED_CONTROLS]
        if not required:
            required = list(settings)
        items.append(
            {
                "target_role": item.get("target_role", ""),
                "category": category,
                "source_plugin_label": item.get("plugin", ""),
                "semantic_settings": settings,
                "required_controls": required,
            }
        )
    return items


def _plugin_available_for_adapter(adapter: dict[str, Any], detected_plugin_names: list[str], *, allow_offline_validated_adapters: bool) -> tuple[bool, str]:
    for plugin_name in detected_plugin_names:
        if adapter_matches_plugin(adapter, plugin_name):
            return True, plugin_name
    if allow_offline_validated_adapters and adapter.get("safe_for_automix") and adapter.get("validation", {}).get("status") == "passed":
        names = adapter.get("plugin_name_patterns") or [adapter.get("adapter_id", "validated_adapter")]
        return True, str(names[0])
    return False, ""


def _has_disallowed_plugin_name(plugin_name: str) -> bool:
    lower = plugin_name.lower()
    return any(term in lower for term in DISALLOWED_PLUGIN_TERMS)


def _adapter_gate_for_category(
    *,
    category_item: dict[str, Any],
    adapter: dict[str, Any],
    plugin_name: str,
    min_confidence: float,
) -> dict[str, Any]:
    settings = category_item.get("semantic_settings", {})
    required = category_item.get("required_controls", list(settings))
    desired = {semantic: settings.get(semantic, 0.0) for semantic in required}
    gate = evaluate_adapter_confidence(
        desired_semantic_controls=desired,
        adapter=adapter,
        plugin_name=plugin_name,
        plugin_detected=bool(plugin_name),
        required_confidence=min_confidence,
        workflow_stage="vocal_placement",
        source_risk="normal",
        required_controls=required,
        fallback="skip category until semantic adapter is validated",
    )
    if _has_disallowed_plugin_name(plugin_name):
        gate["allowed"] = False
        gate.setdefault("reason_codes", []).append("DISALLOWED_PLUGIN_FOR_FINISHING_STAGE")
        gate["reason_codes"] = sorted(set(gate["reason_codes"]))
        gate["fallback_required"] = True
    return gate


def _best_adapter(
    category_item: dict[str, Any],
    adapters: list[dict[str, Any]],
    detected_plugin_names: list[str],
    *,
    min_confidence: float,
    allow_offline_validated_adapters: bool,
) -> dict[str, Any]:
    candidates = []
    for adapter in adapters:
        available, plugin_name = _plugin_available_for_adapter(adapter, detected_plugin_names, allow_offline_validated_adapters=allow_offline_validated_adapters)
        if not available:
            continue
        gate = _adapter_gate_for_category(category_item=category_item, adapter=adapter, plugin_name=plugin_name, min_confidence=min_confidence)
        candidates.append(
            {
                "adapter_id": adapter.get("adapter_id"),
                "plugin_name": plugin_name,
                "adapter_confidence": safe_float(adapter.get("confidence"), 0.0),
                "gate": gate,
                "adapter": adapter,
            }
        )
    candidates.sort(
        key=lambda item: (
            bool(item["gate"].get("allowed")),
            len(item["gate"].get("controls_allowed", {})),
            item["adapter_confidence"],
        ),
        reverse=True,
    )
    if candidates:
        return candidates[0]
    return {
        "adapter_id": None,
        "plugin_name": "",
        "adapter_confidence": 0.0,
        "gate": {
            "allowed": False,
            "controls_allowed": {},
            "controls_skipped": {semantic: {"reason": "NO_AVAILABLE_VALIDATED_ADAPTER"} for semantic in category_item.get("required_controls", [])},
            "required_missing": category_item.get("required_controls", []),
            "reason_codes": ["NO_AVAILABLE_VALIDATED_ADAPTER", "FALLBACK_REQUIRED"],
            "fallback_required": True,
            "fallback": "skip category until adapter is validated",
            "warnings": [],
            "required_confidence": min_confidence,
        },
        "adapter": {},
    }


def _parameter_write_entry(adapter: dict[str, Any], semantic: str, value: Any) -> dict[str, Any] | None:
    control = (adapter.get("semantic_controls") or {}).get(semantic)
    if not isinstance(control, dict):
        return None
    if control.get("normalization") != "normalized_0_1":
        return None
    clamped = clamp_semantic_value(adapter, semantic, value)
    if not clamped.get("allowed"):
        return None
    normalized_value = safe_float(clamped.get("clamped_value"), 0.0)
    if normalized_value < 0.0 or normalized_value > 1.0:
        return None
    target_name = control.get("target_name")
    if not target_name:
        return None
    return {
        "semantic": semantic,
        "target_name": target_name,
        "normalized_value": normalized_value,
        "confidence": safe_float(control.get("confidence"), 0.0),
    }


def build_applicator_plan(
    *,
    project_name: str,
    chain_plan_path: Path,
    mapping_report_path: Path,
    category_results: list[dict[str, Any]],
    apply_allowed: bool,
    rollback_output_path: Path,
    lua_plan_path: Path,
) -> dict[str, Any]:
    fx_to_insert = []
    for item in category_results:
        if not item.get("safe"):
            continue
        writes = []
        adapter = item.get("_adapter") or {}
        for semantic, value in item.get("semantic_settings", {}).items():
            entry = _parameter_write_entry(adapter, semantic, value)
            if entry:
                writes.append(entry)
        fx_to_insert.append(
            {
                "target_role": item.get("target_role") or "final_vocal_space_bus",
                "category": item.get("category"),
                "plugin_name_for_reaper": item.get("plugin_name"),
                "adapter_id": item.get("adapter_id"),
                "parameter_writes": writes,
                "insert_only_if_bus_muted": True,
            }
        )
    plan = {
        "schema": APPLICATOR_PLAN_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "apply_allowed": bool(apply_allowed),
        "chain_plan_path": str(chain_plan_path),
        "mapping_report_path": str(mapping_report_path),
        "rollback_output_path": str(rollback_output_path),
        "fx_to_insert": fx_to_insert,
        "draft_tracks": ["FINAL VOCAL SPACE LEAD DRAFT"],
        "draft_buses": ["FINAL VOCAL SPACE BUS"],
        "pitch_correction_blocked": True,
        "master_modification_blocked": True,
        "final_export_blocked": True,
        "parameter_writes_require_name_match": True,
        "no_fixed_parameter_indexes": True,
    }
    write_json(lua_plan_path.with_suffix(".json"), plan)
    write_lua_applicator_plan(lua_plan_path, plan)
    return plan


def _lua_string(value: Any) -> str:
    text = str(value or "")
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def write_lua_applicator_plan(path: Path, plan: dict[str, Any]) -> Path:
    lines = [
        "-- Generated by final_placement_adapter_mapping.py. Review before use in REAPER.",
        "return {",
        f"  schema = {_lua_string(plan['schema'])},",
        f"  project_name = {_lua_string(plan['project_name'])},",
        f"  apply_allowed = {'true' if plan.get('apply_allowed') else 'false'},",
        f"  chain_plan_path = {_lua_string(plan.get('chain_plan_path'))},",
        f"  mapping_report_path = {_lua_string(plan.get('mapping_report_path'))},",
        f"  rollback_output_path = {_lua_string(plan.get('rollback_output_path'))},",
        "  pitch_correction_blocked = true,",
        "  master_modification_blocked = true,",
        "  final_export_blocked = true,",
        "  fx_to_insert = {",
    ]
    for fx in plan.get("fx_to_insert", []):
        lines.extend(
            [
                "    {",
                f"      target_role = {_lua_string(fx.get('target_role'))},",
                f"      category = {_lua_string(fx.get('category'))},",
                f"      plugin_name_for_reaper = {_lua_string(fx.get('plugin_name_for_reaper'))},",
                f"      adapter_id = {_lua_string(fx.get('adapter_id'))},",
                "      parameter_writes = {",
            ]
        )
        for write in fx.get("parameter_writes", []):
            lines.append(
                "        { semantic = "
                + _lua_string(write.get("semantic"))
                + ", target_name = "
                + _lua_string(write.get("target_name"))
                + ", normalized_value = "
                + str(round(safe_float(write.get("normalized_value"), 0.0), 8))
                + " },"
            )
        lines.extend(["      },", "    },"])
    lines.extend(["  },", "}", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def validate_final_placement_adapters(
    *,
    output_dir: str | Path = "automix",
    chain_plan_path: str | Path | None = None,
    inventory_path: str | Path | None = None,
    adapter_dirs: list[str | Path] | None = None,
    min_confidence: float = 0.85,
    allow_offline_validated_adapters: bool = False,
    generate_applicator_plan: bool = True,
) -> dict[str, Any]:
    output = Path(output_dir)
    chain_path = Path(chain_plan_path) if chain_plan_path else output / "chain_plans" / "final_vocal_space_carving_chain_plan.json"
    inventory = load_inventory(Path(inventory_path) if inventory_path else output / "plugin_inventory.json")
    plugin_audit_path = output / "analysis_reports" / "plugin_inventory_audit.json"
    plugin_audit = _read_json(plugin_audit_path, {})
    if not plugin_audit:
        plugin_audit = audit_plugin_inventory(inventory, output_dir=output)
    dirs = [Path(p) for p in (adapter_dirs or [])]
    if not dirs:
        dirs = [output / "plugins" / "builtin_adapters", output / "plugins" / "learned_adapters", Path("automix/plugins/builtin_adapters"), Path("automix/plugins/learned_adapters")]
    adapters = load_adapters(dirs)
    chain_plan = _read_json(chain_path, {})
    project_name = chain_plan.get("project_name") or plugin_audit.get("project_name") or inventory.get("reaper", {}).get("project_name", "project")
    detected_plugin_names = _detected_plugin_names(plugin_audit, inventory)

    blockers: list[str] = []
    warnings: list[str] = []
    if not chain_path.exists():
        blockers.append("final_vocal_space_chain_plan_missing")
    if chain_plan.get("contains_pitch_correction"):
        blockers.append("chain_plan_contains_pitch_correction")
    if chain_plan.get("contains_master_limiter"):
        blockers.append("chain_plan_contains_master_limiter")
    if not chain_plan.get("original_tracks_must_remain_untouched", False):
        blockers.append("chain_plan_does_not_protect_original_tracks")

    category_results = []
    for category_item in _category_items(chain_plan):
        best = _best_adapter(
            category_item,
            adapters,
            detected_plugin_names,
            min_confidence=min_confidence,
            allow_offline_validated_adapters=allow_offline_validated_adapters,
        )
        gate = best["gate"]
        safe = bool(gate.get("allowed"))
        if not safe:
            blockers.append(f"{category_item['category']}_adapter_not_validated")
        result = {
            "category": category_item["category"],
            "target_role": category_item["target_role"],
            "source_plugin_label": category_item["source_plugin_label"],
            "required_controls": category_item["required_controls"],
            "semantic_settings": category_item["semantic_settings"],
            "adapter_id": best.get("adapter_id"),
            "plugin_name": best.get("plugin_name"),
            "adapter_confidence": best.get("adapter_confidence", 0.0),
            "safe": safe,
            "gate": gate,
            "_adapter": best.get("adapter") or {},
        }
        category_results.append(result)

    all_categories_safe = bool(category_results and all(item["safe"] for item in category_results))
    apply_allowed = bool(all_categories_safe and not blockers and chain_plan.get("draft_only", False) and not chain_plan.get("contains_pitch_correction"))
    rollback_output = output / "rollback" / "final_vocal_space_reaper_applicator_rollback.json"
    report_path = output / "eval_reports" / "final_placement_adapter_mapping_report.json"
    lua_plan_path = output / "chain_plans" / "final_vocal_space_applicator_plan.lua"
    applicator_plan = {}
    if generate_applicator_plan:
        applicator_plan = build_applicator_plan(
            project_name=project_name,
            chain_plan_path=chain_path,
            mapping_report_path=report_path,
            category_results=category_results,
            apply_allowed=apply_allowed,
            rollback_output_path=rollback_output,
            lua_plan_path=lua_plan_path,
        )

    public_results = [{key: value for key, value in item.items() if key != "_adapter"} for item in category_results]
    report = {
        "schema": REPORT_SCHEMA,
        "created_at": now_utc(),
        "project_name": project_name,
        "chain_plan": str(chain_path),
        "inventory_path": str(inventory_path or output / "plugin_inventory.json"),
        "adapter_dirs": [str(path) for path in dirs],
        "min_confidence": min_confidence,
        "detected_plugin_names": detected_plugin_names,
        "categories_required": [item["category"] for item in category_results],
        "category_results": public_results,
        "all_required_categories_safe": all_categories_safe,
        "apply_allowed": apply_allowed,
        "applicator_plan_json": str(lua_plan_path.with_suffix(".json")),
        "applicator_plan_lua": str(lua_plan_path),
        "rollback_output_path": str(rollback_output),
        "blocked_reasons": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "safety": {
            "no_audio_changes": True,
            "no_reaper_project_changes": True,
            "no_pitch_plugins": True,
            "no_final_export": True,
            "no_fixed_parameter_indexes": True,
            "parameter_writes_require_name_match": True,
            "normalized_parameter_values_only": True,
        },
    }
    write_json(report_path, report)
    write_mapping_markdown_report(report, output / "eval_reports" / "final_placement_adapter_mapping_report.md")
    write_json(output / "logs" / "final_placement_adapter_validation_log.json", report)
    return {**report, "applicator_plan": applicator_plan}


def write_mapping_markdown_report(report: dict[str, Any], path: Path) -> Path:
    lines = [
        "# Final Placement Adapter Mapping Report",
        "",
        f"- Project: `{report.get('project_name')}`",
        f"- Apply allowed: `{report.get('apply_allowed')}`",
        f"- All required categories safe: `{report.get('all_required_categories_safe')}`",
        f"- Blocked reasons: `{', '.join(report.get('blocked_reasons', [])) or 'none'}`",
        "",
        "## Category Results",
        "",
        "| Category | Target | Plugin | Adapter | Safe | Required Controls | Reason Codes |",
        "|---|---|---|---|---:|---|---|",
    ]
    for item in report.get("category_results", []):
        reason_codes = item.get("gate", {}).get("reason_codes", [])
        lines.append(
            f"| `{item.get('category')}` | `{item.get('target_role')}` | `{item.get('plugin_name')}` | `{item.get('adapter_id')}` | `{item.get('safe')}` | `{', '.join(item.get('required_controls', []))}` | `{', '.join(reason_codes)}` |"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Pitch correction remains blocked.",
            "- No final export is created.",
            "- No parameter index assumptions are allowed.",
            "- REAPER parameter writes require target-name lookup and normalized 0-1 values.",
            "- If this report is not fully safe, the REAPER applicator must remain disabled.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
