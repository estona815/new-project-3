from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


RISK_ROOT_CAUSE_ROLLUP_SCHEMA = "automix-risk-root-cause-rollup-v1"

ROLLUP_REL_PATH = Path("eval_reports/risk_root_cause_rollup.json")
ROLLUP_REPORT_REL_PATH = Path("eval_reports/risk_root_cause_rollup.md")


ROOT_CAUSE_RULES: list[dict[str, Any]] = [
    {
        "cause_id": "plugin_validation_not_ready",
        "phase_order": 10,
        "phase": "plugin_safety",
        "title": "Plugin availability and semantic write validation are not ready",
        "needles": ["plugin_semantic", "plugin_validation", "validated_plugin", "safe_draft_plugin", "missing_or_unsafe_plugin", "semantic_validation", "validation_report"],
        "recommended_next_action": "Run plugin preflight and semantic validation, then disable or remap unsafe plugins before any draft processing.",
        "acceptance_criteria": [
            "plugin_validation_preflight has no blockers",
            "plugin_semantic_validation_gate reports ready validation evidence",
            "unsafe or unavailable plugins are disabled or kept manual-review only",
        ],
    },
    {
        "cause_id": "accepted_source_or_stems_missing",
        "phase_order": 20,
        "phase": "source_intake",
        "title": "Accepted export source or required stems are missing",
        "needles": ["source_acceptance", "source_handoff", "stem_required", "stems_not_ready", "full_mix_unsafe", "isolated_stems", "high_risk_track", "no_accepted_export_source", "accepted_export_source", "selected_export_source"],
        "recommended_next_action": "Collect isolated stems or record explicit acceptance for a reviewed export source before final export.",
        "acceptance_criteria": [
            "source_acceptance_gate confirms explicit acceptance for the export source",
            "source_handoff_readiness no longer has open stem requests for automatic processing",
            "full-mix/reference tracks remain manual-review only and outside the premaster path",
        ],
    },
    {
        "cause_id": "artifact_evidence_missing",
        "phase_order": 30,
        "phase": "artifact_evidence",
        "title": "Artifact-focused work lacks source, metric, or feedback evidence",
        "needles": ["artifact_evidence", "artifact_signal", "measured_artifact", "suno_artifact", "ai_artifact"],
        "recommended_next_action": "Collect measured artifact metrics, source signal, or user feedback before artifact-focused processing.",
        "acceptance_criteria": [
            "artifact_signal_audit establishes usable source, metric, or feedback signal",
            "artifact_evidence_gate separates measured evidence from report-only placeholders",
        ],
    },
    {
        "cause_id": "primary_render_missing",
        "phase_order": 40,
        "phase": "render",
        "title": "Primary final WAV render evidence is missing or diagnostic-only",
        "needles": ["primary_wav", "final_render", "render_manifest", "diagnostic/report-only", "render_missing", "render_evidence"],
        "recommended_next_action": "Create a real primary WAV render from the accepted source and rerun final render evidence.",
        "acceptance_criteria": [
            "final_render_manifest contains a nonzero created primary WAV",
            "final_render_evidence_gate is ready for final QC",
            "the render path is not the selected source path and is not diagnostic-only",
        ],
    },
    {
        "cause_id": "final_qc_missing_or_failed",
        "phase_order": 50,
        "phase": "final_qc",
        "title": "Final QC evidence is missing, failed, or not linked to render evidence",
        "needles": ["final_qc", "qc_not_requested", "qc_evidence", "final_audio_path", "true_peak", "digital_black", "clipping", "file_integrity"],
        "recommended_next_action": "Run final QC on the primary WAV and validate QC evidence against render evidence.",
        "acceptance_criteria": [
            "final_qc_metrics has qc_passed true and no failures",
            "final_qc_evidence_gate is ready for delivery QC",
            "QC final_audio_path matches final render evidence primary WAV",
        ],
    },
    {
        "cause_id": "ab_preview_missing_or_not_matched",
        "phase_order": 60,
        "phase": "ab_preview",
        "title": "Loudness-matched A/B preview evidence is missing or invalid",
        "needles": ["ab_preview", "preview_output", "matched_loudness", "loudness_match", "loudness_matched"],
        "recommended_next_action": "Create a measured loudness-matched A/B preview linked to the final render before approval.",
        "acceptance_criteria": [
            "final_ab_preview_manifest has created true and loudness_matched true",
            "ab_preview_evidence_gate is ready for human A/B review",
            "preview source_final matches the primary final WAV",
        ],
    },
    {
        "cause_id": "human_approval_missing",
        "phase_order": 70,
        "phase": "human_review",
        "title": "Final human approval evidence is missing or incomplete",
        "needles": ["human_approval", "final_approval", "approval_evidence", "approval_missing", "reviewed_final", "reviewed_ab_preview"],
        "recommended_next_action": "Record matched-loudness A/B listening approval after QC and preview evidence are ready.",
        "acceptance_criteria": [
            "final_human_approval records accepted decision, reviewer, source, stage, final audio, and preview paths",
            "final_approval_evidence_gate is ready for delivery request",
        ],
    },
    {
        "cause_id": "deliverable_package_missing",
        "phase_order": 80,
        "phase": "package",
        "title": "Deliverable ZIP/package evidence is missing or incomplete",
        "needles": ["deliverable_package", "package_created", "package_size", "zip", "files_missing", "not_listed_in_package_manifest"],
        "recommended_next_action": "Build a real deliverable ZIP after final evidence is ready and validate package evidence.",
        "acceptance_criteria": [
            "deliverable_package_manifest has package_created true and files_missing empty",
            "deliverable_package_evidence_gate confirms ZIP integrity and required evidence files",
            "credential-like and raw/reference paths are excluded by default",
        ],
    },
    {
        "cause_id": "delivery_consistency_not_ready",
        "phase_order": 90,
        "phase": "delivery_consistency",
        "title": "Final delivery reports do not yet prove cross-report consistency",
        "needles": ["final_delivery_consistency", "consistency", "mismatch", "not_listed_in_package_manifest"],
        "recommended_next_action": "Regenerate downstream reports from the accepted source until render, QC, A/B, approval, and package evidence paths agree.",
        "acceptance_criteria": [
            "final_delivery_consistency_gate is ready",
            "final audio path matches render, QC, A/B, approval, and package evidence",
            "A/B preview path matches preview and approval evidence",
        ],
    },
    {
        "cause_id": "rollback_or_project_state_not_ready",
        "phase_order": 100,
        "phase": "rollback",
        "title": "Rollback or project-state protection evidence is incomplete",
        "needles": ["rollback", "project_state", "original_tracks", "master_mutated", "master_unchanged"],
        "recommended_next_action": "Repair rollback registry and project-state manifests before applied-stage or delivery confidence.",
        "acceptance_criteria": [
            "rollback_evidence_gate is ready for delivery readiness",
            "project_state_manifest records original_tracks_protected true and master_unchanged true",
        ],
    },
    {
        "cause_id": "feedback_or_claims_need_review",
        "phase_order": 110,
        "phase": "review_hygiene",
        "title": "Feedback, claim language, or policy evidence still needs review",
        "needles": ["feedback", "claim", "processing_policy", "fixture_coverage", "path_hygiene", "requirements_traceability"],
        "recommended_next_action": "Resolve feedback and static audit blockers without inventing listening approval.",
        "acceptance_criteria": [
            "feedback items are resolved only with measured QC and human review evidence",
            "claim language guard and policy audits have no blockers",
        ],
    },
]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _risk_text(risk: dict[str, Any]) -> str:
    return " ".join(
        str(risk.get(key, ""))
        for key in ("code", "summary", "category", "source_report", "recommended_next_action")
    ).lower()


def _severity_rank(severity: str) -> int:
    return {"blocker": 0, "warning": 1, "review": 2, "info": 3}.get(severity, 9)


def _matches_rule(risk: dict[str, Any], rule: dict[str, Any]) -> bool:
    text = _risk_text(risk)
    return any(str(needle).lower() in text for needle in rule.get("needles", []))


def _select_rule(risk: dict[str, Any]) -> dict[str, Any]:
    for rule in ROOT_CAUSE_RULES:
        if _matches_rule(risk, rule):
            return rule
    return {
        "cause_id": "other_open_risks",
        "phase_order": 999,
        "phase": "other",
        "title": "Other open risks require manual review",
        "recommended_next_action": "Review the source report and choose the safest dry-run or manual-review action.",
        "acceptance_criteria": ["the source report no longer emits this blocker or warning"],
    }


def _build_root_cause(rule: dict[str, Any], risks: list[dict[str, Any]]) -> dict[str, Any]:
    risks = sorted(risks, key=lambda item: (_severity_rank(str(item.get("severity", ""))), str(item.get("code", ""))))
    severities = [str(risk.get("severity", "info")) for risk in risks]
    severity = sorted(set(severities), key=_severity_rank)[0] if severities else "info"
    categories = sorted({str(risk.get("category", "other")) for risk in risks})
    representative_codes = []
    for risk in risks:
        code = str(risk.get("code", ""))
        if code and code not in representative_codes:
            representative_codes.append(code)
        if len(representative_codes) >= 12:
            break
    return {
        "cause_id": rule["cause_id"],
        "phase_order": int(rule["phase_order"]),
        "phase": rule["phase"],
        "title": rule["title"],
        "severity": severity,
        "source_risk_count": len(risks),
        "unique_code_count": len({str(risk.get("code", "")) for risk in risks}),
        "categories": categories,
        "source_risk_ids": [str(risk.get("risk_id")) for risk in risks if risk.get("risk_id")],
        "representative_codes": representative_codes,
        "recommended_next_action": rule["recommended_next_action"],
        "acceptance_criteria": list(rule.get("acceptance_criteria", [])),
    }


def build_risk_root_cause_rollup(
    *,
    project_name: str,
    output_dir: Path,
    register: dict[str, Any] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    register = register or _load_json(output_dir / "eval_reports" / "open_risk_register.json")
    risks = [risk for risk in register.get("open_risks", []) or [] if isinstance(risk, dict)]
    grouped: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {}
    for risk in risks:
        rule = _select_rule(risk)
        grouped.setdefault(rule["cause_id"], (rule, []))[1].append(risk)
    root_causes = [_build_root_cause(rule, group) for rule, group in grouped.values()]
    root_causes = sorted(root_causes, key=lambda item: (_severity_rank(item.get("severity", "")), int(item.get("phase_order", 999)), item.get("cause_id", "")))
    blockers = [cause["cause_id"] for cause in root_causes if cause.get("severity") == "blocker"]
    rollup = {
        "schema": RISK_ROOT_CAUSE_ROLLUP_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "source_register": str(output_dir / "eval_reports" / "open_risk_register.json"),
        "open_risk_total": len(risks),
        "root_cause_total": len(root_causes),
        "root_causes": root_causes,
        "next_root_cause": root_causes[0] if root_causes else {},
        "blockers": blockers,
        "warnings": [] if risks else ["no_open_risks_found"],
        "passed": not blockers,
        "limits": [
            "This rollup compresses risk evidence into root causes; it does not approve audio.",
            "Root-cause grouping is deterministic and conservative, not a substitute for reading the source reports.",
            "Human listening review and measured QC remain required before final delivery.",
        ],
    }
    target = output_path or output_dir / ROLLUP_REL_PATH
    write_json(target, rollup)
    write_risk_root_cause_rollup_report(rollup, output_dir)
    return rollup


def write_risk_root_cause_rollup_report(rollup: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Risk Root Cause Rollup",
        "",
        f"- Project: `{rollup.get('project_name')}`",
        f"- Created UTC: `{rollup.get('created_at')}`",
        f"- Passed: `{rollup.get('passed')}`",
        f"- Open risks: `{rollup.get('open_risk_total')}`",
        f"- Root causes: `{rollup.get('root_cause_total')}`",
        "",
        "This rollup compresses repeated report blockers into root causes. It does not approve audio or replace source reports.",
        "",
        "## Root Causes",
        "",
    ]
    if not rollup.get("root_causes"):
        lines.append("- none")
    for cause in rollup.get("root_causes", []):
        lines.extend(
            [
                f"### {cause.get('phase_order')}. {cause.get('title')}",
                "",
                f"- Cause ID: `{cause.get('cause_id')}`",
                f"- Severity: `{cause.get('severity')}`",
                f"- Phase: `{cause.get('phase')}`",
                f"- Source risks: `{cause.get('source_risk_count')}`",
                f"- Unique codes: `{cause.get('unique_code_count')}`",
                f"- Categories: `{cause.get('categories')}`",
                f"- Recommended next action: {cause.get('recommended_next_action')}",
                "- Representative codes:",
            ]
        )
        lines.extend([f"  - `{code}`" for code in cause.get("representative_codes", [])] or ["  - none"])
        lines.append("- Acceptance criteria:")
        lines.extend([f"  - {item}" for item in cause.get("acceptance_criteria", [])] or ["  - none"])
        lines.append("")
    path = Path(output_dir) / ROLLUP_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
