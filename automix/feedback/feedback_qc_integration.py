from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.feedback.revision_memory import load_revision_memory, summarize_feedback_memory
from automix.plugins.plugin_adapter_schema import now_utc, write_json


FEEDBACK_QC_INTEGRATION_SCHEMA = "automix-user-feedback-qc-integration-v1"

INTEGRATION_REL_PATH = Path("eval_reports/user_feedback_qc_integration.json")
INTEGRATION_REPORT_REL_PATH = Path("eval_reports/user_feedback_qc_integration.md")

QC_EVIDENCE_FILES = {
    "final_qc": "eval_reports/final_qc_metrics.json",
    "ab_preview": "eval_reports/final_ab_preview_manifest.json",
    "global_qc": "eval_reports/global_qc_summary.json",
    "translation_check": "eval_reports/project_translation_check.json",
    "premaster_eval": "eval_reports/project_premaster_eval_metrics.json",
    "vocal_placement_eval": "eval_reports/vocal_placement_eval_metrics.json",
    "vocal_recovery_eval": "eval_reports/vocal_recovery_eval_metrics.json",
}

CATEGORY_QC_POINTERS = {
    "vocal_clarity": [
        "final_qc.vocal_preservation.vocal_forwardness_score",
        "final_qc.vocal_preservation.vocal_clarity_score",
        "final_qc.vocal_preservation.vocal_body_score",
        "final_qc.vocal_preservation.vocal_harshness_score",
        "final_qc.translation.small_speaker_vocal_loss_risk",
    ],
    "vocal_presence": [
        "final_qc.vocal_preservation.vocal_forwardness_score",
        "final_qc.vocal_preservation.vocal_clarity_score",
        "final_qc.translation.small_speaker_vocal_loss_risk",
        "final_qc.vocal_preservation.vocal_to_beat_balance",
        "vocal_placement_eval.evaluation_passed",
    ],
    "masking_balance": [
        "final_qc.translation.small_speaker_vocal_loss_risk",
        "vocal_placement_eval.evaluation_passed",
        "translation_check.translation_passed",
    ],
    "sibilance_harshness": [
        "final_qc.vocal_preservation.sibilance_splatter_score",
        "final_qc.vocal_preservation.metallic_artifact_score",
        "final_qc.translation.earbud_harshness_risk",
    ],
    "ai_artifact": [
        "final_qc.vocal_preservation.ai_fizz_score",
        "final_qc.vocal_preservation.metallic_artifact_score",
        "final_qc.translation.phase_correlation",
    ],
    "reverb_delay_space": [
        "final_qc.translation.small_speaker_vocal_loss_risk",
        "ab_preview.loudness_matched",
        "vocal_placement_eval.evaluation_passed",
    ],
    "low_end": [
        "final_qc.translation.low_end_stereo_risk",
        "final_qc.loudness.lra",
        "translation_check.translation_passed",
    ],
    "mastering_dynamics": [
        "final_qc.loudness.integrated_lufs",
        "final_qc.loudness.true_peak_dbTP",
        "final_qc.loudness.lra",
        "premaster_eval.evaluation_passed",
    ],
    "stereo_mono": [
        "final_qc.translation.mono_compatibility_risk",
        "final_qc.translation.phase_correlation",
        "final_qc.translation.low_end_stereo_risk",
    ],
    "tuning_formant": [
        "final_qc.vocal_preservation.vocal_harshness_score",
        "vocal_recovery_eval.evaluation_passed",
    ],
    "female_support_layer": [
        "final_qc.vocal_preservation.vocal_forwardness_score",
        "vocal_placement_eval.evaluation_passed",
    ],
    "general_mix_feedback": [
        "final_qc.qc_passed",
        "global_qc.safe_to_export",
        "ab_preview.loudness_matched",
    ],
}

DEFAULT_REMAINING_RISKS = {
    "vocal_clarity": "Vocal clarity is preference-sensitive and still requires headphone A/B review.",
    "vocal_presence": "Vocal-front placement may need another pass if the lead feels behind the track.",
    "masking_balance": "Instrumental masking can move between sections and should be checked across the full arrangement.",
    "sibilance_harshness": "Harshness reduction can dull consonants if pushed too far.",
    "ai_artifact": "Artifact suppression reduces perceived risk but does not prove total cleanup.",
    "reverb_delay_space": "Space effects may still feel too distant without user listening approval.",
    "low_end": "Low-end translation depends on playback systems and mono fold-down.",
    "mastering_dynamics": "Master dynamics require listening review beyond proxy loudness metrics.",
    "stereo_mono": "Stereo/mono compatibility requires mono playback review.",
    "tuning_formant": "Pitch/formant decisions require human review for emotional tone.",
    "female_support_layer": "Support layers may still compete with the male lead in some phrases.",
    "general_mix_feedback": "Unclassified feedback needs manual triage before processing.",
}


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _lookup(data: dict[str, Any], dotted_path: str) -> Any:
    current: Any = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _load_qc_evidence(output_dir: Path) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for name, rel in QC_EVIDENCE_FILES.items():
        path = output_dir / rel
        data = _load_json(path)
        evidence[name] = {
            "path": str(path),
            "relative_path": rel,
            "exists": path.exists(),
            "json_valid": data is not None if path.suffix.lower() == ".json" else None,
            "data": data or {},
        }
    return evidence


def _resolution_records_by_feedback_id(memory: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    records: dict[str, list[dict[str, Any]]] = {}
    for record in memory.get("resolution_records", []):
        for feedback_id in record.get("feedback_ids", []):
            records.setdefault(str(feedback_id), []).append(record)
    return records


def _feedback_action_plans(entry: dict[str, Any], feedback_id: str) -> list[dict[str, Any]]:
    return [plan for plan in entry.get("action_plans", []) if plan.get("feedback_id") == feedback_id]


def _qc_snapshot(categories: list[str], evidence: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    pointers = sorted({pointer for category in categories for pointer in CATEGORY_QC_POINTERS.get(category, CATEGORY_QC_POINTERS["general_mix_feedback"])})
    snapshot: list[dict[str, Any]] = []
    for pointer in pointers:
        source, _, path = pointer.partition(".")
        source_data = evidence.get(source, {})
        value = _lookup(source_data.get("data", {}), path) if path else None
        snapshot.append(
            {
                "metric": pointer,
                "source_exists": bool(source_data.get("exists")),
                "json_valid": source_data.get("json_valid"),
                "value": value,
                "verified": source_data.get("exists") and source_data.get("json_valid") is not False and value is not None,
            }
        )
    return snapshot


def _before_after_evidence(evidence: dict[str, dict[str, Any]], records: list[dict[str, Any]]) -> dict[str, Any]:
    ab = evidence.get("ab_preview", {}).get("data", {})
    final_qc = evidence.get("final_qc", {}).get("data", {})
    any_accepted = any(record.get("accepted_for_resolution") for record in records)
    any_loudness_matched_review = any(record.get("loudness_matched_ab_reviewed") for record in records)
    return {
        "ab_preview_exists": bool(evidence.get("ab_preview", {}).get("exists")),
        "ab_preview_created": bool(ab.get("created", False)),
        "ab_preview_loudness_matched": bool(ab.get("loudness_matched", False)),
        "human_loudness_matched_ab_review_recorded": bool(any_loudness_matched_review),
        "final_qc_exists": bool(evidence.get("final_qc", {}).get("exists")),
        "final_qc_passed": bool(final_qc.get("qc_passed", False)),
        "resolution_accepted": bool(any_accepted),
        "result_statement": "resolved_with_evidence" if any_accepted else "not_proven_user_review_required",
    }


def build_feedback_qc_integration(
    *,
    project_name: str,
    output_dir: Path,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    memory = load_revision_memory(output_dir, project_name=project_name)
    feedback_summary = summarize_feedback_memory(output_dir)
    qc_evidence = _load_qc_evidence(output_dir)
    records_by_feedback_id = _resolution_records_by_feedback_id(memory)
    resolved_ids = {str(item) for item in memory.get("resolved_feedback_ids", [])}

    items: list[dict[str, Any]] = []
    for entry in memory.get("entries", []):
        for feedback in entry.get("feedback_items", []):
            feedback_id = str(feedback.get("feedback_id", ""))
            categories = [str(item.get("category", "general_mix_feedback")) for item in feedback.get("categories", [])] or ["general_mix_feedback"]
            plans = _feedback_action_plans(entry, feedback_id)
            planned_actions = [action for plan in plans for action in plan.get("planned_actions", [])]
            records = records_by_feedback_id.get(feedback_id, [])
            accepted_records = [record for record in records if record.get("accepted_for_resolution")]
            remaining_risks = sorted(
                {
                    str(risk)
                    for record in records
                    for risk in record.get("remaining_risks", [])
                    if str(risk).strip()
                }
                | {DEFAULT_REMAINING_RISKS.get(category, DEFAULT_REMAINING_RISKS["general_mix_feedback"]) for category in categories}
            )
            qc_snapshot = _qc_snapshot(categories, qc_evidence)
            missing_metrics = [item["metric"] for item in qc_snapshot if not item.get("verified")]
            status = "resolved_with_evidence" if feedback_id in resolved_ids else "unresolved_review_required"
            if records and not accepted_records and feedback_id not in resolved_ids:
                status = "resolution_evidence_incomplete"
            items.append(
                {
                    "feedback_id": feedback_id,
                    "pass_id": entry.get("pass_id", ""),
                    "track_name": entry.get("track_name", ""),
                    "feedback_text": feedback.get("normalized_text", ""),
                    "categories": categories,
                    "cause_hypotheses": sorted({check for action in planned_actions for check in action.get("diagnostic_checks", [])}),
                    "planned_actions": [
                        {
                            "action_id": action.get("action_id", ""),
                            "stage": action.get("stage", ""),
                            "target": action.get("target", ""),
                            "planned_action": action.get("planned_action", ""),
                            "safe_processing_bias": action.get("safe_processing_bias", ""),
                        }
                        for action in planned_actions
                    ],
                    "applied_actions": entry.get("applied_actions", []),
                    "evidence_paths": sorted(
                        {
                            str(path)
                            for path in entry.get("evidence_paths", [])
                            + [path for record in records for path in record.get("evidence_paths", [])]
                            if str(path).strip()
                        }
                    ),
                    "qc_metric_snapshot": qc_snapshot,
                    "missing_qc_metrics": missing_metrics,
                    "before_after_evidence": _before_after_evidence(qc_evidence, records),
                    "remaining_risks": remaining_risks,
                    "resolution_records_count": len(records),
                    "resolution_status": status,
                    "human_review_required": status != "resolved_with_evidence",
                }
            )

    unresolved = [item for item in items if item["resolution_status"] != "resolved_with_evidence"]
    missing_qc_count = sum(1 for item in items if item.get("missing_qc_metrics"))
    integration = {
        "schema": FEEDBACK_QC_INTEGRATION_SCHEMA,
        "project_name": project_name or memory.get("project_name", ""),
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "feedback_summary": feedback_summary,
        "qc_evidence_files": {key: {k: v for k, v in value.items() if k != "data"} for key, value in qc_evidence.items()},
        "items": items,
        "summary": {
            "total_feedback_items": len(items),
            "resolved_with_evidence_count": len(items) - len(unresolved),
            "unresolved_or_incomplete_count": len(unresolved),
            "items_with_missing_qc_metrics": missing_qc_count,
            "requires_human_review": bool(unresolved),
            "dry_run_only_until_resolved": bool(unresolved),
        },
        "warnings": sorted(
            set(feedback_summary.get("warnings", []))
            | ({"feedback_qc_metrics_missing"} if missing_qc_count else set())
            | ({"feedback_resolution_requires_human_review"} if unresolved else set())
        ),
    }
    target = output_path or output_dir / INTEGRATION_REL_PATH
    write_json(target, integration)
    write_feedback_qc_integration_report(integration, output_dir)
    return integration


def write_feedback_qc_integration_report(integration: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# User Feedback QC Integration",
        "",
        f"- Project: `{integration.get('project_name', '')}`",
        f"- Created UTC: `{integration.get('created_at', '')}`",
        "",
        "This report links user feedback to diagnostic hypotheses, dry-run actions, QC evidence, A/B review status, and remaining risk. It does not prove audio improvement by itself.",
        "",
        "## Summary",
        "",
    ]
    summary = integration.get("summary", {})
    for key in ("total_feedback_items", "resolved_with_evidence_count", "unresolved_or_incomplete_count", "items_with_missing_qc_metrics", "requires_human_review"):
        lines.append(f"- {key}: `{summary.get(key)}`")
    feedback_summary = integration.get("feedback_summary", {})
    lines.append(f"- baseline_status: `{feedback_summary.get('baseline_status', '')}`")
    lines.append(f"- no_feedback_fabricated: `{bool(feedback_summary.get('no_feedback_fabricated', False))}`")
    lines.extend(["", "## Feedback Items", ""])
    if not integration.get("items"):
        lines.append("- none recorded; no listening feedback was fabricated for this baseline")
    for item in integration.get("items", []):
        lines.extend(
            [
                f"### {item.get('feedback_id')}",
                "",
                f"- Pass: `{item.get('pass_id')}`",
                f"- Track: `{item.get('track_name') or 'project'}`",
                f"- Feedback: {item.get('feedback_text')}",
                f"- Categories: `{', '.join(item.get('categories', []))}`",
                f"- Resolution: `{item.get('resolution_status')}`",
                f"- Cause hypotheses: `{', '.join(item.get('cause_hypotheses', [])) or 'none'}`",
                "",
                "Planned actions:",
            ]
        )
        for action in item.get("planned_actions", []):
            lines.append(f"- `{action.get('action_id')}`: {action.get('planned_action')}")
        if not item.get("planned_actions"):
            lines.append("- none")
        before_after = item.get("before_after_evidence", {})
        lines.extend(
            [
                "",
                "A/B and QC evidence:",
                f"- A/B preview created: `{before_after.get('ab_preview_created')}`",
                f"- A/B loudness matched: `{before_after.get('ab_preview_loudness_matched')}`",
                f"- Human A/B review recorded: `{before_after.get('human_loudness_matched_ab_review_recorded')}`",
                f"- Final QC passed: `{before_after.get('final_qc_passed')}`",
                f"- Result statement: `{before_after.get('result_statement')}`",
                "",
                "QC snapshot:",
            ]
        )
        for metric in item.get("qc_metric_snapshot", []):
            lines.append(f"- `{metric.get('metric')}` = `{metric.get('value')}` verified=`{metric.get('verified')}`")
        lines.extend(["", "Remaining risks:"])
        lines.extend([f"- {risk}" for risk in item.get("remaining_risks", [])] or ["- none recorded"])
        lines.append("")
    path = Path(output_dir) / INTEGRATION_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
