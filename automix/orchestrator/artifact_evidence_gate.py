from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.feedback.revision_memory import summarize_feedback_memory
from automix.orchestrator.artifact_signal_audit import ARTIFACT_METRIC_PATHS, SIGNAL_THRESHOLD
from automix.plugins.plugin_adapter_schema import now_utc, safe_float, write_json


ARTIFACT_EVIDENCE_SCHEMA = "automix-artifact-evidence-gate-v1"

GATE_REL_PATH = Path("eval_reports/artifact_evidence_gate.json")
GATE_REPORT_REL_PATH = Path("eval_reports/artifact_evidence_gate.md")
TEMPLATE_REL_PATH = Path("review/artifact_evidence_manifest_template.json")
REQUEST_REL_PATH = Path("review/artifact_evidence_request.md")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _lookup(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _is_report_only(data: dict[str, Any]) -> bool:
    warnings = " ".join(str(item).lower() for item in data.get("warnings", []) or [])
    source_stage = str(data.get("input_stage", "")).lower()
    source_path = str(data.get("source_mix_path", "") or data.get("source_audio_path", "") or data.get("render_path", ""))
    return bool(
        source_path == ""
        or "missing" in source_stage
        or "missing render" in warnings
        or data.get("report_only") is True
        or data.get("diagnostic_only") is True
    )


def _metric_candidates(output_dir: Path) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for metric, (rel, keys) in ARTIFACT_METRIC_PATHS.items():
        path = output_dir / rel
        data = _load_json(path)
        raw = _lookup(data, keys) if data else None
        value = safe_float(raw, 0.0) if raw is not None else 0.0
        report_only = _is_report_only(data) if data else False
        passed = bool(path.exists() and data and value >= SIGNAL_THRESHOLD and not report_only)
        blockers: list[str] = []
        warnings: list[str] = []
        if not path.exists():
            blockers.append("artifact_metric_report_missing")
        elif not data:
            blockers.append("artifact_metric_report_invalid_json")
        elif value < SIGNAL_THRESHOLD:
            blockers.append("artifact_metric_below_threshold")
        if report_only:
            blockers.append("artifact_metric_report_only")
            warnings.append("metric_exists_but_not_from_measured_render")
        candidates.append(
            {
                "evidence_type": "measured_metric",
                "metric": metric,
                "path": str(path),
                "value": value,
                "threshold": SIGNAL_THRESHOLD,
                "report_only": report_only,
                "passed": passed,
                "blockers": sorted(set(blockers)),
                "warnings": sorted(set(warnings)),
            }
        )
    return candidates


def _source_candidates(output_dir: Path) -> list[dict[str, Any]]:
    source_map = _load_json(output_dir / "eval_reports/real_project_source_safety_map.json")
    candidates: list[dict[str, Any]] = []
    summary = source_map.get("summary", {}) if source_map else {}
    for signal in ("ai_or_already_processed_vocals", "source_separated_vocals"):
        count = int(summary.get(signal, 0) or 0)
        candidates.append(
            {
                "evidence_type": "source_classification",
                "signal": signal,
                "count": count,
                "passed": count > 0,
                "blockers": [] if count > 0 else [f"{signal}_not_present"],
                "warnings": ["source_signal_is_planning_evidence_not_metric"] if count > 0 else [],
            }
        )
    for group in ("safe_vocal_candidates", "stem_required_tracks", "unknown_tracks", "high_risk_tracks"):
        for track in source_map.get(group, []) or []:
            if not isinstance(track, dict):
                continue
            ai_score = safe_float(track.get("ai_artifact_score"), 0.0)
            source_sep = safe_float(track.get("source_separated_likelihood"), 0.0)
            classification = str(track.get("source_classification", ""))
            passed = bool(ai_score >= SIGNAL_THRESHOLD or source_sep >= SIGNAL_THRESHOLD or classification in {"ai_vocal_stem", "source_separated_vocal"})
            candidates.append(
                {
                    "evidence_type": "source_classification",
                    "signal": "track_artifact_risk",
                    "track_name": track.get("track_name", ""),
                    "group": group,
                    "source_classification": classification,
                    "ai_artifact_score": ai_score,
                    "source_separated_likelihood": source_sep,
                    "passed": passed,
                    "blockers": [] if passed else ["track_artifact_signal_below_threshold"],
                    "warnings": ["track_source_signal_requires_metric_and_ab_review"] if passed else [],
                }
            )
    return candidates


def _feedback_candidate(output_dir: Path) -> dict[str, Any]:
    summary = summarize_feedback_memory(output_dir)
    counts = summary.get("category_counts", {}) if isinstance(summary.get("category_counts", {}), dict) else {}
    artifact_count = int(counts.get("ai_artifact", 0) or 0)
    fabricated = bool(summary.get("no_feedback_fabricated", False)) and int(summary.get("total_entries", 0) or 0) == 0
    passed = bool(artifact_count > 0 and not fabricated)
    blockers: list[str] = []
    if artifact_count <= 0:
        blockers.append("user_artifact_feedback_missing")
    if fabricated:
        blockers.append("feedback_baseline_is_not_user_evidence")
    return {
        "evidence_type": "user_feedback",
        "feedback_memory_exists": bool(summary.get("exists", False)),
        "total_entries": int(summary.get("total_entries", 0) or 0),
        "ai_artifact_feedback_count": artifact_count,
        "pending_unresolved_count": int(summary.get("pending_unresolved_count", 0) or 0),
        "baseline_status": summary.get("baseline_status", ""),
        "no_feedback_fabricated": bool(summary.get("no_feedback_fabricated", False)),
        "passed": passed,
        "blockers": sorted(set(blockers)),
        "warnings": ["user_feedback_requires_qc_and_loudness_matched_ab_resolution"] if passed else [],
    }


def _manifest_candidates(manifest_path: Path | None) -> list[dict[str, Any]]:
    if not manifest_path:
        return []
    manifest = _load_json(Path(manifest_path))
    candidates = manifest.get("artifact_evidence", []) if manifest else []
    if isinstance(candidates, list):
        return [item for item in candidates if isinstance(item, dict)]
    return []


def _manifest_result(candidate: dict[str, Any]) -> dict[str, Any]:
    evidence_type = str(candidate.get("evidence_type", "manual"))
    human_reviewed = bool(candidate.get("human_reviewed", False))
    evidence_path = str(candidate.get("evidence_path", ""))
    value = safe_float(candidate.get("value"), 0.0)
    blockers: list[str] = []
    warnings: list[str] = []
    if not evidence_path:
        blockers.append("artifact_evidence_path_missing")
    elif not Path(evidence_path).exists():
        blockers.append("artifact_evidence_file_missing")
    if evidence_type == "measured_metric" and value < SIGNAL_THRESHOLD:
        blockers.append("artifact_metric_below_threshold")
    if not human_reviewed:
        warnings.append("artifact_evidence_not_human_reviewed")
    passed = not blockers
    return {
        "evidence_type": evidence_type,
        "label": candidate.get("label", ""),
        "evidence_path": evidence_path,
        "value": value,
        "human_reviewed": human_reviewed,
        "passed": passed,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "notes": candidate.get("notes", ""),
    }


def _template() -> dict[str, Any]:
    return {
        "schema": "automix-artifact-evidence-manifest-template-v1",
        "artifact_evidence": [
            {
                "label": "measured_final_qc_ai_fizz",
                "evidence_type": "measured_metric",
                "evidence_path": "automix/eval_reports/final_qc_metrics.json",
                "metric_key": "vocal_preservation.ai_fizz_score",
                "value": 0.0,
                "human_reviewed": False,
                "notes": "Use only after a real render/QC report exists; report-only placeholders do not count.",
            },
            {
                "label": "user_artifact_feedback",
                "evidence_type": "user_feedback",
                "evidence_path": "automix/review/user_feedback_revision_memory.json",
                "value": 1.0,
                "human_reviewed": True,
                "notes": "Use only for actual user listening feedback, not a no-feedback baseline.",
            },
        ],
        "limits": [
            "Do not use zero or missing metrics as proof artifacts are absent.",
            "Do not claim total artifact removal.",
            "Artifact evidence is planning evidence; source, plugin, A/B, and approval gates still apply.",
        ],
    }


def build_artifact_evidence_gate(
    *,
    project_name: str,
    output_dir: Path,
    manifest_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    metric_candidates = _metric_candidates(output_dir)
    source_candidates = _source_candidates(output_dir)
    feedback_candidate = _feedback_candidate(output_dir)
    manifest_results = [_manifest_result(item) for item in _manifest_candidates(manifest_path)]

    passed_metrics = [item for item in metric_candidates + manifest_results if item.get("evidence_type") == "measured_metric" and item.get("passed")]
    passed_sources = [item for item in source_candidates + manifest_results if item.get("evidence_type") == "source_classification" and item.get("passed")]
    passed_feedback = [feedback_candidate] if feedback_candidate.get("passed") else []
    passed_feedback.extend(item for item in manifest_results if item.get("evidence_type") == "user_feedback" and item.get("passed"))
    artifact_established = bool(passed_metrics or passed_sources or passed_feedback)
    measured_metrics_established = bool(passed_metrics)

    blockers: list[str] = []
    warnings: list[str] = []
    if not artifact_established:
        blockers.append("artifact_evidence_not_established")
    if not measured_metrics_established:
        blockers.append("measured_artifact_metrics_missing")
    for item in manifest_results:
        blockers.extend(f"manifest:{blocker}" for blocker in item.get("blockers", []))
        warnings.extend(f"manifest:{warning}" for warning in item.get("warnings", []))
    for item in metric_candidates:
        if "artifact_metric_report_only" in item.get("blockers", []):
            warnings.append(f"report_only_metric:{item.get('metric')}")
    if feedback_candidate.get("blockers"):
        warnings.extend(f"feedback:{item}" for item in feedback_candidate.get("blockers", []))

    template_path = output_dir / TEMPLATE_REL_PATH
    write_json(template_path, _template())
    gate = {
        "schema": ARTIFACT_EVIDENCE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "manifest_path": str(manifest_path or ""),
        "artifact_evidence_established": artifact_established,
        "measured_artifact_metrics_established": measured_metrics_established,
        "ready_for_artifact_review": bool(artifact_established and measured_metrics_established),
        "safe_to_run_artifact_suppression": False,
        "metric_candidates": metric_candidates,
        "source_candidates": source_candidates,
        "feedback_candidate": feedback_candidate,
        "manifest_results": manifest_results,
        "summary": {
            "passed_metric_evidence": len(passed_metrics),
            "passed_source_evidence": len(passed_sources),
            "passed_feedback_evidence": len(passed_feedback),
            "artifact_evidence_established": artifact_established,
            "measured_artifact_metrics_established": measured_metrics_established,
            "ready_for_artifact_review": bool(artifact_established and measured_metrics_established),
        },
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "template_path": str(template_path),
        "limits": [
            "This gate validates artifact evidence only; it does not process audio or claim cleanup.",
            "Measured metrics must come from real render/QC reports, not report-only placeholders.",
            "Human A/B review and plugin/source gates remain required before artifact suppression.",
        ],
    }
    target = output_path or output_dir / GATE_REL_PATH
    write_json(target, gate)
    write_artifact_evidence_report(gate, output_dir)
    write_artifact_evidence_request(gate, output_dir)
    return gate


def write_artifact_evidence_report(gate: dict[str, Any], output_dir: Path) -> Path:
    summary = gate.get("summary", {})
    lines = [
        "# Artifact Evidence Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Artifact evidence established: `{gate.get('artifact_evidence_established')}`",
        f"- Measured metrics established: `{gate.get('measured_artifact_metrics_established')}`",
        f"- Ready for artifact review: `{gate.get('ready_for_artifact_review')}`",
        f"- Safe to run artifact suppression: `{gate.get('safe_to_run_artifact_suppression')}`",
        f"- Passed metric evidence: `{summary.get('passed_metric_evidence', 0)}`",
        f"- Passed source evidence: `{summary.get('passed_source_evidence', 0)}`",
        f"- Passed feedback evidence: `{summary.get('passed_feedback_evidence', 0)}`",
        "",
        "This gate does not claim artifact removal or audio improvement.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in gate.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Metric Candidates", ""])
    for item in gate.get("metric_candidates", []):
        lines.append(f"- `{item.get('metric')}` value=`{item.get('value')}` passed=`{item.get('passed')}` report_only=`{item.get('report_only')}`")
    lines.extend(["", "## Feedback Candidate", ""])
    feedback = gate.get("feedback_candidate", {})
    lines.append(f"- AI artifact feedback count: `{feedback.get('ai_artifact_feedback_count', 0)}`")
    lines.append(f"- Passed: `{feedback.get('passed')}`")
    path = Path(output_dir) / GATE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_artifact_evidence_request(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Artifact Evidence Request",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Template: `{gate.get('template_path')}`",
        "",
        "Needed before artifact-focused processing:",
        "",
        "- Real render/QC metrics showing artifact risk above threshold.",
        "- Or actual user listening feedback about AI fizz, watery smear, metallic edge, or similar artifact.",
        "- Or source classification showing AI/source-separated vocal risk, followed by measured QC before acceptance.",
        "",
        "Current blockers:",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    path = Path(output_dir) / REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
