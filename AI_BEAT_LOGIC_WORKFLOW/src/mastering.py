from __future__ import annotations

import math
import shutil
from pathlib import Path
from typing import Any

from audio_analysis import read_wav_float
from export_audio import write_float_wav
from loudness_estimation import db_to_linear, linear_to_db
from mastering_targets import MasteringTarget, get_mastering_target
from master_qc import analyze_master_wav, build_master_qc_report, verify_master_completion
from mix_master_autopilot import build_mix_master_plan, write_mix_master_plan


def choose_master_source(project_root: Path) -> tuple[Path, str]:
    candidates = [
        (project_root / "09_MIX_MASTER" / "pre_master.wav", "pre_master"),
        (project_root / "03_LOGIC_PROJECT" / "logic_export.wav", "logic_export"),
        (project_root / "04_PROCESSED_AUDIO" / "fallback_processed.wav", "fallback_processed"),
    ]
    for path, label in candidates:
        if path.exists():
            return path, label
    raise FileNotFoundError("No mastering source found. Expected pre_master.wav, Logic export, or fallback_processed.wav.")


def _peak(channels: list[list[float]]) -> float:
    return max((abs(sample) for channel in channels for sample in channel), default=0.0)


def _gain_to_peak(channels: list[list[float]], target_dbfs: float) -> tuple[list[list[float]], float]:
    peak = _peak(channels)
    if peak <= 0.0:
        return channels, 1.0
    gain = db_to_linear(target_dbfs) / peak
    gain = min(gain, 2.5)
    return [[sample * gain for sample in channel] for channel in channels], gain


def _high_pass_channel(samples: list[float], sample_rate: int, cutoff_hz: float = 25.0) -> list[float]:
    if not samples or sample_rate <= 0:
        return list(samples)
    rc = 1.0 / (2.0 * math.pi * cutoff_hz)
    dt = 1.0 / sample_rate
    alpha = rc / (rc + dt)
    output: list[float] = []
    previous_input = samples[0]
    previous_output = 0.0
    for sample in samples:
        value = alpha * (previous_output + sample - previous_input)
        output.append(value)
        previous_input = sample
        previous_output = value
    return output


def _high_pass(channels: list[list[float]], sample_rate: int) -> list[list[float]]:
    return [_high_pass_channel(channel, sample_rate) for channel in channels]


def _compress_value(sample: float, threshold: float, ratio: float) -> float:
    sign = -1.0 if sample < 0 else 1.0
    value = abs(sample)
    if value <= threshold:
        return sample
    return sign * (threshold + (value - threshold) / ratio)


def _gentle_bus_compression(channels: list[list[float]], target: MasteringTarget) -> list[list[float]]:
    threshold = db_to_linear(target.compression_threshold_dbfs)
    return [[_compress_value(sample, threshold, target.compression_ratio) for sample in channel] for channel in channels]


def _subtle_saturation(channels: list[list[float]], target: MasteringTarget) -> list[list[float]]:
    if target.saturation_drive <= 1.0:
        return channels
    normalizer = math.tanh(target.saturation_drive)
    return [[math.tanh(sample * target.saturation_drive) / normalizer for sample in channel] for channel in channels]


def _limit(channels: list[list[float]], ceiling_dbfs: float) -> list[list[float]]:
    ceiling = db_to_linear(ceiling_dbfs)
    return [[max(-ceiling, min(ceiling, sample)) for sample in channel] for channel in channels]


def _effect_availability_note() -> str:
    if shutil.which("ffmpeg"):
        return "ffmpeg available; Python fallback mastering kept conservative for reproducibility."
    return "ffmpeg unavailable; Python fallback mastering used conservative gain/filter/dynamics only."


def render_master(
    source_path: Path,
    output_path: Path,
    target: MasteringTarget,
    bit_depth: int = 24,
) -> dict[str, Any]:
    metadata, channels = read_wav_float(source_path)
    notes: list[str] = [_effect_availability_note()]
    processed, pregain = _gain_to_peak(channels, -6.0)
    notes.append(f"pre-master gain staging applied, gain {pregain:.4f}")
    processed = _high_pass(processed, metadata["sample_rate"])
    notes.append("low-end cleanup below roughly 25 Hz applied")
    notes.append("broad tonal correction was limited to sub cleanup because detailed spectral EQ is not available in fallback")
    processed = _gentle_bus_compression(processed, target)
    notes.append(f"gentle bus compression ratio {target.compression_ratio:.2f}:1")
    processed = _subtle_saturation(processed, target)
    if target.saturation_drive > 1.0:
        notes.append(f"very subtle saturation drive {target.saturation_drive:.2f}")
    processed, target_gain = _gain_to_peak(processed, target.peak_target_dbfs)
    notes.append(f"final gain staged toward {target.peak_target_dbfs:.1f} dBFS")
    processed = _limit(processed, target.limiter_ceiling_dbfs)
    notes.append(f"final limiter ceiling {target.limiter_ceiling_dbfs:.1f} dBFS")
    write_float_wav(output_path, processed, metadata["sample_rate"], bit_depth=bit_depth)
    final_info = analyze_master_wav(output_path)
    return {
        "source_path": str(source_path),
        "output_path": str(output_path),
        "target_gain": target_gain,
        "target": target.name,
        "target_warning": target.warning,
        "processing_notes": notes,
        "final_info": final_info,
        "peak_after_processing_dbfs": linear_to_db(_peak(processed)),
    }


def run_mastering_stage(options: dict[str, Any] | None = None, project_root: Path | None = None) -> dict[str, Any]:
    resolved_options = options or {}
    root = project_root or Path(__file__).resolve().parents[1]
    target = get_mastering_target(resolved_options.get("master_loudness", "master_ready_headroom"))
    mix_dir = root / "09_MIX_MASTER"
    mix_dir.mkdir(parents=True, exist_ok=True)
    mix_plan = build_mix_master_plan(
        input_mode=resolved_options.get("mode", "instrumental_beat"),
        style_target=resolved_options.get("arrangement_genre", "commercial_digicore_hyperpop"),
        master_target_mode=resolved_options.get("master_loudness", "master_ready_headroom"),
        release_ready=bool(resolved_options.get("release_ready")),
        requested_deliverables=(resolved_options.get("release_intent") or {}).get("deliverables_requested")
        if isinstance(resolved_options.get("release_intent"), dict)
        else None,
    )
    mix_plan_paths = write_mix_master_plan(root, mix_plan)
    source_path, source_type = choose_master_source(root)
    output_path = mix_dir / "final_mix_master.wav"
    result = render_master(source_path, output_path, target, bit_depth=24)
    warnings = [target.warning]
    report = build_master_qc_report(
        resolved_options,
        source_path,
        output_path,
        result["final_info"],
        result["processing_notes"],
        warnings,
    )
    report_path = mix_dir / "master_qc_report.md"
    report_path.write_text(report, encoding="utf-8")
    gate = verify_master_completion(root, resolved_options, output_path, report_path)
    return {
        **result,
        "source_type": source_type,
        "master_qc_report": str(report_path),
        "completion_gate": gate,
        "mix_master_plan": mix_plan,
        "mix_master_plan_paths": {key: str(value) for key, value in mix_plan_paths.items()},
    }
