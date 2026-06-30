from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.feedback.revision_memory import summarize_feedback_memory
from automix.plugins.plugin_adapter_schema import now_utc, safe_float, write_json


ARTIFACT_SIGNAL_SCHEMA = "automix-artifact-signal-audit-v1"

AUDIT_REL_PATH = Path("eval_reports/artifact_signal_audit.json")
AUDIT_REPORT_REL_PATH = Path("eval_reports/artifact_signal_audit.md")

ARTIFACT_METRIC_PATHS = {
    "final_qc.vocal_preservation.ai_fizz_score": ("eval_reports/final_qc_metrics.json", ("vocal_preservation", "ai_fizz_score")),
    "final_qc.vocal_preservation.metallic_artifact_score": ("eval_reports/final_qc_metrics.json", ("vocal_preservation", "metallic_artifact_score")),
    "final_qc.vocal_preservation.sibilance_splatter_score": ("eval_reports/final_qc_metrics.json", ("vocal_preservation", "sibilance_splatter_score")),
    "premaster.ai_artifact_risk_profile.high_fizz_risk": ("analysis_reports/project_premaster_safety_analysis.json", ("ai_artifact_risk_profile", "high_fizz_risk")),
    "premaster.ai_artifact_risk_profile.metallic_harshness_risk": ("analysis_reports/project_premaster_safety_analysis.json", ("ai_artifact_risk_profile", "metallic_harshness_risk")),
    "premaster.ai_artifact_risk_profile.sibilance_splatter_risk": ("analysis_reports/project_premaster_safety_analysis.json", ("ai_artifact_risk_profile", "sibilance_splatter_risk")),
}

SIGNAL_THRESHOLD = 0.25


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _lookup(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _metric_observations(output_dir: Path) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for metric, (rel, keys) in ARTIFACT_METRIC_PATHS.items():
        path = output_dir / rel
        data = _load_json(path) or {}
        value = _lookup(data, keys)
        source_stage = data.get("input_stage", "")
        report_only = bool(
            data.get("source_mix_path") == ""
            or "missing" in str(source_stage)
            or "missing render" in " ".join(str(item).lower() for item in data.get("warnings", []))
        )
        numeric = safe_float(value, 0.0) if value is not None else 0.0
        observations.append(
            {
                "metric": metric,
                "path": str(path),
                "exists": path.exists(),
                "json_valid": bool(data),
                "value": numeric,
                "above_threshold": numeric >= SIGNAL_THRESHOLD,
                "report_only": report_only,
                "usable_signal": bool(path.exists() and data and numeric >= SIGNAL_THRESHOLD and not report_only),
            }
        )
    return observations


def _source_observations(source_map: dict[str, Any]) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    summary = source_map.get("summary", {})
    for key in ("ai_or_already_processed_vocals", "source_separated_vocals"):
        count = int(summary.get(key, 0) or 0)
        observations.append(
            {
                "signal": key,
                "count": count,
                "usable_signal": count > 0,
                "notes": "Source classification signal only; still requires conservative processing and human review.",
            }
        )
    for group in ("safe_vocal_candidates", "stem_required_tracks", "unknown_tracks", "high_risk_tracks"):
        for track in source_map.get(group, []):
            ai_score = safe_float(track.get("ai_artifact_score"), 0.0)
            source_sep = safe_float(track.get("source_separated_likelihood"), 0.0)
            classification = str(track.get("source_classification", ""))
            usable = ai_score >= SIGNAL_THRESHOLD or source_sep >= SIGNAL_THRESHOLD or classification in {"ai_vocal_stem", "source_separated_vocal"}
            observations.append(
                {
                    "signal": "track_artifact_risk",
                    "track_name": track.get("track_name", ""),
                    "group": group,
                    "source_classification": classification,
                    "ai_artifact_score": ai_score,
                    "source_separated_likelihood": source_sep,
                    "usable_signal": usable,
                    "notes": "Track-level source risk is a planning signal, not cleanup proof.",
                }
            )
    return observations


def _feedback_observation(output_dir: Path) -> dict[str, Any]:
    summary = summarize_feedback_memory(output_dir)
    counts = summary.get("category_counts", {})
    artifact_count = int(counts.get("ai_artifact", 0) or 0)
    return {
        "feedback_memory_exists": bool(summary.get("exists", False)),
        "total_entries": int(summary.get("total_entries", 0) or 0),
        "ai_artifact_feedback_count": artifact_count,
        "pending_unresolved_count": int(summary.get("pending_unresolved_count", 0) or 0),
        "usable_signal": artifact_count > 0,
        "baseline_status": summary.get("baseline_status", ""),
        "no_feedback_fabricated": bool(summary.get("no_feedback_fabricated", False)),
    }


def build_artifact_signal_audit(
    *,
    project_name: str,
    output_dir: Path,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    source_map = _load_json(output_dir / "eval_reports" / "real_project_source_safety_map.json") or {}
    source_observations = _source_observations(source_map)
    metric_observations = _metric_observations(output_dir)
    feedback_observation = _feedback_observation(output_dir)

    usable_source = [item for item in source_observations if item.get("usable_signal")]
    usable_metrics = [item for item in metric_observations if item.get("usable_signal")]
    usable_feedback = feedback_observation.get("usable_signal", False)
    established = bool(usable_source or usable_metrics or usable_feedback)

    blockers: list[str] = []
    if not established:
        blockers.append("artifact_signal_not_established")
    if not usable_metrics:
        blockers.append("measured_artifact_metrics_not_established")

    warnings: list[str] = []
    if not usable_feedback:
        warnings.append("no_user_artifact_feedback_recorded")
    if source_map.get("summary", {}).get("ai_or_already_processed_vocals", 0) == 0 and source_map.get("summary", {}).get("source_separated_vocals", 0) == 0:
        warnings.append("source_map_does_not_classify_ai_or_source_separated_vocals")
    if any(item.get("report_only") for item in metric_observations):
        warnings.append("some_artifact_metric_reports_are_report_only")

    audit = {
        "schema": ARTIFACT_SIGNAL_SCHEMA,
        "project_name": project_name or source_map.get("project_name", ""),
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "artifact_signal_established": established,
        "safe_to_run_artifact_suppression": False,
        "source_observations": source_observations,
        "metric_observations": metric_observations,
        "feedback_observation": feedback_observation,
        "summary": {
            "usable_source_signals": len(usable_source),
            "usable_metric_signals": len(usable_metrics),
            "usable_feedback_signal": bool(usable_feedback),
            "artifact_signal_established": established,
            "safe_to_run_artifact_suppression": False,
        },
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "limits": [
            "This audit does not process audio, reduce artifacts, or prove cleanup.",
            "Artifact-focused processing still requires validated plugin mappings, source safety, loudness-matched A/B, and human review.",
            "Zero or missing metrics are treated as insufficient evidence, not proof that artifacts are absent.",
        ],
    }
    target = output_path or output_dir / AUDIT_REL_PATH
    write_json(target, audit)
    write_artifact_signal_report(audit, output_dir)
    return audit


def write_artifact_signal_report(audit: dict[str, Any], output_dir: Path) -> Path:
    summary = audit.get("summary", {})
    lines = [
        "# Artifact Signal Audit",
        "",
        f"- Project: `{audit.get('project_name')}`",
        f"- Created UTC: `{audit.get('created_at')}`",
        f"- Artifact signal established: `{summary.get('artifact_signal_established', False)}`",
        f"- Safe to run artifact suppression: `{summary.get('safe_to_run_artifact_suppression', False)}`",
        f"- Usable source signals: `{summary.get('usable_source_signals', 0)}`",
        f"- Usable metric signals: `{summary.get('usable_metric_signals', 0)}`",
        f"- Usable feedback signal: `{summary.get('usable_feedback_signal', False)}`",
        "",
        "This report is evidence triage only. It does not claim artifact removal or audio improvement.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in audit.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in audit.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Metric Observations", ""])
    for item in audit.get("metric_observations", []):
        lines.append(
            f"- `{item.get('metric')}` value=`{item.get('value')}` usable=`{item.get('usable_signal')}` report_only=`{item.get('report_only')}`"
        )
    lines.extend(["", "## Feedback Observation", ""])
    feedback = audit.get("feedback_observation", {})
    lines.append(f"- AI artifact feedback count: `{feedback.get('ai_artifact_feedback_count', 0)}`")
    lines.append(f"- Baseline status: `{feedback.get('baseline_status', '')}`")
    lines.extend(["", "## Source Observations", ""])
    for item in audit.get("source_observations", [])[:80]:
        if item.get("signal") == "track_artifact_risk":
            lines.append(
                f"- `{item.get('track_name')}` group=`{item.get('group')}` class=`{item.get('source_classification')}` ai=`{item.get('ai_artifact_score')}` source_sep=`{item.get('source_separated_likelihood')}` usable=`{item.get('usable_signal')}`"
            )
        else:
            lines.append(f"- `{item.get('signal')}` count=`{item.get('count')}` usable=`{item.get('usable_signal')}`")
    path = Path(output_dir) / AUDIT_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
