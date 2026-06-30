from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_THRESHOLDS = {
    "formant_drift_score_reject": 0.35,
    "metallic_increase_score_reject": 0.30,
    "tail_warble_score_reject": 0.25,
    "reverb_tail_pitch_drag_score_reject": 0.25,
    "clarity_loss_db_reject": -1.5,
    "air_loss_db_reject": -2.0,
    "transient_loss_reject": 0.25,
    "stereo_width_change_reject": 0.20,
    "difference_source_energy_reject": 0.35,
}


def load_thresholds(path: Path | None = None) -> dict[str, float]:
    if path is None or not path.exists():
        return dict(DEFAULT_THRESHOLDS)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    out = dict(DEFAULT_THRESHOLDS)
    out.update({key: float(value) for key, value in loaded.items() if isinstance(value, (int, float))})
    return out


def harden_pitch_evaluation(metrics: dict[str, Any], thresholds: dict[str, float] | None = None) -> dict[str, Any]:
    thresholds = thresholds or dict(DEFAULT_THRESHOLDS)
    renders = metrics.setdefault(
        "renders_created",
        {
            "original": False,
            "pitch_processed": False,
            "loudness_matched": False,
            "difference": False,
        },
    )
    warnings = list(metrics.get("warnings", []))
    reason_codes: list[str] = []

    if not all(bool(renders.get(key)) for key in ("original", "pitch_processed", "loudness_matched", "difference")):
        warnings.append("missing_required_render")
        reason_codes.append("MISSING_RENDER")

    if float(metrics.get("formant_drift_score", 0.0)) > thresholds["formant_drift_score_reject"]:
        warnings.append("formant_drift_reject")
        reason_codes.append("FORMANT_DRIFT")
    if float(metrics.get("metallic_increase_score", 0.0)) > thresholds["metallic_increase_score_reject"]:
        warnings.append("metallic_increase_reject")
        reason_codes.append("METALLIC_INCREASE")
    if float(metrics.get("tail_warble_score", 0.0)) > thresholds["tail_warble_score_reject"]:
        warnings.append("tail_warble_reject")
        reason_codes.append("TAIL_WARBLE")
    if float(metrics.get("reverb_tail_pitch_drag_score", 0.0)) > thresholds["reverb_tail_pitch_drag_score_reject"]:
        warnings.append("reverb_tail_pitch_drag_reject")
        reason_codes.append("REVERB_TAIL_PITCH_DRAG")
    if float(metrics.get("clarity_loss_db", 0.0)) < thresholds["clarity_loss_db_reject"]:
        warnings.append("clarity_loss_reject")
        reason_codes.append("CLARITY_LOSS")
    if float(metrics.get("air_loss_db", 0.0)) < thresholds["air_loss_db_reject"]:
        warnings.append("air_loss_reject")
        reason_codes.append("AIR_LOSS")
    if float(metrics.get("transient_loss", 0.0)) > thresholds["transient_loss_reject"]:
        warnings.append("transient_loss_reject")
        reason_codes.append("TRANSIENT_LOSS")
    if float(metrics.get("stereo_width_change", 0.0)) > thresholds["stereo_width_change_reject"]:
        warnings.append("stereo_width_change_reject")
        reason_codes.append("STEREO_WIDTH_CHANGE")
    if float(metrics.get("difference_source_energy", 0.0)) > thresholds["difference_source_energy_reject"]:
        warnings.append("difference_source_energy_reject")
        reason_codes.append("DIFFERENCE_SOURCE_DAMAGE")

    # Pitch improvement alone can never pass when damage metrics fail.
    evaluation_passed = not reason_codes and float(metrics.get("pitch_error_improvement", 0.0)) >= 0.0
    metrics["warnings"] = sorted(set(warnings))
    metrics["reason_codes"] = reason_codes
    metrics["evaluation_passed"] = bool(evaluation_passed)
    metrics["recommended_action"] = "accept_light" if evaluation_passed else "reject_pitch_correction"
    if "MISSING_RENDER" in reason_codes:
        metrics["recommended_action"] = "manual_review_required"
    return metrics


def missing_render_metrics(track_name: str, available_paths: dict[str, str | None] | None = None) -> dict[str, Any]:
    available_paths = available_paths or {}
    metrics = {
        "schema": "automix-pitch-ab-evaluation-v1",
        "track_name": track_name,
        "renders_created": {
            "original": bool(available_paths.get("original")),
            "pitch_processed": bool(available_paths.get("pitch_processed")),
            "loudness_matched": bool(available_paths.get("loudness_matched")),
            "difference": bool(available_paths.get("difference")),
        },
        "pitch_error_improvement": 0.0,
        "formant_drift_score": 0.0,
        "metallic_increase_score": 0.0,
        "clarity_loss_db": 0.0,
        "air_loss_db": 0.0,
        "transient_loss": 0.0,
        "stereo_width_change": 0.0,
        "tail_warble_score": 0.0,
        "side_tail_instability_score": 0.0,
        "reverb_tail_pitch_drag_score": 0.0,
        "difference_source_energy": 0.0,
        "warnings": [],
    }
    return harden_pitch_evaluation(metrics)

