from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .audio_qc import compare_before_after
    from .qc_thresholds import audio_qc_profile, load_profile, thresholds_for
    from .severity import (
        Finding,
        add_finding,
        findings_to_dicts,
        findings_to_markdown,
        has_warn_plus,
        max_severity,
        warn_plus_findings,
    )
except ImportError:  # pragma: no cover - direct script execution.
    from audio_qc import compare_before_after
    from qc_thresholds import audio_qc_profile, load_profile, thresholds_for
    from severity import (
        Finding,
        add_finding,
        findings_to_dicts,
        findings_to_markdown,
        has_warn_plus,
        max_severity,
        warn_plus_findings,
    )


RESONANCE_WORDS = ("resonance", "ring", "ringing", "whistle", "metallic", "nasal", "box", "harsh", "shard")
TRUE_REBEAT_CLAIMS = ("true_rebeat", "true rebeat", "beat fully re-created", "beat fully recreated")
LOSSLESS_CLAIMS = ("lossless restoration", "true original-resolution master", "original resolution master")
VOCAL_TUNE_CLAIMS = ("vocal fully tuned", "vocal tuned", "pitch corrected", "pitch_correction")
PITCH_NEGATIONS = ("pitch correction unavailable", "pitch correction not performed", "no pitch correction", "not pitch corrected")
STEM_CLAIMS = ("stem mix", "stem_mix", "stem rebuild", "stem_rebuild", "stem-assisted rebuild")
REFERENCE_PERFECT_CLAIMS = ("reference matched perfectly", "perfect reference match")
NOISE_REMOVED_CLAIMS = ("noise completely removed", "perfectly removed", "fully removed noise")
PRO_FINAL_CLAIMS = ("professional final master", "commercial final master")


def _read_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True)


def _claim_blob(report: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("claim", "claims", "claim_text", "final_claim", "summary", "selected_claim", "allowed_claims"):
        if key in report:
            parts.append(_as_text(report.get(key)))
    return " ".join(parts).lower()


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _nested(report: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = report
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _comparison_from_report(report: dict[str, Any]) -> dict[str, Any]:
    metrics = report.get("metrics") or report.get("qc_metrics") or {}
    if not isinstance(metrics, dict):
        return {"before": {}, "after": {}, "delta": {}}
    return {
        "before": metrics.get("before", {}) if isinstance(metrics.get("before", {}), dict) else {},
        "after": metrics.get("after", {}) if isinstance(metrics.get("after", {}), dict) else {},
        "delta": metrics.get("delta", {}) if isinstance(metrics.get("delta", {}), dict) else {},
    }


def _merge_comparison(primary: dict[str, Any] | None, fallback: dict[str, Any]) -> dict[str, Any]:
    merged = primary or {"before": {}, "after": {}, "delta": {}}
    for section in ("before", "after", "delta"):
        merged.setdefault(section, {})
        for key, value in fallback.get(section, {}).items():
            merged[section].setdefault(key, value)
    return merged


def _delta(comparison: dict[str, Any], key: str) -> float | None:
    value = comparison.get("delta", {}).get(key)
    if value is None:
        return None
    return _number(value)


def _after(comparison: dict[str, Any], key: str) -> float | None:
    value = comparison.get("after", {}).get(key)
    if value is None:
        return None
    return _number(value)


def _role_set(raw_roles: list[Any]) -> set[str]:
    roles = set()
    for item in raw_roles:
        text = _as_text(item).lower()
        if "drum" in text or "kick" in text or "snare" in text:
            roles.add("drums")
        if "bass" in text or "808" in text:
            roles.add("bass")
        if "music" in text or "instrument" in text or "synth" in text or "keys" in text or "guitar" in text:
            roles.add("music")
        if "vocal" in text:
            roles.add("vocal")
    return roles


def _stem_roles(report: dict[str, Any]) -> set[str]:
    evidence = report.get("evidence", {}) if isinstance(report.get("evidence", {}), dict) else {}
    raw_roles = []
    raw_roles.extend(_as_list(report.get("stem_roles")))
    raw_roles.extend(_as_list(evidence.get("stem_roles")))
    raw_roles.extend(_as_list(report.get("available_stems")))
    raw_roles.extend(_as_list(evidence.get("available_stems")))
    return _role_set(raw_roles)


def _rebuild_roles(report: dict[str, Any]) -> set[str]:
    evidence = report.get("evidence", {}) if isinstance(report.get("evidence", {}), dict) else {}
    raw_roles = []
    for key in (
        "rebuild_roles",
        "midi_roles",
        "audio_rebuild_roles",
        "reconstructed_roles",
        "timeline_rebuild_roles",
    ):
        raw_roles.extend(_as_list(report.get(key)))
        raw_roles.extend(_as_list(evidence.get(key)))
    return _role_set(raw_roles)


def _evidence_count(report: dict[str, Any], *names: str) -> int:
    evidence = report.get("evidence", {}) if isinstance(report.get("evidence", {}), dict) else {}
    for name in names:
        value = report.get(name, evidence.get(name))
        if value is not None:
            return int(_number(value))
    return 0


def _source_is_lossy(report: dict[str, Any]) -> bool:
    source_format = _as_text(report.get("source_format") or _nested(report, "source", "format")).lower()
    return _boolish(report.get("source_is_lossy") or _nested(report, "source", "lossy")) or source_format in {
        "mp3",
        "aac",
        "m4a",
        "ogg",
        "opus",
        "lossy",
    }


def _check_metric_thresholds(
    comparison: dict[str, Any],
    thresholds: dict[str, Any],
    findings: list[Finding],
    after_path: str = "",
) -> None:
    brightness_delta = _delta(comparison, "air_fizz_band_db")
    if brightness_delta is not None:
        if brightness_delta <= -_number(thresholds["brightness_loss_fail_db"]):
            add_finding(
                "FAIL",
                "BRIGHTNESS_LOSS_EXCESSIVE",
                "Air/fizz brightness dropped beyond the fail guard.",
                f"air_fizz_delta_db={brightness_delta:.2f}, fail={thresholds['brightness_loss_fail_db']:.2f}",
                "Reduce DeAI, de-essing, high-shelf, or side-air reduction; render a safer candidate and rerun the checker.",
                findings,
                affected_file=after_path,
                failed_assumption="Cleanup preserved brightness and vocal/air clarity.",
                command_to_rerun="python3 harness/engineering_rule_checker.py --before BEFORE.wav --after AFTER.wav --profile PROFILE.json --processing-report REPORT.json --out-json rule_check.json --out-md rule_check.md",
                human_listening_required=True,
            )
        elif brightness_delta <= -_number(thresholds["brightness_loss_warn_db"]):
            add_finding(
                "WARN",
                "BRIGHTNESS_LOSS_WARN",
                "Air/fizz brightness dropped beyond the warn guard.",
                f"air_fizz_delta_db={brightness_delta:.2f}, warn={thresholds['brightness_loss_warn_db']:.2f}",
                "A/B a lighter DeAI or de-esser candidate and document whether artifact reduction justifies the loss.",
                findings,
                affected_file=after_path,
                failed_assumption="Top-end cleanup did not dull the track.",
                human_listening_required=True,
            )

    transient_ratio = _delta(comparison, "transient_ratio")
    if transient_ratio is not None:
        if transient_ratio < _number(thresholds["transient_loss_fail_ratio"]):
            add_finding(
                "FAIL",
                "TRANSIENT_LOSS_EXCESSIVE",
                "Transient proxy fell beyond the fail guard.",
                f"transient_ratio={transient_ratio:.3f}, fail={thresholds['transient_loss_fail_ratio']:.3f}",
                "Back off compression, limiting, DeAI, or smoothing; render a punch-preserve candidate.",
                findings,
                affected_file=after_path,
                failed_assumption="Processing preserved transient punch.",
                human_listening_required=True,
            )
        elif transient_ratio < _number(thresholds["transient_loss_warn_ratio"]):
            add_finding(
                "WARN",
                "TRANSIENT_LOSS_WARN",
                "Transient proxy fell beyond the warn guard.",
                f"transient_ratio={transient_ratio:.3f}, warn={thresholds['transient_loss_warn_ratio']:.3f}",
                "Compare against a less compressed/less cleaned candidate before selecting a final.",
                findings,
                affected_file=after_path,
                failed_assumption="Processing preserved attack detail.",
                human_listening_required=True,
            )

    side_mid_delta = _delta(comparison, "side_mid_ratio_db")
    if side_mid_delta is not None:
        if abs(side_mid_delta) > _number(thresholds["side_mid_change_fail_db"]):
            add_finding(
                "FAIL",
                "STEREO_WIDTH_COLLAPSE_OR_INSTABILITY",
                "Side/mid ratio changed beyond the fail guard.",
                f"side_mid_delta_db={side_mid_delta:.2f}, fail={thresholds['side_mid_change_fail_db']:.2f}",
                "Audit M/S EQ, stereo DeAI, wideners, and side-only filters; rerender with safer width preservation.",
                findings,
                affected_file=after_path,
                failed_assumption="M/S processing preserved stereo intent.",
                human_listening_required=True,
            )
        elif abs(side_mid_delta) > _number(thresholds["side_mid_change_warn_db"]):
            add_finding(
                "WARN",
                "SIDE_MID_CHANGE_WARN",
                "Side/mid ratio changed beyond the warn guard.",
                f"side_mid_delta_db={side_mid_delta:.2f}, warn={thresholds['side_mid_change_warn_db']:.2f}",
                "Document the M/S reason and run mono/stereo listening before final selection.",
                findings,
                affected_file=after_path,
                failed_assumption="Stereo change was intentional and safe.",
                human_listening_required=True,
            )

    punch_delta = _delta(comparison, "low_band_energy_db")
    if punch_delta is not None:
        if punch_delta <= -_number(thresholds["punch_loss_fail_db"]):
            add_finding(
                "FAIL",
                "PUNCH_LOSS_EXCESSIVE",
                "Bass/punch proxy fell beyond the fail guard.",
                f"low_band_delta_db={punch_delta:.2f}, fail={thresholds['punch_loss_fail_db']:.2f}",
                "Restore 45-140 Hz punch, reduce limiter drive, or use a punch-preserve candidate.",
                findings,
                affected_file=after_path,
                failed_assumption="Processing preserved kick/bass weight.",
                human_listening_required=True,
            )
        elif punch_delta <= -_number(thresholds["punch_loss_warn_db"]):
            add_finding(
                "WARN",
                "PUNCH_LOSS_WARN",
                "Bass/punch proxy fell beyond the warn guard.",
                f"low_band_delta_db={punch_delta:.2f}, warn={thresholds['punch_loss_warn_db']:.2f}",
                "A/B against the punch-preserve candidate and check limiter/sub-side decisions.",
                findings,
                affected_file=after_path,
                failed_assumption="Punch was not sacrificed for cleanup.",
                human_listening_required=True,
            )

    true_peak = _after(comparison, "approx_true_peak_dbfs")
    if true_peak is not None and true_peak > _number(thresholds["true_peak_target_dbfs"]):
        add_finding(
            "FAIL",
            "TRUE_PEAK_RULE_FAIL",
            "Output exceeds the engineering true-peak target.",
            f"approx_true_peak_dbfs={true_peak:.2f}, target={thresholds['true_peak_target_dbfs']:.2f}",
            "Lower limiter ceiling/output gain and rerun render plus QC.",
            findings,
            affected_file=after_path,
            failed_assumption="Master safety overrides loudness and reference matching.",
            human_listening_required=True,
        )


def _check_claims(report: dict[str, Any], findings: list[Finding], processing_report_path: str = "") -> None:
    blob = _claim_blob(report)
    mode = _as_text(report.get("mode") or report.get("classification")).lower()
    stem_roles = _stem_roles(report)
    rebuild_roles = _rebuild_roles(report)
    midi_count = _evidence_count(report, "midi_item_count", "midi_items")
    rebuild_audio_count = _evidence_count(report, "rebuild_audio_item_count", "audio_rebuild_item_count")
    has_rebuild_items = midi_count > 0 or rebuild_audio_count > 0
    has_true_rebeat_roles = {"drums", "bass", "music"}.issubset(rebuild_roles)

    if _contains_any(blob, TRUE_REBEAT_CLAIMS) or mode == "true_rebeat":
        if not (has_rebuild_items and has_true_rebeat_roles):
            add_finding(
                "FAIL",
                "TRUE_REBEAT_CLAIM_UNSUPPORTED",
                "A true rebeat claim lacks MIDI/audio reconstruction and drum/bass/music evidence.",
                f"midi_items={midi_count}, rebuild_audio_items={rebuild_audio_count}, rebuild_roles={sorted(rebuild_roles)}, stem_roles={sorted(stem_roles)}",
                "Downgrade the claim to fullmix rescue or drum reinforcement, or add auditable MIDI/audio reconstruction and rerun RPP audit.",
                findings,
                affected_file=processing_report_path,
                failed_assumption="True rebeat evidence exists in the REAPER timeline.",
                command_to_rerun="python3 harness/reaper_project_audit.py --rpp PATH_TO_PROJECT.rpp --out reports/rpp_audit.json",
                human_listening_required=True,
            )

    if _source_is_lossy(report) and _contains_any(blob, LOSSLESS_CLAIMS):
        add_finding(
            "FAIL",
            "LOSSY_SOURCE_FALSE_LOSSLESS_CLAIM",
            "A lossy source was described as lossless restoration.",
            f"source_format={report.get('source_format') or _nested(report, 'source', 'format')}",
            "Use exact language: Source was lossy MP3. Output is improved processing/mastering, not true lossless restoration.",
            findings,
            affected_file=processing_report_path,
            failed_assumption="MP3-derived WAV can be described as lossless restoration.",
            human_listening_required=False,
        )

    if _contains_any(blob, STEM_CLAIMS) and not stem_roles:
        add_finding(
            "FAIL",
            "STEM_CLAIM_WITHOUT_STEMS",
            "A stem mix/rebuild claim has no stem role evidence.",
            "available_stems/stem_roles are empty.",
            "Downgrade to fullmix rescue or import/audit active stems before using stem language.",
            findings,
            affected_file=processing_report_path,
            failed_assumption="Stem tracks exist and are active.",
            command_to_rerun="python3 harness/reaper_project_audit.py --rpp PATH_TO_PROJECT.rpp --out reports/rpp_audit.json",
            human_listening_required=False,
        )

    pitch = report.get("pitch_correction", {}) if isinstance(report.get("pitch_correction", {}), dict) else {}
    if _contains_any(blob, VOCAL_TUNE_CLAIMS) and not _contains_any(blob, PITCH_NEGATIONS) and not _boolish(
        pitch.get("validated") or pitch.get("edit_evidence")
    ):
        add_finding(
            "FAIL",
            "VOCAL_TUNING_CLAIM_UNSUPPORTED",
            "A vocal tuning/pitch correction claim lacks pitch contour, edit evidence, or validation.",
            json.dumps(pitch, sort_keys=True),
            "Remove the tuning claim or run an auditable pitch-correction workflow with before/after validation.",
            findings,
            affected_file=processing_report_path,
            failed_assumption="Pitch/timing correction evidence exists.",
            human_listening_required=True,
        )

    if _contains_any(blob, NOISE_REMOVED_CLAIMS):
        add_finding(
            "WARN",
            "ABSOLUTE_NOISE_REMOVAL_CLAIM",
            "The report uses absolute noise-removal language.",
            "Noise/artifact reduction can be measured, but complete removal was claimed.",
            "Replace with measured reduction language and note remaining artifact risk.",
            findings,
            affected_file=processing_report_path,
            failed_assumption="Noise can be claimed completely removed by automation.",
            human_listening_required=True,
        )

    if _contains_any(blob, PRO_FINAL_CLAIMS) and not _boolish(report.get("human_listening_approved")):
        add_finding(
            "WARN",
            "PRO_FINAL_MASTER_CLAIM_REQUIRES_LISTENING",
            "A professional final master claim lacks human listening approval.",
            "human_listening_approved is not true.",
            "Downgrade to candidate/processed print until QC passes and the user accepts the listening tradeoff.",
            findings,
            affected_file=processing_report_path,
            failed_assumption="Automation alone can certify professional final mastering.",
            human_listening_required=True,
        )

    if _contains_any(blob, REFERENCE_PERFECT_CLAIMS):
        add_finding(
            "WARN",
            "PERFECT_REFERENCE_MATCH_CLAIM",
            "Reference matching was described as perfect.",
            "Reference matching is advisory and cannot prove identical musical quality.",
            "Use reference-guided language and list accepted/rejected reference deltas.",
            findings,
            affected_file=processing_report_path,
            failed_assumption="A reference can be perfectly matched by automation.",
            human_listening_required=True,
        )


def _move_missing_fields(move: dict[str, Any], required: tuple[str, ...]) -> list[str]:
    return [field for field in required if move.get(field) in (None, "", [])]


def _move_category(move: dict[str, Any]) -> str:
    return _as_text(move.get("category") or move.get("type") or move.get("processor") or move.get("kind")).lower()


def _check_processing_moves(
    report: dict[str, Any],
    comparison: dict[str, Any],
    profile: dict[str, Any],
    thresholds: dict[str, Any],
    findings: list[Finding],
    processing_report_path: str = "",
) -> None:
    moves = []
    for key in ("processing_moves", "moves", "eq_moves", "ms_moves", "dynamic_eq_bands", "compression_moves", "deesser_moves"):
        raw = report.get(key)
        if isinstance(raw, list):
            moves.extend(raw)

    allowed_ms_reasons = {reason.lower() for reason in profile.get("allowed_ms_reasons", [])}

    for index, move_raw in enumerate(moves):
        if not isinstance(move_raw, dict):
            continue
        move = move_raw
        category = _move_category(move)
        problem_text = _as_text(move.get("problem") or move.get("target_problem") or move.get("reason")).lower()

        if category in {"eq", "resonance", "resonance_control", "dynamic_notch"}:
            eq_type = _as_text(move.get("eq_type") or move.get("shape") or move.get("filter_type")).lower()
            q_value = _number(move.get("q") or move.get("q_estimate"), default=0.0)
            broad = "broad" in eq_type or eq_type in {"high_shelf", "low_shelf", "tilt", "wide_cut"}
            narrow_problem = _contains_any(problem_text, RESONANCE_WORDS)
            if narrow_problem and (broad or q_value < _number(thresholds["resonance_min_q"])):
                add_finding(
                    "WARN",
                    "BROAD_EQ_USED_FOR_RESONANCE",
                    "A narrow resonance problem was treated with broad or low-Q EQ.",
                    f"move_index={index}, eq_type={eq_type}, q={q_value}, problem={problem_text}",
                    "Use a high-Q or dynamic notch first, then rerun QC and document exact frequency/Q.",
                    findings,
                    affected_file=processing_report_path,
                    failed_assumption="Broad EQ is acceptable resonance control.",
                    human_listening_required=True,
                )

        if category in {"ms_eq", "m/s eq", "mid_side_eq", "mid-side eq"} or _as_text(move.get("domain")).lower() in {"ms", "mid_side", "mid-side"}:
            missing = _move_missing_fields(move, ("band", "target", "static_or_dynamic", "amount_db", "reason", "risk"))
            if missing:
                add_finding(
                    "WARN",
                    "MS_EQ_REPORT_FIELDS_MISSING",
                    "An M/S EQ move is missing required audit fields.",
                    f"move_index={index}, missing={missing}",
                    "Report band, Mid/Side target, static/dynamic behavior, dB amount, reason, risk, and side/mid metric.",
                    findings,
                    affected_file=processing_report_path,
                    failed_assumption="M/S EQ can be audited from the processing report.",
                    human_listening_required=False,
                )
            reason = _as_text(move.get("reason")).lower()
            if reason and not any(allowed in reason for allowed in allowed_ms_reasons):
                add_finding(
                    "WARN",
                    "MS_EQ_REASON_NOT_ALLOWED",
                    "An M/S EQ move used a reason outside the allowed rulebook reasons.",
                    f"move_index={index}, reason={reason}",
                    "Use M/S EQ only for side wash, stereo harshness, low-end mono, vocal center protection, side cleanup, or width stabilization.",
                    findings,
                    affected_file=processing_report_path,
                    failed_assumption="M/S EQ reason is professionally bounded.",
                    human_listening_required=True,
                )

        if category in {"deesser", "de-esser", "de_esser"}:
            target = _as_text(move.get("target") or move.get("source")).lower()
            max_reduction = abs(_number(move.get("max_reduction_db") or move.get("max_gain_reduction_db")))
            if any(term in target for term in ("fullmix", "full mix", "master", "stereo")):
                add_finding(
                    "WARN",
                    "FULLMIX_DEESSER_RISK",
                    "A de-esser is targeting the fullmix/master path.",
                    f"move_index={index}, target={target}, max_reduction_db={max_reduction:.2f}",
                    "Prefer isolated vocal de-essing when possible; keep fullmix de-essing narrow and light, then run brightness/vocal A/B.",
                    findings,
                    affected_file=processing_report_path,
                    failed_assumption="Fullmix de-essing is low risk.",
                    human_listening_required=True,
                )
            if max_reduction > _number(thresholds["fullmix_deesser_max_reduction_db"]) and any(
                term in target for term in ("fullmix", "full mix", "master", "stereo")
            ):
                add_finding(
                    "FAIL",
                    "FULLMIX_DEESSER_TOO_AGGRESSIVE",
                    "Fullmix de-essing exceeds the profile reduction guard.",
                    f"move_index={index}, max_reduction_db={max_reduction:.2f}, guard={thresholds['fullmix_deesser_max_reduction_db']:.2f}",
                    "Reduce de-esser depth or move processing to an isolated vocal/fullmix-derived vocal support path.",
                    findings,
                    affected_file=processing_report_path,
                    failed_assumption="Fullmix de-essing preserved cymbals, air, and intelligibility.",
                    human_listening_required=True,
                )
            if not move.get("brightness_loss_guard"):
                add_finding(
                    "WARN",
                    "DEESSER_BRIGHTNESS_GUARD_MISSING",
                    "A de-esser move lacks a brightness loss guard.",
                    f"move_index={index}",
                    "Add a brightness/vocal-presence guard and rerun the engineering checker.",
                    findings,
                    affected_file=processing_report_path,
                    failed_assumption="De-esser decision can be validated against brightness loss.",
                    human_listening_required=False,
                )

        if category in {"compression", "compressor", "comp"}:
            missing = _move_missing_fields(
                move,
                (
                    "target",
                    "purpose",
                    "ratio",
                    "attack_ms",
                    "release_ms",
                    "knee_db",
                    "gain_reduction_target_db",
                    "makeup_gain_db",
                    "expected_sonic_effect",
                    "failure_mode",
                ),
            )
            if missing:
                add_finding(
                    "WARN",
                    "COMPRESSION_REPORT_FIELDS_MISSING",
                    "A compression move is missing required intent fields.",
                    f"move_index={index}, missing={missing}",
                    "Define target, purpose, ratio, attack, release, knee, gain reduction, makeup, expected effect, and failure mode.",
                    findings,
                    affected_file=processing_report_path,
                    failed_assumption="Compression was intentional and auditable.",
                    human_listening_required=False,
                )
            target = _as_text(move.get("target")).lower()
            gain_reduction = abs(_number(move.get("gain_reduction_target_db") or move.get("gain_reduction_db")))
            if "master" in target and gain_reduction > _number(thresholds["master_bus_max_gain_reduction_db"]):
                add_finding(
                    "WARN",
                    "MASTER_COMPRESSION_TOO_HEAVY",
                    "Master bus compression exceeds the profile gain-reduction guard.",
                    f"move_index={index}, gain_reduction_db={gain_reduction:.2f}, guard={thresholds['master_bus_max_gain_reduction_db']:.2f}",
                    "Reduce master compression or move control to source/bus processing; rerun transient and punch QC.",
                    findings,
                    affected_file=processing_report_path,
                    failed_assumption="Master compression remained conservative.",
                    human_listening_required=True,
                )

        if category in {"dynamic_eq", "dynamic eq", "dyneq", "master_dynamic_eq"}:
            missing = _move_missing_fields(
                move,
                ("frequency_range_hz", "q_or_bandwidth", "threshold_behavior", "max_reduction_db", "attack_release_concept", "reason", "risk"),
            )
            if missing:
                add_finding(
                    "WARN",
                    "DYNAMIC_EQ_REPORT_FIELDS_MISSING",
                    "A dynamic EQ band is missing required audit fields.",
                    f"move_index={index}, missing={missing}",
                    "Report frequency range, Q/bandwidth, threshold behavior, max reduction, attack/release concept, reason, and risk.",
                    findings,
                    affected_file=processing_report_path,
                    failed_assumption="Dynamic EQ band can be audited.",
                    human_listening_required=False,
                )
            max_reduction = abs(_number(move.get("max_reduction_db") or move.get("max_gain_reduction_db")))
            if "master" in _as_text(move.get("target")).lower() and max_reduction > _number(thresholds["master_dynamic_eq_max_reduction_db"]):
                add_finding(
                    "WARN",
                    "MASTER_DYNAMIC_EQ_TOO_HEAVY",
                    "Master dynamic EQ exceeds the profile max-reduction guard.",
                    f"move_index={index}, max_reduction_db={max_reduction:.2f}, guard={thresholds['master_dynamic_eq_max_reduction_db']:.2f}",
                    "Reduce max reduction or move the repair earlier in the mix path.",
                    findings,
                    affected_file=processing_report_path,
                    failed_assumption="Master dynamic EQ remained subtle.",
                    human_listening_required=True,
                )

        if category in {"deai", "suno_deai", "artifact_reduction"}:
            intensity = _as_text(move.get("intensity")).lower()
            if intensity in {"strong", "extreme"}:
                brightness_delta = _delta(comparison, "air_fizz_band_db")
                transient_ratio = _delta(comparison, "transient_ratio")
                side_mid_delta = _delta(comparison, "side_mid_ratio_db")
                punch_delta = _delta(comparison, "low_band_energy_db")
                risky = (
                    (brightness_delta is not None and brightness_delta <= -_number(thresholds["brightness_loss_warn_db"]))
                    or (transient_ratio is not None and transient_ratio < _number(thresholds["transient_loss_warn_ratio"]))
                    or (side_mid_delta is not None and abs(side_mid_delta) > _number(thresholds["side_mid_change_warn_db"]))
                    or (punch_delta is not None and punch_delta <= -_number(thresholds["punch_loss_warn_db"]))
                )
                add_finding(
                    "WARN" if risky else "INFO",
                    "STRONG_DEAI_REQUIRES_EXTRA_QC",
                    "Strong/extreme DeAI is not a default final setting.",
                    f"move_index={index}, intensity={intensity}, risky_metric={risky}",
                    "Keep a mild/punch-preserve candidate and require human A/B before selecting strong DeAI.",
                    findings,
                    affected_file=processing_report_path,
                    failed_assumption="Higher DeAI intensity is automatically better.",
                    human_listening_required=True,
                )

    for plugin in _as_list(report.get("plugins")) + _as_list(report.get("plugin_audit")):
        if not isinstance(plugin, dict):
            continue
        available = _boolish(plugin.get("available", True))
        required = _boolish(plugin.get("required", False))
        if available:
            continue
        mode = _as_text(report.get("mode") or report.get("classification")).lower()
        severity = _as_text(plugin.get("severity")).upper()
        if severity not in {"WARN", "FAIL", "BLOCKER"}:
            severity = "BLOCKER" if required and mode in {"suno_deai", "vocal_repair", "true_rebeat"} else ("FAIL" if required else "WARN")
        add_finding(
            severity,
            "PLUGIN_MISSING_OR_UNVERIFIED",
            "A referenced plugin is missing or unverified.",
            json.dumps(plugin, sort_keys=True),
            "Install/verify the plugin or switch to a documented fallback chain, then rerun plugin audit and render validation.",
            findings,
            affected_file=processing_report_path,
            failed_assumption="Required processing plugin is available and loaded.",
            command_to_rerun="python3 harness/plugin_audit.py --project-root . --out reports/plugin_audit.json",
            human_listening_required=False,
        )

    reference = report.get("reference_matching", {}) if isinstance(report.get("reference_matching", {}), dict) else {}
    true_peak_failed = any(finding.code in {"TRUE_PEAK_RULE_FAIL", "TRUE_PEAK_TARGET_EXCEEDED"} for finding in findings)
    if (reference.get("forced") or reference.get("override_safety")) and true_peak_failed:
        add_finding(
            "FAIL",
            "REFERENCE_MATCHING_OVERRIDES_TRUE_PEAK",
            "Reference matching attempted to override clipping/true-peak safety.",
            json.dumps(reference, sort_keys=True),
            "Lower output/limiter ceiling and reject the reference-matched candidate until true peak passes.",
            findings,
            affected_file=processing_report_path,
            failed_assumption="Reference matching can override master safety.",
            human_listening_required=True,
        )

    candidates = _as_list(report.get("candidates"))
    selected = _as_text(report.get("selected_candidate") or _nested(report, "selection", "selected_candidate")).lower()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        name = _as_text(candidate.get("name") or candidate.get("id")).lower()
        if selected and name != selected:
            continue
        metrics = candidate.get("metrics", {}) if isinstance(candidate.get("metrics", {}), dict) else {}
        brightness_loss = _number(metrics.get("brightness_loss_db"), default=0.0)
        punch_loss = _number(metrics.get("punch_loss_db"), default=0.0)
        transient_ratio = _number(metrics.get("transient_ratio"), default=1.0)
        intensity = _as_text(candidate.get("deai_intensity")).lower()
        if intensity in {"strong", "extreme"} and (
            brightness_loss > _number(thresholds["brightness_loss_warn_db"])
            or punch_loss > _number(thresholds["punch_loss_warn_db"])
            or transient_ratio < _number(thresholds["transient_loss_warn_ratio"])
        ):
            add_finding(
                "FAIL",
                "STRONG_DEAI_SELECTED_DESPITE_COLLAPSE",
                "A stronger DeAI candidate was selected despite brightness, punch, or transient collapse.",
                json.dumps(candidate, sort_keys=True),
                "Select the safest musically usable candidate, not the cleanest one, and rerun the final report.",
                findings,
                affected_file=processing_report_path,
                failed_assumption="More DeAI cleanup is automatically the best final.",
                human_listening_required=True,
            )


def run_engineering_rule_check(
    *,
    before: str | Path | None = None,
    after: str | Path | None = None,
    profile_path: str | Path | None = None,
    processing_report_path: str | Path | None = None,
    processing_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = load_profile(profile_path)
    thresholds = thresholds_for(profile)
    report = processing_report or _read_json(processing_report_path)
    findings: list[Finding] = []

    comparison: dict[str, Any] | None = None
    if before and after:
        comparison = compare_before_after(before, after, findings, profile=audio_qc_profile(profile))
    elif not (report.get("metrics") or report.get("qc_metrics")):
        add_finding(
            "BLOCKER",
            "QC_AUDIO_OR_METRICS_MISSING",
            "No before/after audio or precomputed metrics were provided.",
            "The rule checker needs either --before/--after or metrics in the processing report.",
            "Provide before/after WAV files or embed before/after/delta metrics in the processing report.",
            findings,
            affected_file=str(processing_report_path or ""),
            failed_assumption="Objective QC evidence is available.",
        )
    comparison = _merge_comparison(comparison, _comparison_from_report(report))

    _check_metric_thresholds(comparison, thresholds, findings, str(after or ""))
    _check_claims(report, findings, str(processing_report_path or ""))
    _check_processing_moves(report, comparison, profile, thresholds, findings, str(processing_report_path or ""))

    if not findings:
        add_finding(
            "PASS",
            "ENGINEERING_RULE_CHECK_PASS",
            "Engineering rule check passed for available metrics and claims.",
            "No WARN+ findings were produced.",
            "Keep this rule check attached to the render report.",
            findings,
            affected_file=str(processing_report_path or ""),
        )

    warn_plus = warn_plus_findings(findings)
    payload = {
        "profile": profile.get("profile_name", "default"),
        "profile_path": str(profile_path or ""),
        "status": "not_final_warn_plus" if warn_plus else "pass",
        "max_severity": max_severity(findings),
        "warn_plus_count": len(warn_plus),
        "comparison": comparison,
        "findings": findings_to_dicts(findings),
        "commands": {
            "rerun_rule_check": "python3 harness/engineering_rule_checker.py --before BEFORE.wav --after AFTER.wav --profile PROFILE.json --processing-report REPORT.json --out-json rule_check.json --out-md rule_check.md",
            "rerun_audio_qc": "python3 harness/audio_qc.py --before BEFORE.wav --after AFTER.wav --json",
            "rerun_plugin_audit": "python3 harness/plugin_audit.py --project-root . --out reports/plugin_audit.json",
        },
    }
    return payload


def _markdown_report(payload: dict[str, Any]) -> str:
    title = "# Engineering Rule Check"
    summary = [
        title,
        "",
        f"- Profile: `{payload.get('profile')}`",
        f"- Status: `{payload.get('status')}`",
        f"- Max severity: `{payload.get('max_severity')}`",
        f"- WARN+ count: `{payload.get('warn_plus_count')}`",
        "",
        "## Findings",
        "",
        findings_to_markdown([Finding(**finding) for finding in payload.get("findings", [])]),
        "",
        "## Rerun Commands",
        "",
    ]
    for command in payload.get("commands", {}).values():
        summary.append(f"- `{command}`")
    return "\n".join(summary) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check REAPER/audio processing decisions against engineering rules.")
    parser.add_argument("--before", help="Before/source WAV for objective QC.")
    parser.add_argument("--after", help="After/rendered WAV for objective QC.")
    parser.add_argument("--profile", default=str(Path(__file__).resolve().parents[1] / "presets" / "engineering_rules" / "default_engineering_rules.json"))
    parser.add_argument("--processing-report", required=True)
    parser.add_argument("--out-json")
    parser.add_argument("--out-md")
    args = parser.parse_args(argv)

    payload = run_engineering_rule_check(
        before=args.before,
        after=args.after,
        profile_path=args.profile,
        processing_report_path=args.processing_report,
    )

    if args.out_json:
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if args.out_md:
        Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_md).write_text(_markdown_report(payload), encoding="utf-8")

    if not args.out_json and not args.out_md:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 2 if has_warn_plus(payload["findings"]) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
