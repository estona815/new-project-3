from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc


COMPACT_CONTEXT_SCHEMA = "automix-compact-mix-context-v1"
DEFAULT_CONTEXT_PATH = Path("work/state/RUN_CONTEXT.compact.json")
DEFAULT_OUTPUT_DIR = Path("automix")
DEFAULT_PROJECT_NAME = "project"
MAIN_VOCAL_TRACK = "08 MALE_NONHOOK_CENTER"
REQUIRED_AI_RESCUE_PLUGIN = "JS: Codex Vocal AI Artifact Split Tamer"
ALLOWED_PRIMARY_TARGETS = [
    "vocal_clarity",
    "vocal_center_stability",
    "female_layer_control",
    "low_end_density",
    "instrumental_presence",
    "ai_fizz_reduction",
    "master_cohesion",
    "limiter_pressure_control",
]


def build_compact_mix_context(
    *,
    project_name: str = DEFAULT_PROJECT_NAME,
    workspace_root: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    workspace_root = workspace_root.resolve()
    output_dir = _resolve(workspace_root, output_dir)

    current_state_path = output_dir / "eval_reports/current_state_summary.json"
    harness_path = output_dir / "eval_reports/mix_master_quality_harness.json"
    asset_manifest_path = workspace_root / "work/assets/asset_manifest.json"
    plugin_trace_path = workspace_root / "work/traces/plugin_trace.json"
    validation_gates_path = workspace_root / "work/traces/validation_gates.json"
    qc_report_path = workspace_root / "work/qc/qc_report.json"
    final_qc_metrics_path = output_dir / "eval_reports/final_qc_metrics.json"
    final_export_state_path = output_dir / "export/final_export_state.json"
    final_render_manifest_path = output_dir / "export/final_render_manifest.json"
    ab_preview_gate_path = output_dir / "eval_reports/ab_preview_evidence_gate.json"
    source_acceptance_path = output_dir / "eval_reports/source_acceptance_gate.json"

    current_state = _load_json(current_state_path)
    harness = _load_json(harness_path)
    asset_manifest = _load_json(asset_manifest_path)
    plugin_trace = _load_json(plugin_trace_path)
    validation_gates = _load_json(validation_gates_path)
    qc_report = _load_json(qc_report_path)
    final_qc_metrics = _load_json(final_qc_metrics_path)
    final_export_state = _load_json(final_export_state_path)
    final_render_manifest = _load_json(final_render_manifest_path)
    ab_preview_gate = _load_json(ab_preview_gate_path)
    source_acceptance = _load_json(source_acceptance_path)

    blockers = _unique(
        list(current_state.get("blockers", []))
        + list(current_state.get("qc", {}).get("critical_blockers", []))
        + list(harness.get("blockers", []))
    )
    warnings = _unique(list(current_state.get("warnings", [])) + list(harness.get("warnings", [])))
    gates = harness.get("current_gate_status", {})
    assets = _asset_summary(asset_manifest, asset_manifest_path, workspace_root)
    plugin_status = _plugin_trace_summary(plugin_trace, plugin_trace_path, validation_gates, workspace_root)
    qc_headline = _qc_headline(qc_report, qc_report_path, final_qc_metrics, final_qc_metrics_path, workspace_root)
    gate_snapshot = _gate_snapshot(harness, workspace_root)
    active_path_safety = _active_path_safety_status(validation_gates)
    quality_gate = _quality_gate_compact(
        safe_to_export=bool(current_state.get("safe_to_export", False)),
        workspace_root=workspace_root,
        assets=assets,
        plugin_status=plugin_status,
        qc_headline=qc_headline,
        gate_snapshot=gate_snapshot,
        active_path_safety=active_path_safety,
    )
    delivery_status = quality_gate["delivery_status"]
    source_status = _source_stem_approval_status(source_acceptance, gates)
    last_render_path = _last_render_path(final_render_manifest, final_export_state, qc_headline)
    last_ab_preview_path = _last_ab_preview_path(ab_preview_gate)
    next_actions = _recommended_next_actions(blockers, gates, current_state)

    context = {
        "schema": COMPACT_CONTEXT_SCHEMA,
        "created_at": now_utc(),
        "project_name": project_name,
        "workspace_root": str(workspace_root),
        "current_slug": plugin_status.get("slug") or project_name,
        "delivery_status": delivery_status,
        "safe_to_export": bool(current_state.get("safe_to_export", False)),
        "approved_previous_render": _approved_previous_render(final_export_state),
        "source_stem_approval_status": source_status,
        "reference_profile_path": _reference_profile_path(workspace_root),
        "latest_qc_headline": qc_headline,
        "open_blockers": _limit(blockers, 12),
        "next_primary_mix_target": _next_primary_mix_target(blockers, qc_headline),
        "user_taste_notes": _user_taste_notes(),
        "plugin_trace_status": plugin_status,
        "active_path_safety_status": active_path_safety,
        "last_render_path": last_render_path,
        "last_ab_preview_path": last_ab_preview_path,
        "next_required_action": next_actions[0] if next_actions else "Refresh compact context before the next pass.",
        "token_policy": {
            "read_first": [
                str(DEFAULT_CONTEXT_PATH),
                "work/state/current_state_summary.md",
                "work/state/QUALITY_GATE.compact.json",
                "reports/latest_qc_headline.json",
                "work/blockers/open_blockers.json",
                "work/state/PASS_PLAN.latest.json",
            ],
            "open_full_docs_only_when_needed": [
                "REAPER_REFERENCE_MIX_PIPELINE.md",
                "MASTERING_QC_STANDARD.md",
                "USER_FEEDBACK_REVISION_LOOP.md",
                "docs/automix_runbook.md",
            ],
            "default_max_primary_complaints": 3,
            "default_candidate_renders": 1,
            "max_candidate_passes_without_explicit_user_request": 2,
        },
        "claim_boundary": _claim_boundary(current_state, harness, blockers),
        "current_state": {
            "path": _relative(workspace_root, current_state_path),
            "exists": current_state_path.exists(),
            "mode": current_state.get("mode"),
            "global_status": current_state.get("global_status", "unknown"),
            "development_status": current_state.get("development_status", "unknown"),
            "overall_qc_status": current_state.get("overall_qc_status", "unknown"),
            "safe_to_export": bool(current_state.get("safe_to_export", False)),
            "stage_status": current_state.get("stage_status", {}),
            "next_required_actions": _limit(current_state.get("next_required_actions", []), 6),
        },
        "readiness": {
            "source_ready": bool(gates.get("source_ready", False)),
            "parameter_write_ready": bool(gates.get("parameter_write_ready", False)),
            "render_qc_ready": bool(gates.get("render_qc_ready", False)),
            "safe_to_export": bool(current_state.get("safe_to_export", False)),
            "ready_for_high_quality_offline_planning": bool(
                harness.get("readiness", {}).get("ready_for_high_quality_offline_planning", False)
            ),
            "ready_for_reaper_dry_run": bool(harness.get("readiness", {}).get("ready_for_reaper_dry_run", False)),
            "ready_for_applied_parameter_writes": bool(
                harness.get("readiness", {}).get("ready_for_applied_mix_or_master_parameter_writes", False)
            ),
            "ready_for_delivery_claims": bool(harness.get("readiness", {}).get("ready_for_delivery_claims", False)),
            "render_was_created_by_harness": bool(harness.get("readiness", {}).get("render_was_created", False)),
        },
        "assets": assets,
        "plugin_trace": plugin_status,
        "qc_headline": qc_headline,
        "quality_gate": quality_gate,
        "gate_snapshot": gate_snapshot,
        "blockers": _limit(blockers, 12),
        "warnings": _limit(warnings, 12),
        "recommended_next_actions": next_actions,
        "run_constraints": [
            "Preserve source timing and arrangement unless the user explicitly requests edits.",
            "Keep full mix/reference tracks muted and out of the active master path.",
            "Use measured render/QC evidence before delivery or reference-match claims.",
            "For AI vocal cleanup, prove the required first-slot rescue plugin in plugin trace.",
            "Treat unresolved user feedback as delivery-blocking.",
        ],
        "source_files": {
            "current_state_summary": _relative(workspace_root, current_state_path),
            "mix_master_quality_harness": _relative(workspace_root, harness_path),
            "asset_manifest": _relative(workspace_root, asset_manifest_path),
            "plugin_trace": _relative(workspace_root, plugin_trace_path),
            "qc_report": _relative(workspace_root, qc_report_path),
            "final_qc_metrics": _relative(workspace_root, final_qc_metrics_path),
        },
    }
    return context


def write_compact_mix_context(context: dict[str, Any], context_path: Path, *, workspace_root: Path) -> dict[str, str]:
    workspace_root = workspace_root.resolve()
    context_path = _resolve(workspace_root, context_path)
    markdown_path = context_path.with_suffix(".md")
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text(json.dumps(context, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(compact_context_markdown(context), encoding="utf-8")
    support_paths = write_compact_support_files(context, workspace_root=workspace_root)
    return {
        "json": str(context_path),
        "markdown": str(markdown_path),
        **support_paths,
    }


def write_compact_support_files(context: dict[str, Any], *, workspace_root: Path) -> dict[str, str]:
    paths: dict[str, str] = {}
    quality_gate_path = workspace_root / "work/state/QUALITY_GATE.compact.json"
    current_summary_path = workspace_root / "work/state/current_state_summary.md"
    latest_qc_path = workspace_root / "reports/latest_qc_headline.json"
    blockers_path = workspace_root / "work/blockers/open_blockers.json"
    read_order_path = workspace_root / "work/state/READ_ORDER.md"
    token_budget_path = workspace_root / "work/state/TOKEN_BUDGET.md"
    pass_template_path = workspace_root / "work/state/PASS_PLAN.template.json"
    pass_latest_path = workspace_root / "work/state/PASS_PLAN.latest.json"
    reference_template_path = workspace_root / "reports/reference_profile.template.json"

    _write_json(quality_gate_path, context.get("quality_gate", {}))
    _write_json(latest_qc_path, context.get("latest_qc_headline", {}))
    _write_json(blockers_path, _open_blockers_payload(context))
    _write_json(pass_template_path, _pass_plan_template_payload())
    if not pass_latest_path.exists():
        _write_json(pass_latest_path, _pass_plan_latest_payload(context))
    _write_json(reference_template_path, _reference_profile_template_payload())
    current_summary_path.parent.mkdir(parents=True, exist_ok=True)
    current_summary_path.write_text(_current_state_summary_markdown(context), encoding="utf-8")
    read_order_path.parent.mkdir(parents=True, exist_ok=True)
    read_order_path.write_text(_read_order_markdown(), encoding="utf-8")
    token_budget_path.parent.mkdir(parents=True, exist_ok=True)
    token_budget_path.write_text(_token_budget_markdown(), encoding="utf-8")

    for key, path in {
        "quality_gate_json": quality_gate_path,
        "current_state_summary_md": current_summary_path,
        "latest_qc_json": latest_qc_path,
        "open_blockers_json": blockers_path,
        "read_order_md": read_order_path,
        "token_budget_md": token_budget_path,
        "pass_plan_template_json": pass_template_path,
        "pass_plan_latest_json": pass_latest_path,
        "reference_profile_template_json": reference_template_path,
    }.items():
        paths[key] = str(path)
    return paths


def compact_context_markdown(context: dict[str, Any]) -> str:
    readiness = context.get("readiness", {})
    current = context.get("current_state", {})
    plugin = context.get("plugin_trace", {})
    qc = context.get("qc_headline", {})
    assets = context.get("assets", {})
    lines = [
        "# Compact Mix Context",
        "",
        f"- Schema: `{context.get('schema')}`",
        f"- Project: `{context.get('project_name')}`",
        f"- Created UTC: `{context.get('created_at')}`",
        f"- Claim boundary: `{context.get('claim_boundary')}`",
        "",
        "## State",
        "",
        f"- Mode: `{current.get('mode')}`",
        f"- Global status: `{current.get('global_status')}`",
        f"- Development status: `{current.get('development_status')}`",
        f"- Overall QC: `{current.get('overall_qc_status')}`",
        f"- Safe to export: `{current.get('safe_to_export')}`",
        "",
        "## Readiness",
        "",
    ]
    for key in [
        "source_ready",
        "parameter_write_ready",
        "render_qc_ready",
        "safe_to_export",
        "ready_for_high_quality_offline_planning",
        "ready_for_reaper_dry_run",
        "ready_for_delivery_claims",
    ]:
        lines.append(f"- `{key}`: `{readiness.get(key)}`")
    lines.extend(
        [
            "",
            "## Assets",
            "",
            f"- Stems: `{assets.get('stem_count')}`",
            f"- References: `{assets.get('reference_count')}`",
            f"- Manifest: `{assets.get('path')}`",
            "",
            "## Plugin Trace",
            "",
            f"- Exists: `{plugin.get('exists')}`",
            f"- Slug: `{plugin.get('slug')}`",
            f"- Required first slot OK: `{plugin.get('required_first_slot_ok')}`",
            f"- Main vocal first FX: `{plugin.get('main_vocal_first_fx')}`",
            "",
            "## QC Headline",
            "",
            f"- Status: `{qc.get('status')}`",
            f"- Audio path: `{qc.get('audio_path')}`",
            f"- Metrics measured: `{qc.get('metrics_measured')}`",
            f"- Integrated LUFS: `{qc.get('integrated_lufs')}`",
            f"- True peak: `{qc.get('true_peak_db_tp')}`",
            "",
            "## Blockers",
            "",
        ]
    )
    blockers = context.get("blockers", [])
    if blockers:
        lines.extend(f"- `{blocker}`" for blocker in blockers)
    else:
        lines.append("- none")
    lines.extend(["", "## Recommended Next Actions", ""])
    actions = context.get("recommended_next_actions", [])
    if actions:
        lines.extend(f"- {action}" for action in actions)
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def _asset_summary(asset_manifest: dict[str, Any], asset_manifest_path: Path, workspace_root: Path) -> dict[str, Any]:
    return {
        "path": _relative(workspace_root, asset_manifest_path),
        "exists": asset_manifest_path.exists(),
        "stems_root": asset_manifest.get("stems_root", "input/stems"),
        "reference_root": asset_manifest.get("reference_root", "input/reference"),
        "stem_count": int(asset_manifest.get("stem_count", 0) or 0),
        "reference_count": int(asset_manifest.get("reference_count", 0) or 0),
        "unknown_stem_count": int(asset_manifest.get("unknown_stem_count", 0) or 0),
        "source_manifest_hash": asset_manifest.get("source_manifest_hash"),
    }


def _plugin_trace_summary(
    plugin_trace: dict[str, Any],
    plugin_trace_path: Path,
    validation_gates: dict[str, Any],
    workspace_root: Path,
) -> dict[str, Any]:
    rows = list(plugin_trace.get("rows", []))
    first_slot = None
    for row in rows:
        if row.get("track") == MAIN_VOCAL_TRACK and _safe_int(row.get("fx_index"), default=-1) == 0:
            first_slot = row
            break
    required_ok = bool(first_slot and first_slot.get("plugin") == REQUIRED_AI_RESCUE_PLUGIN and first_slot.get("status") == "loaded")
    loaded = [row for row in rows if row.get("status") == "loaded"]
    missing = [row for row in rows if row.get("status") == "missing"]
    return {
        "path": _relative(workspace_root, plugin_trace_path),
        "exists": plugin_trace_path.exists(),
        "slug": plugin_trace.get("slug"),
        "source_full_mix_policy": plugin_trace.get("source_full_mix_policy"),
        "required_main_track": plugin_trace.get("required_main_track", MAIN_VOCAL_TRACK),
        "required_first_slot_ok": required_ok,
        "main_vocal_first_fx": first_slot.get("plugin") if first_slot else None,
        "main_vocal_first_fx_status": first_slot.get("status") if first_slot else "missing",
        "loaded_plugin_count": len(loaded),
        "missing_plugin_count": len(missing),
        "validation_gates": validation_gates if validation_gates else {},
    }


def _qc_headline(
    qc_report: dict[str, Any],
    qc_report_path: Path,
    final_qc_metrics: dict[str, Any],
    final_qc_metrics_path: Path,
    workspace_root: Path,
) -> dict[str, Any]:
    source = final_qc_metrics if final_qc_metrics else qc_report
    path = final_qc_metrics_path if final_qc_metrics else qc_report_path
    metrics = source.get("metrics", {})
    loudness = source.get("loudness", {})
    file_integrity = source.get("file_integrity", {})
    audio_path = source.get("audio_path") or source.get("final_audio_path")
    metrics_measured = _qc_metrics_measured(metrics, file_integrity)
    return {
        "path": _relative(workspace_root, path),
        "exists": path.exists(),
        "status": source.get("status") or _qc_status_from_flags(source),
        "qc_passed": source.get("qc_passed"),
        "audio_path": None if audio_path in {"", "."} else audio_path,
        "metrics_measured": metrics_measured,
        "duration_seconds": file_integrity.get("duration_seconds") if metrics_measured else None,
        "sample_rate": file_integrity.get("sample_rate") if metrics_measured else None,
        "bit_depth": file_integrity.get("bit_depth") if metrics_measured else None,
        "integrated_lufs": _metric_value(metrics, "integrated_lufs", loudness.get("integrated_lufs")) if metrics_measured else None,
        "true_peak_db_tp": _metric_value(metrics, "true_peak_db_tp", loudness.get("true_peak_dbTP")) if metrics_measured else None,
        "sample_peak_dbfs": _metric_value(metrics, "sample_peak_dbfs", loudness.get("sample_peak_dbFS")) if metrics_measured else None,
        "stereo_correlation": _metric_value(metrics, "stereo_correlation") if metrics_measured else None,
        "summary": source.get("summary"),
        "failures": _limit(source.get("failures", []), 6),
        "warnings": _limit(source.get("warnings", []), 6),
    }


def _gate_snapshot(harness: dict[str, Any], workspace_root: Path) -> dict[str, Any]:
    gates = harness.get("current_gate_status", {}).get("gates", {})
    snapshot: dict[str, Any] = {}
    for name, gate in gates.items():
        snapshot[name] = {
            "path": _relative(workspace_root, Path(gate.get("path", ""))) if gate.get("path") else "",
            "found": bool(gate.get("found", False)),
            "ready": bool(gate.get("ready", False)),
            "passed": gate.get("passed"),
            "blockers": _limit(gate.get("blockers", []), 5),
            "warnings": _limit(gate.get("warnings", []), 3),
        }
    return snapshot


def _active_path_safety_status(validation_gates: dict[str, Any]) -> dict[str, Any]:
    checks = validation_gates.get("gate_checks", {})
    raw_full_mix_not_active = bool(checks.get("raw_full_mix_not_active", False))
    reference_muted = bool(checks.get("full_mix_reference_muted", False))
    reference_master_send_disabled = bool(checks.get("full_mix_reference_master_send_disabled", False))
    reference_safe = reference_muted and reference_master_send_disabled
    return {
        "status": "pass" if raw_full_mix_not_active and reference_safe else "blocked_or_unverified",
        "raw_full_mix_not_in_active_path": raw_full_mix_not_active,
        "reference_tracks_muted_and_master_send_disabled": reference_safe,
        "full_mix_reference_muted": reference_muted,
        "full_mix_reference_master_send_disabled": reference_master_send_disabled,
        "required_routing_exists": bool(checks.get("required_routing_exists", False)),
        "required_buses_exist": bool(checks.get("required_buses_exist", False)),
    }


def _quality_gate_compact(
    *,
    safe_to_export: bool,
    workspace_root: Path,
    assets: dict[str, Any],
    plugin_status: dict[str, Any],
    qc_headline: dict[str, Any],
    gate_snapshot: dict[str, Any],
    active_path_safety: dict[str, Any],
) -> dict[str, Any]:
    hard_gate = {
        "source_approval_confirmed": _gate_ready(gate_snapshot, "source_acceptance"),
        "reference_profile_cached": bool(_reference_profile_path(workspace_root)),
        "raw_full_mix_not_in_active_path": bool(active_path_safety.get("raw_full_mix_not_in_active_path")),
        "reference_tracks_muted_and_master_send_disabled": bool(
            active_path_safety.get("reference_tracks_muted_and_master_send_disabled")
        ),
        "render_completed": _gate_ready(gate_snapshot, "final_render_evidence"),
        "qc_completed": _gate_ready(gate_snapshot, "final_qc_evidence") and bool(qc_headline.get("metrics_measured")),
        "loudness_matched_ab_completed": _gate_ready(gate_snapshot, "ab_preview_evidence"),
        "plugin_semantic_validation_completed": _gate_ready(gate_snapshot, "plugin_semantic_validation"),
    }
    soft_gate = {
        "male_vocal_center_confirmed": bool(plugin_status.get("required_main_track")),
        "male_vocal_clear_and_forward": False,
        "female_vocal_not_lead": True,
        "instrumental_not_buried": False,
        "low_end_density_ok": False,
        "harshness_controlled": False,
        "ai_fizz_controlled": False,
        "mono_fold_down_ok": False,
        "limiter_pressure_ok": False,
    }
    hard_blockers = [key for key, value in hard_gate.items() if not value]
    delivery_status = _delivery_status_from_gates(safe_to_export, hard_gate, qc_headline)
    return {
        "schema": "automix-quality-gate-compact-v1",
        "created_at": now_utc(),
        "safe_to_export": safe_to_export,
        "delivery_status": delivery_status,
        "hard_gate": hard_gate,
        "soft_gate": soft_gate,
        "hard_blockers": hard_blockers,
        "soft_watch_items": [key for key, value in soft_gate.items() if not value],
        "rules": {
            "safe_to_export_false_allows_only": ["blocked", "review_copy"],
            "delivery_ready_requires_all_hard_gates_true": True,
            "reference_or_raw_full_mix_must_not_enter_active_master_path": True,
            "male_vocal_center_lead": True,
            "female_vocal_support_only": True,
            "no_louder_master_before_qc": True,
        },
        "evidence": {
            "asset_manifest": assets.get("path"),
            "plugin_trace": plugin_status.get("path"),
            "latest_qc_headline": qc_headline.get("path"),
        },
    }


def _gate_ready(gate_snapshot: dict[str, Any], gate_name: str) -> bool:
    gate = gate_snapshot.get(gate_name, {})
    return bool(gate.get("ready") or gate.get("passed") is True)


def _delivery_status_from_gates(safe_to_export: bool, hard_gate: dict[str, bool], qc_headline: dict[str, Any]) -> str:
    all_hard = all(hard_gate.values())
    if safe_to_export and all_hard:
        return "delivery_ready"
    if qc_headline.get("metrics_measured") and hard_gate.get("render_completed") and hard_gate.get("qc_completed"):
        return "review_copy"
    return "blocked"


def _source_stem_approval_status(source_acceptance: dict[str, Any], gates: dict[str, Any]) -> str:
    if source_acceptance.get("accepted_export_source_ready") or gates.get("source_ready"):
        return "approved"
    if source_acceptance.get("candidate_sources_total", 0):
        return "candidate_review_required"
    return "missing_or_unconfirmed"


def _approved_previous_render(final_export_state: dict[str, Any]) -> str | None:
    selected = final_export_state.get("selected_export_source")
    if selected:
        return str(selected)
    return None


def _reference_profile_path(workspace_root: Path) -> str | None:
    candidates = sorted((workspace_root / "reports").glob("reference_profile*.json"))
    candidates = [path for path in candidates if path.name != "reference_profile.template.json"]
    if candidates:
        return str(candidates[-1])
    return None


def _last_render_path(final_render_manifest: dict[str, Any], final_export_state: dict[str, Any], qc_headline: dict[str, Any]) -> str | None:
    renders = final_render_manifest.get("renders", [])
    for render in reversed(renders):
        if isinstance(render, dict) and render.get("path"):
            return str(render["path"])
        if isinstance(render, str):
            return render
    selected = final_export_state.get("selected_export_source")
    if selected:
        return str(selected)
    audio_path = qc_headline.get("audio_path")
    return str(audio_path) if audio_path else None


def _last_ab_preview_path(ab_preview_gate: dict[str, Any]) -> str | None:
    manifest = ab_preview_gate.get("manifest_summary", {})
    output = manifest.get("output_path")
    return str(output) if output else None


def _next_primary_mix_target(blockers: list[str], qc_headline: dict[str, Any]) -> str:
    blocker_text = " ".join(blockers).lower()
    failure_text = " ".join(qc_headline.get("failures", [])).lower()
    if "limiter" in blocker_text or "true_peak" in failure_text:
        return "limiter_pressure_control"
    if "fizz" in blocker_text or "artifact" in blocker_text:
        return "ai_fizz_reduction"
    if "female" in blocker_text:
        return "female_layer_control"
    return "vocal_clarity"


def _user_taste_notes() -> list[str]:
    return [
        "Male main vocal stays center lead.",
        "Female vocal is support only: side, shadow, double, harmony, or tucked layer.",
        "Fix masking, harshness, AI fizz, low-mid mud, mono fold-down, and limiter pressure before making the master louder.",
        "Keep raw full mix/reference muted with master send disabled and outside the active premaster/master path.",
        "Use one primary target per pass and one default candidate render.",
    ]


def _recommended_next_actions(blockers: list[str], gates: dict[str, Any], current_state: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    blocker_text = " ".join(blockers)
    if "accepted_source" in blocker_text or "source_acceptance" in blocker_text or not gates.get("source_ready", False):
        actions.append("Run source acceptance or provide accepted stem/export evidence before applied mix claims.")
    if "plugin_semantic_validation" in blocker_text or not gates.get("parameter_write_ready", False):
        actions.append("Keep FX parameter writes conservative until semantic plugin validation evidence passes.")
    if "final_render" in blocker_text or not gates.get("render_qc_ready", False):
        actions.append("Create or register a primary WAV render, then run final render and final QC evidence gates.")
    if "ab_preview" in blocker_text:
        actions.append("Create a loudness-matched A/B preview before human review or feedback closure.")
    if current_state.get("safe_to_export") is False:
        actions.append("Return review_copy or blocked status until QC, A/B, approval, package, and consistency gates pass.")
    return _limit(_unique(actions), 6)


def _open_blockers_payload(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "automix-open-blockers-compact-v1",
        "created_at": now_utc(),
        "delivery_status": context.get("delivery_status"),
        "safe_to_export": context.get("safe_to_export"),
        "open_blockers": context.get("open_blockers", []),
        "hard_blockers": context.get("quality_gate", {}).get("hard_blockers", []),
        "next_required_action": context.get("next_required_action"),
    }


def _pass_plan_template_payload() -> dict[str, Any]:
    return {
        "schema": "automix-pass-plan-template-v1",
        "pass_id": "",
        "primary_target": {
            "allowed_values": ALLOWED_PRIMARY_TARGETS,
            "selected": "",
        },
        "secondary_guardrails": [
            "raw_full_mix_reference_muted_and_out_of_master_path",
            "male_vocal_center_lead",
            "female_vocal_support_only",
            "no_louder_master_before_qc",
            "mono_fold_down_checked",
        ],
        "allowed_changes": [],
        "forbidden_changes": [
            "raw_full_mix_in_active_path",
            "female_vocal_as_lead",
            "unverified_final_delivery_claim",
            "commercial_ready_claim_without_gates",
            "master_louder_push_before_masking_harshness_fizz_mud_mono_limiter_checks",
            "three_or_more_candidate_renders_without_explicit_user_request",
        ],
        "expected_qc_improvement": [],
        "render_outputs": [],
        "qc_outputs": [],
        "rollback_plan": {
            "source_project_copy_required": True,
            "previous_render_preserved": True,
            "revert_method": "",
            "rollback_artifacts": [],
        },
    }


def _pass_plan_latest_payload(context: dict[str, Any]) -> dict[str, Any]:
    payload = _pass_plan_template_payload()
    payload.update(
        {
            "schema": "automix-pass-plan-latest-v1",
            "pass_id": "next_pass_unassigned",
            "primary_target": context.get("next_primary_mix_target", "vocal_clarity"),
            "allowed_changes": [
                "diagnostic planning",
                "routing safety inspection",
                "single-target conservative REAPER pass after blockers are cleared",
            ],
            "expected_qc_improvement": [
                "measurable improvement only after render and QC evidence exist",
            ],
            "render_outputs": [
                "renders/<slug>/<slug>_review.wav",
            ],
            "qc_outputs": [
                "reports/<slug>/qc_metrics.json",
                "reports/<slug>/decision_notes.md",
                "reports/<slug>/actual_reaper_plugin_trace.json",
            ],
        }
    )
    return payload


def _reference_profile_template_payload() -> dict[str, Any]:
    return {
        "schema": "automix-reference-profile-template-v1",
        "reference_name": "",
        "lufs_i": None,
        "true_peak_db": None,
        "lra": None,
        "crest_factor": None,
        "stereo_correlation": None,
        "low_band_energy": None,
        "low_mid_mud_band": None,
        "vocal_presence_band": None,
        "harshness_band": None,
        "air_band": None,
        "ai_fizz_band": None,
        "low_end_side_risk": None,
        "notes": "",
    }


def _current_state_summary_markdown(context: dict[str, Any]) -> str:
    lines = [
        "# Current State Summary",
        "",
        f"- Current slug: `{context.get('current_slug')}`",
        f"- Delivery status: `{context.get('delivery_status')}`",
        f"- Safe to export: `{context.get('safe_to_export')}`",
        f"- Source approval: `{context.get('source_stem_approval_status')}`",
        f"- Reference profile: `{context.get('reference_profile_path')}`",
        f"- Last render: `{context.get('last_render_path')}`",
        f"- Last A/B preview: `{context.get('last_ab_preview_path')}`",
        f"- Next primary mix target: `{context.get('next_primary_mix_target')}`",
        "",
        "## Next Required Action",
        "",
        f"- {context.get('next_required_action')}",
        "",
    ]
    return "\n".join(lines)


def _read_order_markdown() -> str:
    return """# Compact Read Order

Default read order is capped at six files:

1. `work/state/RUN_CONTEXT.compact.json`
2. `work/state/current_state_summary.md`
3. `work/state/QUALITY_GATE.compact.json`
4. `reports/latest_qc_headline.json`
5. `work/blockers/open_blockers.json`
6. `work/state/PASS_PLAN.latest.json`

Open long prompts, long reports, historical logs, and old render notes only when
an open blocker directly requires that evidence. Do not reread old logs to fill
ordinary context; update `RUN_CONTEXT.compact.json` instead.
"""


def _token_budget_markdown() -> str:
    return """# Token Budget Rules

- Do not re-summarize entire project documents.
- Do not print full long files.
- Keep responses centered on changed files, blockers, QC headline, and next action.
- When information is missing, update `RUN_CONTEXT.compact.json` instead of growing the prompt.
- Select exactly one primary target per pass.
- Create one candidate render by default.
- Allow two candidates only when comparison is required.
- Do not create three or more candidates without explicit user request.
- Do not claim final delivery, commercial readiness, or reference matching while `safe_to_export` is false.
- Do not make the master louder before masking, harshness, AI fizz, low-mid mud, mono fold-down, and limiter pressure are checked.
"""


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _claim_boundary(current_state: dict[str, Any], harness: dict[str, Any], blockers: list[str]) -> str:
    if current_state.get("safe_to_export") and harness.get("readiness", {}).get("ready_for_delivery_claims"):
        return "delivery_ready_after_human_review"
    if harness.get("readiness", {}).get("ready_for_high_quality_offline_planning"):
        return "planning_or_review_copy_only"
    if blockers:
        return "blocked"
    return "unverified"


def _metric_value(metrics: dict[str, Any], key: str, fallback: Any = None) -> Any:
    value = metrics.get(key, fallback)
    if isinstance(value, dict):
        return value.get("value")
    return value


def _qc_metrics_measured(metrics: dict[str, Any], file_integrity: dict[str, Any]) -> bool:
    if (file_integrity.get("duration_seconds") or 0) > 0 and (file_integrity.get("sample_rate") or 0) > 0:
        return True
    for value in metrics.values():
        if isinstance(value, dict) and value.get("status") == "unavailable":
            continue
        if isinstance(value, dict) and value.get("value") is not None:
            return True
        if not isinstance(value, dict) and value is not None:
            return True
    return False


def _qc_status_from_flags(source: dict[str, Any]) -> str:
    if source.get("qc_passed") is True:
        return "PASS"
    if source.get("qc_passed") is False or source.get("failures"):
        return "BLOCKED"
    return "unknown"


def _safe_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _limit(items: Any, size: int) -> list[Any]:
    if not isinstance(items, list):
        return []
    return items[:size]


def _unique(items: list[Any]) -> list[Any]:
    seen = set()
    result = []
    for item in items:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False) if isinstance(item, (dict, list)) else str(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _resolve(root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return root / path


def _relative(root: Path, path: Path) -> str:
    if not path:
        return ""
    resolved = _resolve(root, path)
    try:
        return str(resolved.relative_to(root))
    except ValueError:
        return str(path)
