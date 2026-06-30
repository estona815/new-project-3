from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


OPEN_RISK_REGISTER_SCHEMA = "automix-open-risk-register-v1"

AUDIT_REL_PATH = Path("eval_reports/open_risk_register.json")
AUDIT_REPORT_REL_PATH = Path("eval_reports/open_risk_register.md")

REPORTS_TO_SCAN: list[dict[str, str]] = [
    {"rel": "eval_reports/intent_classification.json", "category": "intent"},
    {"rel": "eval_reports/real_project_source_safety_map.json", "category": "source"},
    {"rel": "eval_reports/source_acceptance_gate.json", "category": "source"},
    {"rel": "eval_reports/real_project_plugin_readiness.json", "category": "plugin"},
    {"rel": "eval_reports/plugin_semantic_validation_gate.json", "category": "plugin"},
    {"rel": "eval_reports/plugin_semantic_validation_collection_plan.json", "category": "plugin"},
    {"rel": "eval_reports/plugin_semantic_validation_queue.json", "category": "plugin"},
    {"rel": "eval_reports/plugin_semantic_validation_runtime_collection_package.json", "category": "plugin"},
    {"rel": "eval_reports/plugin_semantic_validation_runtime_collector_package.json", "category": "plugin"},
    {"rel": "eval_reports/reaper_runtime_collector_safety_audit.json", "category": "plugin"},
    {"rel": "eval_reports/reaper_runtime_collection_operator_readiness.json", "category": "plugin"},
    {"rel": "eval_reports/plugin_semantic_validation_runtime_observation_gate.json", "category": "plugin"},
    {"rel": "eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json", "category": "plugin"},
    {"rel": "eval_reports/plugin_semantic_validation_runtime_report_authoring_package.json", "category": "plugin"},
    {"rel": "eval_reports/plugin_semantic_validation_runtime_report_authoring_gate.json", "category": "plugin"},
    {"rel": "eval_reports/plugin_semantic_validation_runtime_evidence_gate.json", "category": "plugin"},
    {"rel": "eval_reports/plugin_validation_action_plan.json", "category": "plugin"},
    {"rel": "eval_reports/plugin_availability_resolution_plan.json", "category": "plugin"},
    {"rel": "eval_reports/plugin_availability_operator_decision_package.json", "category": "plugin"},
    {"rel": "eval_reports/plugin_availability_decision_gate.json", "category": "plugin"},
    {"rel": "eval_reports/artifact_evidence_gate.json", "category": "artifact"},
    {"rel": "eval_reports/ab_preview_evidence_gate.json", "category": "ab_preview"},
    {"rel": "eval_reports/global_qc_summary.json", "category": "qc"},
    {"rel": "eval_reports/final_qc_metrics.json", "category": "qc"},
    {"rel": "eval_reports/final_qc_evidence_gate.json", "category": "qc"},
    {"rel": "eval_reports/processing_policy_audit.json", "category": "processing_policy"},
    {"rel": "eval_reports/fixture_coverage_audit.json", "category": "harness"},
    {"rel": "eval_reports/requirements_traceability_audit.json", "category": "traceability"},
    {"rel": "eval_reports/professional_readiness_audit.json", "category": "delivery_readiness"},
    {"rel": "eval_reports/approval_export_readiness.json", "category": "delivery_readiness"},
    {"rel": "eval_reports/final_delivery_consistency_gate.json", "category": "delivery_readiness"},
    {"rel": "eval_reports/final_approval_evidence_gate.json", "category": "human_review"},
    {"rel": "eval_reports/deliverable_package_evidence_gate.json", "category": "package"},
    {"rel": "eval_reports/final_render_evidence_gate.json", "category": "render"},
    {"rel": "eval_reports/claim_language_guard.json", "category": "claims"},
    {"rel": "eval_reports/user_feedback_qc_integration.json", "category": "feedback"},
    {"rel": "export/final_export_state.json", "category": "final_export"},
    {"rel": "export/final_render_manifest.json", "category": "render"},
    {"rel": "export/deliverable_package_manifest.json", "category": "package"},
    {"rel": "export/project_state_manifest.json", "category": "project_state"},
    {"rel": "rollback/global_rollback_registry.json", "category": "rollback"},
    {"rel": "eval_reports/rollback_evidence_gate.json", "category": "rollback"},
    {"rel": "review/recovery_review_gate_summary.json", "category": "human_review"},
    {"rel": "review/final_human_approval.json", "category": "human_review"},
]

GENERIC_BLOCKER_FIELDS = ["blockers", "critical_blockers", "blocked_reasons", "failures"]
GENERIC_WARNING_FIELDS = ["warnings", "skipped_notes"]

NEXT_ACTION_HINTS = [
    ("validated_plugin_mapping", "run plugin inventory and adapter validation before draft processing"),
    ("semantic_validation_runtime", "validate queued REAPER runtime evidence and rerun semantic validation before parameter writes"),
    ("semantic_validation", "collect REAPER-observed semantic parameter validation reports before parameter writes"),
    ("artifact_evidence", "collect measured artifact metrics, source signal, or user feedback before artifact-focused work"),
    ("ab_preview_evidence", "create and validate a measured loudness-matched A/B preview before approval"),
    ("ab_preview", "create and validate a measured loudness-matched A/B preview before approval"),
    ("no_validated_safe_plugin_adapters", "validate stock/JSFX/plugin adapter mappings before safe draft work"),
    ("missing_or_unsafe_plugin_mapping", "map or disable unsafe plugins before automation"),
    ("isolated_stems_required", "provide isolated stems or keep the source in manual-review mode"),
    ("stem_required", "provide isolated stems before vocal recovery, placement, or pitch work"),
    ("source_acceptance", "validate accepted source/stem evidence before final export packaging"),
    ("explicit_source_acceptance", "record explicit user listening acceptance before accepting this source"),
    ("full_mix_unsafe", "do not pitch-correct the full mix; request stems or keep manual review"),
    ("unknown_tracks", "classify unknown tracks manually or rerun scan with clearer project labels"),
    ("no_accepted_export_source", "complete and accept a reviewed draft source before final export"),
    ("human_review", "complete human review and record approval/decision evidence"),
    ("final_approval_evidence", "record matched-loudness A/B approval evidence before delivery request"),
    ("deliverable_package_evidence", "create a real final ZIP and validate package evidence before professional delivery readiness"),
    ("final_delivery_consistency", "repair cross-report source, render, QC, A/B, approval, and package links before delivery readiness"),
    ("mismatch", "repair the mismatched evidence paths or regenerate downstream reports from the accepted source"),
    ("not_listed_in_package_manifest", "rebuild the deliverable package so final audio and preview files are included"),
    ("deliverable_package", "create a real final ZIP and validate package evidence before professional delivery readiness"),
    ("package_created", "create the deliverable ZIP after final render, QC, A/B, approval, and rollback evidence are ready"),
    ("files_missing", "repair missing package evidence files before rebuilding the deliverable ZIP"),
    ("zip", "create or repair the deliverable ZIP and verify it opens cleanly"),
    ("credential", "remove credential-like files from package inputs and rebuild the package"),
    ("secret", "remove secret-like files from package inputs and rebuild the package"),
    ("loudness_matched_ab_review", "record matched-loudness A/B listening evidence before final approval"),
    ("matched_loudness", "record matched-loudness A/B listening evidence before final approval"),
    ("feedback", "record or resolve user feedback with measured QC and loudness-matched A/B evidence"),
    ("final_delivery_not_requested", "run final-delivery readiness only after accepted source, render, package, QC, A/B, and approval exist"),
    ("diagnostic/report-only", "produce an accepted render only after delivery gates are ready"),
    ("final_render_evidence", "create a real primary WAV render and validate render evidence before final QC"),
    ("final_qc_evidence", "run final QC on the primary WAV and validate the metrics against render evidence"),
    ("final_qc", "run final QC on the primary WAV and validate the metrics against render evidence"),
    ("true_peak", "revise or rerender the master so measured true peak stays within the delivery ceiling"),
    ("digital_black", "rerender the final WAV or investigate routing if QC detects silence"),
    ("primary_wav", "create a real primary WAV render and validate render evidence before final QC"),
    ("supporting_report_missing", "generate the missing supporting report when that workflow has evidence"),
    ("claim", "revise unsupported delivery wording before packaging"),
    ("rollback", "repair rollback metadata before any applied-stage confidence or delivery"),
    ("render", "rerun render or keep the package in diagnostic mode until render evidence exists"),
]


def _load_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return {}, f"read_error:{path}:{exc}"
    except json.JSONDecodeError as exc:
        return {}, f"json_decode_error:{path}:{exc}"
    if not isinstance(data, dict):
        return {}, f"json_type_error:{path}:expected_object"
    return data, None


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _next_action(code: str, *, fallback: str = "review the source report and choose the safest next manual or dry-run step") -> str:
    lowered = code.lower()
    for needle, action in NEXT_ACTION_HINTS:
        if needle in lowered:
            return action
    return fallback


def _severity_rank(severity: str) -> int:
    return {"blocker": 0, "warning": 1, "review": 2, "info": 3}.get(severity, 9)


def _risk_id(source_rel: str, severity: str, code: str, index: int) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in f"{source_rel}_{severity}_{code}")[:96].strip("_")
    return f"risk_{index:03d}_{slug or 'unknown'}"


def _add_risk(
    risks: list[dict[str, Any]],
    *,
    severity: str,
    category: str,
    source_rel: str,
    code: str,
    summary: str,
    context: dict[str, Any] | None = None,
    recommended_next_action: str | None = None,
) -> None:
    risks.append(
        {
            "risk_id": _risk_id(source_rel, severity, code, len(risks) + 1),
            "severity": severity,
            "category": category,
            "source_report": source_rel,
            "code": str(code),
            "summary": str(summary),
            "context": context or {},
            "recommended_next_action": recommended_next_action or _next_action(str(code)),
        }
    )


def _collect_generic_risks(risks: list[dict[str, Any]], *, source_rel: str, category: str, data: dict[str, Any]) -> None:
    for field in GENERIC_BLOCKER_FIELDS:
        for item in _as_list(data.get(field)):
            code = str(item)
            _add_risk(
                risks,
                severity="blocker",
                category=category,
                source_rel=source_rel,
                code=code,
                summary=f"{field}: {code}",
            )
    for field in GENERIC_WARNING_FIELDS:
        for item in _as_list(data.get(field)):
            code = str(item)
            _add_risk(
                risks,
                severity="warning",
                category=category,
                source_rel=source_rel,
                code=code,
                summary=f"{field}: {code}",
            )


def _collect_source_safety_risks(risks: list[dict[str, Any]], *, source_rel: str, data: dict[str, Any]) -> None:
    summary = data.get("summary", {})
    for key in ("stem_required_tracks", "unknown_tracks", "full_mix_unsafe_tracks"):
        count = int(summary.get(key, 0) or 0)
        if count:
            _add_risk(
                risks,
                severity="blocker" if key != "unknown_tracks" else "review",
                category="source",
                source_rel=source_rel,
                code=f"{key}:{count}",
                summary=f"{count} {key.replace('_', ' ')} require review before automation",
                context={"count": count},
            )
    for track in data.get("high_risk_tracks", []) or []:
        if not isinstance(track, dict):
            continue
        name = str(track.get("track_name", "unknown track"))
        action = str(track.get("recommended_next_action", "manual_review_required"))
        risk_code = str(track.get("pitch_risk") or track.get("recovery_risk") or "high_risk_track")
        _add_risk(
            risks,
            severity="blocker" if "unsafe" in risk_code else "review",
            category="source",
            source_rel=source_rel,
            code=f"high_risk_track:{risk_code}:{name}",
            summary=f"High-risk source track `{name}` needs `{action}`",
            context={
                "track_name": name,
                "role": track.get("role"),
                "source_classification": track.get("source_classification"),
                "pitch_risk": track.get("pitch_risk"),
                "recovery_risk": track.get("recovery_risk"),
                "recommended_next_action": action,
                "warnings": track.get("warnings", []),
            },
            recommended_next_action=_next_action(action, fallback=action),
        )


def _collect_plugin_risks(risks: list[dict[str, Any]], *, source_rel: str, data: dict[str, Any]) -> None:
    if not data.get("safe_draft_plugin_ready", False):
        _add_risk(
            risks,
            severity="blocker",
            category="plugin",
            source_rel=source_rel,
            code="safe_draft_plugin_ready_false",
            summary="No validated safe plugin adapter set is ready for safe draft automation",
            recommended_next_action="run plugin inventory and adapter validation before draft processing",
        )
    mappings = data.get("missing_or_unsafe_mappings", []) or []
    for mapping in mappings[:20]:
        _add_risk(
            risks,
            severity="warning",
            category="plugin",
            source_rel=source_rel,
            code=f"missing_or_unsafe_plugin_mapping:{mapping}",
            summary=f"Plugin mapping is missing or unsafe: `{mapping}`",
            recommended_next_action="map, validate, or explicitly disable this plugin before automation",
        )


def _collect_intent_risks(risks: list[dict[str, Any]], *, source_rel: str, data: dict[str, Any]) -> None:
    safe_next = str(data.get("safe_next_mode", ""))
    if safe_next:
        _add_risk(
            risks,
            severity="info",
            category="intent",
            source_rel=source_rel,
            code=f"safe_next_mode:{safe_next}",
            summary=f"Recommended safe next mode is `{safe_next}`",
            recommended_next_action=_next_action(safe_next, fallback=safe_next),
        )
    if not data.get("safe_draft_intents"):
        _add_risk(
            risks,
            severity="review",
            category="intent",
            source_rel=source_rel,
            code="no_safe_draft_intents",
            summary="No safe draft intents are currently available",
            recommended_next_action=_next_action(safe_next or "validated_plugin_mapping_required"),
        )


def _collect_requirements_risks(risks: list[dict[str, Any]], *, source_rel: str, data: dict[str, Any]) -> None:
    for req_id in data.get("incomplete_requirement_ids", []) or []:
        _add_risk(
            risks,
            severity="blocker",
            category="traceability",
            source_rel=source_rel,
            code=f"incomplete_requirement:{req_id}",
            summary=f"Requirement `{req_id}` is incomplete in traceability audit",
        )


def _collect_final_state_risks(risks: list[dict[str, Any]], *, source_rel: str, data: dict[str, Any]) -> None:
    if data and not data.get("safe_to_export", False):
        reasons = data.get("blocked_reasons", []) or ["final_export_not_safe"]
        for reason in reasons:
            _add_risk(
                risks,
                severity="blocker",
                category="final_export",
                source_rel=source_rel,
                code=str(reason),
                summary=f"Final export is blocked: `{reason}`",
            )


def _collect_project_state_risks(risks: list[dict[str, Any]], *, source_rel: str, data: dict[str, Any]) -> None:
    if data and data.get("original_tracks_protected") is False:
        _add_risk(risks, severity="blocker", category="project_state", source_rel=source_rel, code="original_tracks_not_protected", summary="Project state does not prove original tracks are protected")
    if data and data.get("master_unchanged") is False:
        _add_risk(risks, severity="blocker", category="project_state", source_rel=source_rel, code="master_mutated", summary="Project state indicates the master may have changed")


def _collect_rollback_risks(risks: list[dict[str, Any]], *, source_rel: str, data: dict[str, Any]) -> None:
    validation = data.get("validation", {}) if data else {}
    if validation and not validation.get("passed", False):
        for failure in validation.get("failures", []) or ["rollback_validation_failed"]:
            _add_risk(risks, severity="blocker", category="rollback", source_rel=source_rel, code=str(failure), summary=f"Rollback validation failed: `{failure}`")


def _collect_package_manifest_risks(risks: list[dict[str, Any]], *, source_rel: str, data: dict[str, Any]) -> None:
    if data and not data.get("package_created", False):
        _add_risk(risks, severity="blocker", category="package", source_rel=source_rel, code="package_created_false", summary="Deliverable package manifest does not show a created ZIP")
    if data and not data.get("zip_path"):
        _add_risk(risks, severity="blocker", category="package", source_rel=source_rel, code="zip_path_missing", summary="Deliverable package manifest has no ZIP path")
    if data and int(data.get("package_size_bytes", 0) or 0) <= 0:
        _add_risk(risks, severity="blocker", category="package", source_rel=source_rel, code="package_size_bytes_missing_or_zero", summary="Deliverable package manifest has no nonzero package size")
    for item in data.get("files_missing", []) or []:
        _add_risk(risks, severity="blocker", category="package", source_rel=source_rel, code=f"files_missing:{item}", summary=f"Deliverable package is missing `{item}`")


def _dedupe_risks(risks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str]] = set()
    out: list[dict[str, Any]] = []
    for risk in sorted(risks, key=lambda item: (_severity_rank(item.get("severity", "")), item.get("category", ""), item.get("source_report", ""), item.get("code", ""))):
        key = (risk.get("severity", ""), risk.get("category", ""), risk.get("source_report", ""), risk.get("code", ""))
        if key in seen:
            continue
        seen.add(key)
        risk["risk_id"] = _risk_id(risk.get("source_report", ""), risk.get("severity", ""), risk.get("code", ""), len(out) + 1)
        out.append(risk)
    return out


def build_open_risk_register(
    *,
    project_name: str,
    output_dir: Path,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    risks: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    missing_reports: list[str] = []
    for spec in REPORTS_TO_SCAN:
        rel = spec["rel"]
        category = spec["category"]
        path = output_dir / rel
        data, error = _load_json(path) if path.exists() and path.suffix.lower() == ".json" else ({}, None)
        reports.append(
            {
                "relative_path": rel,
                "path": str(path),
                "category": category,
                "exists": path.exists(),
                "json_valid": error is None if path.exists() and path.suffix.lower() == ".json" else None,
                "json_error": error,
            }
        )
        if not path.exists():
            missing_reports.append(rel)
            continue
        if error:
            _add_risk(risks, severity="blocker", category=category, source_rel=rel, code=error, summary=f"Report JSON could not be read: `{error}`")
            continue
        _collect_generic_risks(risks, source_rel=rel, category=category, data=data)
        if rel == "eval_reports/real_project_source_safety_map.json":
            _collect_source_safety_risks(risks, source_rel=rel, data=data)
        elif rel == "eval_reports/real_project_plugin_readiness.json":
            _collect_plugin_risks(risks, source_rel=rel, data=data)
        elif rel == "eval_reports/intent_classification.json":
            _collect_intent_risks(risks, source_rel=rel, data=data)
        elif rel == "eval_reports/requirements_traceability_audit.json":
            _collect_requirements_risks(risks, source_rel=rel, data=data)
        elif rel == "export/final_export_state.json":
            _collect_final_state_risks(risks, source_rel=rel, data=data)
        elif rel == "export/project_state_manifest.json":
            _collect_project_state_risks(risks, source_rel=rel, data=data)
        elif rel == "rollback/global_rollback_registry.json":
            _collect_rollback_risks(risks, source_rel=rel, data=data)
        elif rel == "export/deliverable_package_manifest.json":
            _collect_package_manifest_risks(risks, source_rel=rel, data=data)
    risks = _dedupe_risks(risks)
    counts: dict[str, int] = {"blocker": 0, "warning": 0, "review": 0, "info": 0}
    by_category: dict[str, dict[str, int]] = {}
    for risk in risks:
        severity = risk.get("severity", "info")
        counts[severity] = counts.get(severity, 0) + 1
        category = risk.get("category", "other")
        cat = by_category.setdefault(category, {"blocker": 0, "warning": 0, "review": 0, "info": 0})
        cat[severity] = cat.get(severity, 0) + 1
    warnings = [f"missing_optional_report:{rel}" for rel in missing_reports]
    register = {
        "schema": OPEN_RISK_REGISTER_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "risk_counts": counts,
        "risk_counts_by_category": by_category,
        "open_risks": risks,
        "reports_scanned": reports,
        "missing_reports": missing_reports,
        "blockers": [risk["code"] for risk in risks if risk.get("severity") == "blocker"],
        "warnings": warnings,
        "passed": counts.get("blocker", 0) == 0,
        "limits": [
            "The register summarizes report risk evidence; it does not listen to or approve audio.",
            "Final delivery still requires explicit readiness, QC, A/B, rollback, and human approval gates.",
        ],
    }
    target = output_path or output_dir / AUDIT_REL_PATH
    write_json(target, register)
    write_open_risk_register_report(register, output_dir)
    return register


def write_open_risk_register_report(register: dict[str, Any], output_dir: Path) -> Path:
    counts = register.get("risk_counts", {})
    lines = [
        "# Open Risk Register",
        "",
        f"- Project: `{register.get('project_name')}`",
        f"- Created UTC: `{register.get('created_at')}`",
        f"- Passed: `{register.get('passed')}`",
        f"- Blockers: `{counts.get('blocker', 0)}`",
        f"- Warnings: `{counts.get('warning', 0)}`",
        f"- Review items: `{counts.get('review', 0)}`",
        f"- Info items: `{counts.get('info', 0)}`",
        "",
        "This register consolidates report risks and recommended next actions. It does not prove audio quality or user acceptance.",
        "",
        "## Category Counts",
        "",
    ]
    for category, summary in sorted(register.get("risk_counts_by_category", {}).items()):
        lines.append(f"- `{category}` blockers `{summary.get('blocker', 0)}`, warnings `{summary.get('warning', 0)}`, review `{summary.get('review', 0)}`, info `{summary.get('info', 0)}`")
    lines.extend(["", "## Open Risks", ""])
    if not register.get("open_risks"):
        lines.append("- none")
    for risk in register.get("open_risks", []):
        lines.extend(
            [
                f"### {risk.get('risk_id')}",
                "",
                f"- Severity: `{risk.get('severity')}`",
                f"- Category: `{risk.get('category')}`",
                f"- Source report: `{risk.get('source_report')}`",
                f"- Code: `{risk.get('code')}`",
                f"- Summary: {risk.get('summary')}",
                f"- Recommended next action: {risk.get('recommended_next_action')}",
                "",
            ]
        )
    lines.extend(["## Missing Reports", ""])
    lines.extend([f"- `{item}`" for item in register.get("missing_reports", [])] or ["- none"])
    path = Path(output_dir) / AUDIT_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
