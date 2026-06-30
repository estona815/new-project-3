from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Any

from automix.export.audio_export_utils import wav_info
from automix.plugins.plugin_adapter_schema import now_utc, safe_float, write_json


FINAL_QC_EVIDENCE_SCHEMA = "automix-final-qc-evidence-gate-v1"

GATE_REL_PATH = Path("eval_reports/final_qc_evidence_gate.json")
GATE_REPORT_REL_PATH = Path("eval_reports/final_qc_evidence_gate.md")
TEMPLATE_REL_PATH = Path("review/final_qc_evidence_manifest_template.json")
REQUEST_REL_PATH = Path("review/final_qc_evidence_request.md")

DEFAULT_QC_REL_PATH = Path("eval_reports/final_qc_metrics.json")
FINAL_RENDER_EVIDENCE_REL_PATH = Path("eval_reports/final_render_evidence_gate.json")
RENDER_MANIFEST_REL_PATH = Path("export/final_render_manifest.json")

TRUE_PEAK_CEILING_DBTP = -1.0
DURATION_TOLERANCE_SECONDS = 0.01
VOLUME_UNIFORMITY_MAX_RMS_DB_SPREAD = 12.0
VOLUME_UNIFORMITY_MAX_ADJACENT_DB_DELTA = 14.0
VOLUME_UNIFORMITY_WARNING_ADJACENT_DB_DELTA = 10.0
VOLUME_UNIFORMITY_MAX_ADJACENT_JUMP_COUNT = 2
VOLUME_UNIFORMITY_WARNING_ADJACENT_JUMP_COUNT = 1
VOCAL_PRESENCE_MIN_SOFT = 0.20
VOCAL_PRESENCE_MIN_HARD = 0.12
VOCAL_MASKING_RISK_MAX_HARD = 0.78
VOCAL_TO_BEAT_BALANCE_MIN_SOFT = 0.18
VOCAL_TO_BEAT_BALANCE_MIN_HARD = 0.12


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_path(path_text: str, output_dir: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    candidates = [path, output_dir / path, output_dir.parent / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return path


def _path_key(path_text: str, output_dir: Path) -> str:
    if not path_text:
        return ""
    try:
        return str(_resolve_path(path_text, output_dir).resolve())
    except OSError:
        return str(_resolve_path(path_text, output_dir))


def _render_manifest_primary_wavs(manifest: dict[str, Any], output_dir: Path) -> set[str]:
    paths: set[str] = set()
    renders = manifest.get("renders", []) if isinstance(manifest.get("renders", []), list) else []
    for item in renders:
        if not isinstance(item, dict):
            continue
        if item.get("format") != "wav" or not item.get("created"):
            continue
        path = str(item.get("path", "") or "")
        if path:
            paths.add(_path_key(path, output_dir))
    return paths


def _audio_status(path_text: str, output_dir: Path) -> dict[str, Any]:
    if not path_text:
        return {
            "path": "",
            "exists": False,
            "valid_wav": False,
            "failures": ["final_audio_path_missing"],
        }
    path = _resolve_path(path_text, output_dir)
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "valid_wav": False,
            "failures": ["final_audio_file_missing"],
        }
    if not path.is_file():
        return {
            "path": str(path),
            "exists": True,
            "valid_wav": False,
            "failures": ["final_audio_path_not_file"],
        }
    if path.suffix.lower() != ".wav":
        return {
            "path": str(path),
            "exists": True,
            "size_bytes": path.stat().st_size,
            "valid_wav": False,
            "failures": ["final_audio_file_not_wav"],
        }
    try:
        info = wav_info(path)
    except (wave.Error, EOFError, OSError) as exc:
        return {
            "path": str(path),
            "exists": True,
            "size_bytes": path.stat().st_size,
            "valid_wav": False,
            "failures": [f"final_audio_wav_unreadable:{exc}"],
        }
    failures: list[str] = []
    if int(info.get("size_bytes", 0) or 0) <= 0:
        failures.append("final_audio_file_empty")
    if float(info.get("duration_seconds", 0.0) or 0.0) <= 0.0:
        failures.append("final_audio_duration_missing")
    for key in ("sample_rate", "bit_depth", "channels"):
        if int(info.get(key, 0) or 0) <= 0:
            failures.append(f"final_audio_{key}_missing")
    info["path"] = str(path)
    info["valid_wav"] = not failures
    info["failures"] = failures
    return info


def _file_integrity_blockers(file_integrity: dict[str, Any], audio: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not isinstance(file_integrity, dict) or not file_integrity:
        return ["final_qc_file_integrity_missing"]
    if file_integrity.get("exists") is not True:
        blockers.append("final_qc_file_integrity_missing_or_false")
    for key in ("size_bytes", "sample_rate", "bit_depth", "channels"):
        expected = int(file_integrity.get(key, 0) or 0)
        actual = int(audio.get(key, 0) or 0)
        if expected <= 0:
            blockers.append(f"final_qc_file_integrity_{key}_missing")
        elif actual and expected != actual:
            blockers.append(f"final_qc_file_integrity_{key}_mismatch")
    expected_duration = safe_float(file_integrity.get("duration_seconds"), 0.0)
    actual_duration = safe_float(audio.get("duration_seconds"), 0.0)
    if expected_duration <= 0.0:
        blockers.append("final_qc_file_integrity_duration_seconds_missing")
    elif actual_duration and abs(expected_duration - actual_duration) > DURATION_TOLERANCE_SECONDS:
        blockers.append("final_qc_file_integrity_duration_seconds_mismatch")
    for key in ("clipping_detected", "digital_black_detected", "unexpected_silence_detected"):
        if file_integrity.get(key) is True:
            blockers.append(f"final_qc_{key}")
    return sorted(set(blockers))


def _volume_uniformity_blockers(volume_uniformity: dict[str, Any], blockers: list[str], warnings: list[str]) -> None:
    if not volume_uniformity:
        return
    status = str(volume_uniformity.get("status", "")).lower()
    if status == "insufficient_active_windows":
        warnings.append("final_qc_warning:volume_uniformity_insufficient_active_windows")
        return
    if status != "assessed":
        return
    active_range = volume_uniformity.get("active_dbfs_range")
    if active_range is None:
        return
    if float(active_range) > VOLUME_UNIFORMITY_MAX_RMS_DB_SPREAD:
        blockers.append("final_qc_volume_uniformity_exceeds_limit")
    severe_jump_count = int(volume_uniformity.get("severe_level_jump_count", 0))
    if severe_jump_count > VOLUME_UNIFORMITY_MAX_ADJACENT_JUMP_COUNT:
        blockers.append("final_qc_volume_uniformity_excessive_abrupt_jumps")
    active_delta = volume_uniformity.get("max_adjacent_dbfs_delta")
    if active_delta is None:
        return
    if float(active_delta) > VOLUME_UNIFORMITY_MAX_ADJACENT_DB_DELTA:
        blockers.append("final_qc_volume_uniformity_abrupt_level_jump")
    elif float(active_delta) > VOLUME_UNIFORMITY_WARNING_ADJACENT_DB_DELTA:
        warnings.append("final_qc_warning:volume_uniformity_abrupt_level_jump")
    abrupt_jump_count = int(volume_uniformity.get("abrupt_level_jump_count", 0))
    if abrupt_jump_count > VOLUME_UNIFORMITY_WARNING_ADJACENT_JUMP_COUNT:
        warnings.append(f"final_qc_warning:volume_uniformity_multiple_abrupt_jumps:{abrupt_jump_count}")


def _vocal_presence_blockers(vocal_preservation: dict[str, Any], blockers: list[str], warnings: list[str]) -> None:
    if not vocal_preservation:
        return
    forwardness = safe_float(vocal_preservation.get("vocal_forwardness_score"), 0.0)
    clarity = safe_float(vocal_preservation.get("vocal_clarity_score"), 0.0)
    masking = safe_float(vocal_preservation.get("vocal_masking_risk"), 0.0)
    to_beat_balance = safe_float(vocal_preservation.get("vocal_to_beat_balance"), 0.0)
    if forwardness < VOCAL_PRESENCE_MIN_HARD and clarity < 0.28:
        blockers.append("final_qc_vocal_presence_too_weak")
    elif forwardness < VOCAL_PRESENCE_MIN_SOFT:
        warnings.append(f"final_qc_warning:vocal_forwardness_low:{round(forwardness, 2)}")
    if clarity < 0.28:
        warnings.append(f"final_qc_warning:vocal_clarity_low:{round(clarity, 2)}")
    if to_beat_balance < VOCAL_TO_BEAT_BALANCE_MIN_HARD and forwardness < VOCAL_PRESENCE_MIN_SOFT:
        blockers.append("final_qc_vocal_to_beat_balance_critical")
    elif to_beat_balance < VOCAL_TO_BEAT_BALANCE_MIN_SOFT:
        warnings.append(f"final_qc_warning:vocal_to_beat_balance_low:{round(to_beat_balance, 2)}")
    if masking > VOCAL_MASKING_RISK_MAX_HARD:
        blockers.append("final_qc_vocal_masking_excessive")


def _template() -> dict[str, Any]:
    return {
        "schema": "automix-final-qc-evidence-manifest-template-v1",
        "expected_reports": [
            "automix/eval_reports/final_qc_metrics.json",
            "automix/eval_reports/final_qc_evidence_gate.json",
            "automix/eval_reports/final_render_evidence_gate.json",
            "automix/export/final_render_manifest.json",
        ],
        "required_checks": [
            "final_qc_metrics.json uses schema automix-final-qc-metrics-v1",
            "final_audio_path exists, is a readable nonempty WAV, and matches final render evidence",
            "file_integrity values match the actual WAV header",
            "qc_passed is true and failures is empty",
            "clipping, digital black, unexpected silence, and true-peak ceiling blockers are absent",
            "volume_uniformity spread and abrupt-level deltas are within configured tolerance when assessed",
            "frequent abrupt-level volume jumps are limited.",
            "vocal forwardness/clarity are above soft thresholds and masking risk is controlled",
            "vocal-to-beat balance remains above soft thresholds when measured",
        ],
        "limits": [
            "This template is not final approval.",
            "Final QC evidence does not replace loudness-matched A/B review or human listening.",
            "Do not use missing, diagnostic, or mismatched QC metrics as delivery evidence.",
        ],
    }


def build_final_qc_evidence_gate(
    *,
    project_name: str,
    output_dir: Path,
    qc_metrics_path: Path | None = None,
    final_render_evidence_path: Path | None = None,
    render_manifest_path: Path | None = None,
    true_peak_ceiling_dbTP: float = TRUE_PEAK_CEILING_DBTP,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    qc_path = Path(qc_metrics_path) if qc_metrics_path else output_dir / DEFAULT_QC_REL_PATH
    render_gate_path = Path(final_render_evidence_path) if final_render_evidence_path else output_dir / FINAL_RENDER_EVIDENCE_REL_PATH
    render_manifest_file = Path(render_manifest_path) if render_manifest_path else output_dir / RENDER_MANIFEST_REL_PATH
    qc_metrics = _load_json(qc_path)
    render_gate = _load_json(render_gate_path)
    render_manifest = _load_json(render_manifest_file)
    blockers: list[str] = []
    warnings: list[str] = []

    if not qc_path.exists() or not qc_metrics:
        blockers.append("final_qc_metrics_missing_or_invalid")
    elif qc_metrics.get("schema") != "automix-final-qc-metrics-v1":
        blockers.append("final_qc_metrics_schema_invalid")

    if not render_gate_path.exists() or not render_gate:
        blockers.append("final_render_evidence_gate_missing_or_invalid")
    elif render_gate.get("schema") != "automix-final-render-evidence-gate-v1":
        blockers.append("final_render_evidence_gate_schema_invalid")
    elif not render_gate.get("ready_for_final_qc", False):
        blockers.append("final_render_evidence_not_ready")
        blockers.extend(f"final_render_evidence:{item}" for item in render_gate.get("blockers", []) or [])

    if not render_manifest_file.exists() or not render_manifest:
        blockers.append("final_render_manifest_missing_or_invalid")
    elif render_manifest.get("schema") != "automix-final-render-manifest-v1":
        blockers.append("final_render_manifest_schema_invalid")

    final_audio = _audio_status(str(qc_metrics.get("final_audio_path", "") or ""), output_dir)
    if not final_audio.get("valid_wav", False):
        blockers.extend(str(item) for item in final_audio.get("failures", []))

    file_integrity = qc_metrics.get("file_integrity", {}) if isinstance(qc_metrics.get("file_integrity", {}), dict) else {}
    blockers.extend(_file_integrity_blockers(file_integrity, final_audio))

    if qc_metrics.get("qc_passed") is not True:
        blockers.append("final_qc_not_passed")
    qc_failures = [str(item) for item in qc_metrics.get("failures", []) or []]
    if qc_failures:
        blockers.append("final_qc_has_failures")
        blockers.extend(f"final_qc_failure:{item}" for item in qc_failures)
    warnings.extend(f"final_qc_warning:{item}" for item in qc_metrics.get("warnings", []) or [])
    _volume_uniformity_blockers(
        qc_metrics.get("volume_uniformity", {}) if isinstance(qc_metrics.get("volume_uniformity", {}), dict) else {},
        blockers,
        warnings,
    )
    _vocal_presence_blockers(qc_metrics.get("vocal_preservation", {}) if isinstance(qc_metrics.get("vocal_preservation", {}), dict) else {}, blockers, warnings)

    loudness = qc_metrics.get("loudness", {}) if isinstance(qc_metrics.get("loudness", {}), dict) else {}
    true_peak = loudness.get("true_peak_dbTP")
    if true_peak is None:
        blockers.append("final_qc_true_peak_missing")
    elif safe_float(true_peak, 999.0) > true_peak_ceiling_dbTP:
        blockers.append("final_qc_true_peak_above_ceiling")

    final_key = _path_key(str(qc_metrics.get("final_audio_path", "") or ""), output_dir)
    render_gate_key = _path_key(str(render_gate.get("primary_wav_path", "") or ""), output_dir)
    if final_key and render_gate_key and final_key != render_gate_key:
        blockers.append("final_audio_path_mismatch_render_evidence_primary_wav")
    render_manifest_keys = _render_manifest_primary_wavs(render_manifest, output_dir)
    if render_manifest_keys and final_key and final_key not in render_manifest_keys:
        blockers.append("final_audio_not_in_render_manifest_primary_wavs")
    elif render_manifest and not render_manifest_keys:
        blockers.append("final_render_manifest_primary_wav_missing")

    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))
    ready = not blockers
    template_path = output_dir / TEMPLATE_REL_PATH
    write_json(template_path, _template())
    volume_uniformity = qc_metrics.get("volume_uniformity", {}) if isinstance(qc_metrics.get("volume_uniformity", {}), dict) else {}
    vocal_preservation = qc_metrics.get("vocal_preservation", {}) if isinstance(qc_metrics.get("vocal_preservation", {}), dict) else {}
    gate = {
        "schema": FINAL_QC_EVIDENCE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "qc_metrics_path": str(qc_path),
        "final_render_evidence_path": str(render_gate_path),
        "render_manifest_path": str(render_manifest_file),
        "ready_for_delivery_qc": ready,
        "ready_for_approval_readiness": ready,
        "final_audio_path": final_audio.get("path", ""),
        "true_peak_ceiling_dbTP": true_peak_ceiling_dbTP,
        "audio_status": final_audio,
        "file_integrity_summary": file_integrity,
        "qc_summary": {
            "qc_passed": bool(qc_metrics.get("qc_passed", False)),
            "failures": qc_failures,
            "warnings": qc_metrics.get("warnings", []) or [],
            "volume_uniformity": {
                "status": volume_uniformity.get("status"),
                "active_dbfs_range": volume_uniformity.get("active_dbfs_range"),
                "active_window_count": volume_uniformity.get("active_window_count"),
                "window_count": volume_uniformity.get("window_count"),
                "max_adjacent_dbfs_delta": volume_uniformity.get("max_adjacent_dbfs_delta"),
                "abrupt_level_jump_count": volume_uniformity.get("abrupt_level_jump_count"),
                "severe_level_jump_count": volume_uniformity.get("severe_level_jump_count"),
                "adjacent_jump_ratio": volume_uniformity.get("adjacent_jump_ratio"),
            },
            "vocal_presence": {
                "vocal_forwardness_score": vocal_preservation.get("vocal_forwardness_score"),
                "vocal_clarity_score": vocal_preservation.get("vocal_clarity_score"),
                "vocal_masking_risk": vocal_preservation.get("vocal_masking_risk"),
                "vocal_to_beat_balance": vocal_preservation.get("vocal_to_beat_balance"),
            },
            "true_peak_dbTP": true_peak,
            "clipping_detected": bool(file_integrity.get("clipping_detected", False)),
            "digital_black_detected": bool(file_integrity.get("digital_black_detected", False)),
            "unexpected_silence_detected": bool(file_integrity.get("unexpected_silence_detected", False)),
        },
        "render_link_summary": {
            "final_render_evidence_ready": bool(render_gate.get("ready_for_final_qc", False)),
            "render_evidence_primary_wav": render_gate.get("primary_wav_path", ""),
            "final_audio_matches_render_evidence": bool(final_key and render_gate_key and final_key == render_gate_key),
            "render_manifest_primary_wavs_total": len(render_manifest_keys),
            "final_audio_in_render_manifest": bool(final_key and final_key in render_manifest_keys),
        },
        "blockers": blockers,
        "warnings": warnings,
        "template_path": str(template_path),
        "limits": [
            "This gate validates final QC evidence only; it does not approve audio.",
            "Measured QC does not replace loudness-matched A/B review, rollback evidence, or human approval.",
            "A passing gate means the QC report is internally consistent with the final render evidence.",
        ],
    }
    target = output_path or output_dir / GATE_REL_PATH
    write_json(target, gate)
    write_final_qc_evidence_report(gate, output_dir)
    write_final_qc_evidence_request(gate, output_dir)
    return gate


def write_final_qc_evidence_report(gate: dict[str, Any], output_dir: Path) -> Path:
    audio = gate.get("audio_status", {})
    qc = gate.get("qc_summary", {})
    render = gate.get("render_link_summary", {})
    lines = [
        "# Final QC Evidence Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Ready for delivery QC: `{gate.get('ready_for_delivery_qc')}`",
        f"- Ready for approval readiness: `{gate.get('ready_for_approval_readiness')}`",
        f"- Final audio: `{gate.get('final_audio_path')}`",
        f"- QC passed: `{qc.get('qc_passed')}`",
        f"- True peak dBTP: `{qc.get('true_peak_dbTP')}`",
        f"- True peak ceiling dBTP: `{gate.get('true_peak_ceiling_dbTP')}`",
        f"- Render evidence ready: `{render.get('final_render_evidence_ready')}`",
        f"- Final audio matches render evidence: `{render.get('final_audio_matches_render_evidence')}`",
        "",
        "This gate does not approve audio or claim quality. It only checks measured final QC evidence.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in gate.get("warnings", [])] or ["- none"])
    volume_uniformity = gate.get("qc_summary", {}).get("volume_uniformity", {})
    vocal_presence = gate.get("qc_summary", {}).get("vocal_presence", {})
    lines.extend(
        [
            "",
            "## Volume Uniformity",
            "",
            f"- Status: `{volume_uniformity.get('status')}`",
            f"- Active dbfs range: `{volume_uniformity.get('active_dbfs_range')}`",
            f"- Max adjacent dbfs delta: `{volume_uniformity.get('max_adjacent_dbfs_delta')}`",
            f"- abrupt level jump count: `{volume_uniformity.get('abrupt_level_jump_count')}`",
            f"- severe level jump count: `{volume_uniformity.get('severe_level_jump_count')}`",
            f"- adjacent jump ratio: `{volume_uniformity.get('adjacent_jump_ratio')}`",
            f"- Active window count: `{volume_uniformity.get('active_window_count')}`",
            f"- Window count: `{volume_uniformity.get('window_count')}`",
        ]
    )
    lines.extend(
        [
            "",
            "## Vocal Presence",
            "",
            f"- Forwardness: `{vocal_presence.get('vocal_forwardness_score')}`",
            f"- Clarity: `{vocal_presence.get('vocal_clarity_score')}`",
            f"- Masking risk: `{vocal_presence.get('vocal_masking_risk')}`",
            f"- Vocal-to-beat balance: `{vocal_presence.get('vocal_to_beat_balance')}`",
        ]
    )
    lines.extend(["", "## Audio File", ""])
    lines.append(f"- Path: `{audio.get('path', '')}`")
    lines.append(f"- Valid WAV: `{audio.get('valid_wav', False)}`")
    lines.append(f"- Duration seconds: `{audio.get('duration_seconds', '')}`")
    lines.append(f"- Sample rate: `{audio.get('sample_rate', '')}`")
    lines.append(f"- Bit depth: `{audio.get('bit_depth', '')}`")
    lines.append(f"- Channels: `{audio.get('channels', '')}`")
    path = Path(output_dir) / GATE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_final_qc_evidence_request(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Final QC Evidence Request",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Template: `{gate.get('template_path')}`",
        "",
    ]
    if gate.get("ready_for_delivery_qc"):
        lines.extend(
            [
                "Final QC evidence is ready for approval-readiness checks. This is not final approval.",
                "",
                "Next checks:",
                "",
                "- Keep the final QC metrics and report with the render evidence.",
                "- Validate loudness-matched A/B preview evidence.",
                "- Record human approval only after reviewing the matched-loudness preview.",
            ]
        )
    else:
        lines.extend(["Final QC evidence is not ready. Resolve these blockers first:", ""])
        lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    path = Path(output_dir) / REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
