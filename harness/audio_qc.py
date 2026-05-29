from __future__ import annotations

import argparse
import json
import math
import struct
import wave
from pathlib import Path
from typing import Any

try:
    import numpy as np
except Exception:  # pragma: no cover - exercised only on minimal Python installs.
    np = None  # type: ignore[assignment]

try:
    import pyloudnorm as pyln
except Exception:  # pragma: no cover - optional dependency.
    pyln = None  # type: ignore[assignment]

try:
    from scipy.io import wavfile as scipy_wavfile
except Exception:  # pragma: no cover - optional dependency.
    scipy_wavfile = None  # type: ignore[assignment]

try:
    from .severity import Finding, add_finding, findings_to_dicts, has_warn_plus, max_severity
except ImportError:  # pragma: no cover - direct script execution.
    from severity import Finding, add_finding, findings_to_dicts, has_warn_plus, max_severity


EPS = 1e-12
BANDS = {
    "low_band_energy_db": (20.0, 120.0),
    "low_mid_mud_band_db": (180.0, 500.0),
    "vocal_presence_band_db": (1000.0, 4000.0),
    "harshness_band_db": (3000.0, 8000.0),
    "sibilance_band_db": (5000.0, 9000.0),
    "air_fizz_band_db": (10000.0, 18000.0),
}
DEFAULT_TARGETS = {
    "true_peak_target_dbfs": -1.0,
    "max_acceptable_brightness_loss_db": 3.0,
    "max_acceptable_transient_loss_ratio": 0.30,
    "max_acceptable_side_mid_change_db": 3.0,
    "max_duration_delta_sec": 0.50,
    "max_duration_delta_ratio": 0.01,
}


def _db(value: float) -> float:
    return 20.0 * math.log10(max(float(value), EPS))


def _read_wav_pcm(path: Path, findings: list[Finding]) -> tuple[int, int, Any]:
    if not path.exists():
        add_finding(
            "FAIL",
            "AUDIO_FILE_MISSING",
            "Audio file is missing.",
            f"Path does not exist: {path}",
            "Provide the missing before/after WAV or correct the command path.",
            findings,
            affected_file=str(path),
            failed_assumption="Required before/after audio exists.",
        )
        raise FileNotFoundError(path)

    try:
        with wave.open(str(path), "rb") as handle:
            channels = handle.getnchannels()
            sample_width = handle.getsampwidth()
            sample_rate = handle.getframerate()
            frame_count = handle.getnframes()
            raw = handle.readframes(frame_count)
    except wave.Error as exc:
        if scipy_wavfile is not None and np is not None:
            try:
                sample_rate, scipy_data = scipy_wavfile.read(str(path))
                samples = scipy_data.astype(np.float32, copy=False)
                if np.issubdtype(scipy_data.dtype, np.integer):
                    info = np.iinfo(scipy_data.dtype)
                    samples = samples / float(max(abs(info.min), info.max))
                if samples.ndim == 1:
                    samples = samples.reshape((-1, 1))
                channels = int(samples.shape[1])
                add_finding(
                    "INFO",
                    "WAV_READ_SCIPY_FLOAT_FALLBACK",
                    "Read WAV through scipy fallback because Python wave could not parse the format.",
                    str(exc),
                    "No action needed if downstream metrics pass.",
                    findings,
                    affected_file=str(path),
                )
                return int(sample_rate), channels, np.nan_to_num(samples[:, :channels])
            except Exception:
                pass
        add_finding(
            "FAIL",
            "WAV_READ_FAILED",
            "The file could not be read as a PCM WAV.",
            str(exc),
            "Convert the file to WAV before running QC, then rerun the same command.",
            findings,
            affected_file=str(path),
            failed_assumption="QC input is a readable PCM WAV.",
        )
        raise

    if channels < 1:
        add_finding(
            "FAIL",
            "WAV_CHANNEL_COUNT_INVALID",
            "WAV has no audio channels.",
            f"channels={channels}",
            "Re-export the WAV with mono or stereo audio.",
            findings,
            affected_file=str(path),
        )
        raise ValueError("WAV has no channels")

    if np is None:
        if sample_width != 2:
            add_finding(
                "WARN",
                "NUMPY_REQUIRED_FOR_NON_16BIT_WAV",
                "Only 16-bit PCM fallback decoding is available without numpy.",
                f"sample_width={sample_width}",
                "Install numpy or provide a 16-bit PCM WAV for full QC.",
                findings,
                affected_file=str(path),
            )
            raise ValueError("numpy is required for this WAV format")
        values = struct.unpack("<" + "h" * (len(raw) // 2), raw)
        samples = [sample / 32768.0 for sample in values]
        frames = [samples[index : index + channels] for index in range(0, len(samples), channels)]
        return sample_rate, channels, frames

    if sample_width == 1:
        data = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
        data = (data - 128.0) / 128.0
    elif sample_width == 2:
        data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif sample_width == 3:
        bytes_data = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        signed = (
            bytes_data[:, 0].astype(np.int32)
            | (bytes_data[:, 1].astype(np.int32) << 8)
            | (bytes_data[:, 2].astype(np.int32) << 16)
        )
        signed = np.where(signed & 0x800000, signed - 0x1000000, signed)
        data = signed.astype(np.float32) / 8388608.0
    elif sample_width == 4:
        data = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        add_finding(
            "FAIL",
            "UNSUPPORTED_WAV_WIDTH",
            "Unsupported PCM sample width.",
            f"sample_width={sample_width}",
            "Convert to 16, 24, or 32-bit PCM WAV and rerun QC.",
            findings,
            affected_file=str(path),
        )
        raise ValueError(f"Unsupported WAV width: {sample_width}")

    if len(data) % channels:
        data = data[: len(data) - (len(data) % channels)]
    return sample_rate, channels, data.reshape((-1, channels))


def _as_mono(samples: Any) -> Any:
    if np is None:
        return [sum(frame) / len(frame) for frame in samples]
    if samples.ndim == 1:
        return samples
    return np.mean(samples, axis=1)


def _rms(samples: Any) -> float:
    if np is None:
        flat = [value for frame in samples for value in (frame if isinstance(frame, list) else [frame])]
        return math.sqrt(sum(value * value for value in flat) / max(1, len(flat)))
    return float(np.sqrt(np.mean(np.square(samples), dtype=np.float64)))


def _peak(samples: Any) -> float:
    if np is None:
        flat = [value for frame in samples for value in (frame if isinstance(frame, list) else [frame])]
        return max((abs(value) for value in flat), default=0.0)
    return float(np.max(np.abs(samples))) if samples.size else 0.0


def _approx_true_peak(samples: Any) -> float | None:
    if np is None:
        return None
    if samples.shape[0] < 2:
        return _peak(samples)
    midpoint = (samples[:-1] + samples[1:]) * 0.5
    return max(_peak(samples), float(np.max(np.abs(midpoint))))


def _band_metrics(samples: Any, sample_rate: int) -> dict[str, float | None]:
    results = {name: None for name in BANDS}
    results["spectral_centroid_hz"] = None
    if np is None:
        return results

    mono = _as_mono(samples).astype(np.float64, copy=False)
    if mono.size < 32 or sample_rate <= 0:
        return results
    mono = mono - float(np.mean(mono))
    window = np.hanning(mono.size)
    spectrum = np.fft.rfft(mono * window)
    power = np.square(np.abs(spectrum))
    freqs = np.fft.rfftfreq(mono.size, 1.0 / sample_rate)
    total_power = float(np.sum(power)) + EPS
    results["spectral_centroid_hz"] = float(np.sum(freqs * power) / total_power)
    for name, (low, high) in BANDS.items():
        mask = (freqs >= low) & (freqs < high)
        band_power = float(np.sum(power[mask])) + EPS
        results[name] = 10.0 * math.log10(band_power / total_power + EPS)
    return results


def _side_mid_ratio_db(samples: Any, channels: int) -> float | None:
    if np is None or channels < 2:
        return None
    left = samples[:, 0]
    right = samples[:, 1]
    mid = (left + right) * 0.5
    side = (left - right) * 0.5
    return _db(_rms(side) / max(_rms(mid), EPS))


def _transient_proxy(samples: Any, sample_rate: int) -> float | None:
    if np is None:
        return None
    mono = _as_mono(samples)
    if mono.size < 2:
        return 0.0
    diff = np.abs(np.diff(mono))
    return float(np.percentile(diff, 95))


def _noise_floor_proxy_dbfs(samples: Any, sample_rate: int) -> float | None:
    mono = _as_mono(samples)
    if np is None:
        if not mono:
            return None
        return _db(math.sqrt(sum(value * value for value in mono) / len(mono)))
    if mono.size == 0:
        return None
    frame_len = max(64, int(sample_rate * 0.05))
    if mono.size < frame_len:
        return _db(_rms(mono))
    frame_count = mono.size // frame_len
    trimmed = mono[: frame_count * frame_len].reshape(frame_count, frame_len)
    frame_rms = np.sqrt(np.mean(np.square(trimmed), axis=1))
    return _db(float(np.percentile(frame_rms, 10)))


def _integrated_loudness(samples: Any, sample_rate: int, findings: list[Finding], path: Path) -> float | None:
    if np is None or pyln is None:
        add_finding(
            "WARN",
            "INTEGRATED_LOUDNESS_UNAVAILABLE",
            "Integrated loudness was not calculated because optional dependency pyloudnorm is unavailable.",
            "pyloudnorm import failed or numpy is unavailable.",
            "Install pyloudnorm in the harness environment, then rerun before/after QC.",
            findings,
            affected_file=str(path),
            failed_assumption="Integrated LUFS is available for QC.",
            command_to_rerun="python3 -m harness.audio_qc --before BEFORE.wav --after AFTER.wav --json",
        )
        return None
    try:
        meter = pyln.Meter(sample_rate)
        return float(meter.integrated_loudness(samples))
    except Exception as exc:
        add_finding(
            "WARN",
            "INTEGRATED_LOUDNESS_FAILED",
            "Integrated loudness calculation failed.",
            str(exc),
            "Inspect the WAV format or calculate LUFS with an external meter, then attach the result.",
            findings,
            affected_file=str(path),
        )
        return None


def analyze_file(path: str | Path, findings: list[Finding] | None = None) -> dict[str, Any]:
    findings = findings if findings is not None else []
    audio_path = Path(path)
    sample_rate, channels, samples = _read_wav_pcm(audio_path, findings)
    duration = (samples.shape[0] if np is not None else len(samples)) / max(1, sample_rate)
    peak = _peak(samples)
    rms = _rms(samples)
    true_peak = _approx_true_peak(samples)
    band_values = _band_metrics(samples, sample_rate)
    metrics: dict[str, Any] = {
        "file": str(audio_path),
        "duration_sec": round(duration, 6),
        "sample_rate_hz": int(sample_rate),
        "channels": int(channels),
        "integrated_loudness_lufs": _integrated_loudness(samples, sample_rate, findings, audio_path),
        "peak_dbfs": _db(peak),
        "approx_true_peak_dbfs": _db(true_peak) if true_peak is not None else None,
        "rms_dbfs": _db(rms),
        "crest_factor_db": _db(peak) - _db(rms),
        "side_mid_ratio_db": _side_mid_ratio_db(samples, channels),
        "transient_proxy": _transient_proxy(samples, sample_rate),
        "silence_noise_floor_proxy_dbfs": _noise_floor_proxy_dbfs(samples, sample_rate),
    }
    metrics.update(band_values)
    if np is None:
        add_finding(
            "WARN",
            "SPECTRAL_METRICS_UNAVAILABLE",
            "Spectral, transient, and stereo metrics were not fully calculated because numpy is unavailable.",
            "numpy import failed.",
            "Install numpy or run QC in the bundled Python environment.",
            findings,
            affected_file=str(audio_path),
        )
    if duration <= 0.0:
        add_finding(
            "FAIL",
            "AUDIO_DURATION_INVALID",
            "Audio duration is not plausible.",
            f"duration_sec={duration}",
            "Re-export the WAV and rerun QC.",
            findings,
            affected_file=str(audio_path),
        )
    return metrics


def _target(profile: dict[str, Any] | None, key: str) -> float:
    if profile and key in profile:
        return float(profile[key])
    return float(DEFAULT_TARGETS[key])


def compare_before_after(
    before: str | Path,
    after: str | Path,
    findings: list[Finding] | None = None,
    *,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    findings = findings if findings is not None else []
    before_metrics = analyze_file(before, findings)
    after_metrics = analyze_file(after, findings)
    comparison: dict[str, Any] = {
        "before": before_metrics,
        "after": after_metrics,
        "delta": {},
    }
    before_duration = float(before_metrics["duration_sec"])
    after_duration = float(after_metrics["duration_sec"])
    duration_delta = after_duration - before_duration
    comparison["delta"]["duration_sec"] = duration_delta
    allowed_duration_delta = max(
        _target(profile, "max_duration_delta_sec"),
        before_duration * _target(profile, "max_duration_delta_ratio"),
    )
    if abs(duration_delta) > allowed_duration_delta:
        add_finding(
            "FAIL",
            "OUTPUT_DURATION_MISMATCH",
            "Output duration differs from source beyond tolerance.",
            f"before={before_duration:.3f}s after={after_duration:.3f}s tolerance={allowed_duration_delta:.3f}s",
            "Fix source selection, render bounds, or sample-rate conversion; rerun before/after QC.",
            findings,
            affected_file=str(after),
            failed_assumption="Before and after files represent the same complete song section.",
            command_to_rerun=f"python3 -m harness.audio_qc --before {before} --after {after} --json",
            human_listening_required=True,
        )

    true_peak = after_metrics.get("approx_true_peak_dbfs")
    target_tp = _target(profile, "true_peak_target_dbfs")
    if true_peak is not None and float(true_peak) > target_tp:
        add_finding(
            "FAIL",
            "TRUE_PEAK_TARGET_EXCEEDED",
            "Output exceeds the true-peak target.",
            f"approx_true_peak_dbfs={true_peak:.2f}, target={target_tp:.2f}",
            "Lower limiter ceiling or output trim, re-render, and rerun QC.",
            findings,
            affected_file=str(after),
            failed_assumption="Printed master is true-peak safe.",
            command_to_rerun=f"python3 -m harness.audio_qc --before {before} --after {after} --json",
            human_listening_required=True,
        )
    if float(after_metrics["peak_dbfs"]) >= -0.05:
        add_finding(
            "FAIL",
            "SAMPLE_PEAK_CLIPPING_RISK",
            "Output peak is at or near digital full scale.",
            f"peak_dbfs={after_metrics['peak_dbfs']:.2f}",
            "Lower output ceiling, avoid codec clipping, and re-render.",
            findings,
            affected_file=str(after),
            failed_assumption="Render does not clip.",
            command_to_rerun=f"python3 -m harness.audio_qc --before {before} --after {after} --json",
            human_listening_required=True,
        )

    for key in (
        "integrated_loudness_lufs",
        "rms_dbfs",
        "crest_factor_db",
        "spectral_centroid_hz",
        "low_band_energy_db",
        "low_mid_mud_band_db",
        "vocal_presence_band_db",
        "harshness_band_db",
        "sibilance_band_db",
        "air_fizz_band_db",
        "side_mid_ratio_db",
        "transient_proxy",
        "silence_noise_floor_proxy_dbfs",
    ):
        before_value = before_metrics.get(key)
        after_value = after_metrics.get(key)
        if before_value is not None and after_value is not None:
            comparison["delta"][key] = float(after_value) - float(before_value)

    brightness_delta = comparison["delta"].get("air_fizz_band_db")
    if brightness_delta is not None and brightness_delta < -_target(profile, "max_acceptable_brightness_loss_db"):
        add_finding(
            "WARN",
            "BRIGHTNESS_LOSS_SUSPICIOUS",
            "DeAI or cleanup may have reduced air/fizz brightness beyond the accepted guard.",
            f"air_fizz_delta_db={brightness_delta:.2f}",
            "Reduce DeAI intensity, restore controlled air, then rerun QC and human A/B.",
            findings,
            affected_file=str(after),
            failed_assumption="Noise reduction preserved vocal intelligibility and top-end life.",
            command_to_rerun=f"python3 -m harness.audio_qc --before {before} --after {after} --json",
            human_listening_required=True,
        )

    before_transient = before_metrics.get("transient_proxy")
    after_transient = after_metrics.get("transient_proxy")
    if before_transient and after_transient is not None:
        ratio = float(after_transient) / max(float(before_transient), EPS)
        comparison["delta"]["transient_ratio"] = ratio
        if ratio < 1.0 - _target(profile, "max_acceptable_transient_loss_ratio"):
            add_finding(
                "WARN",
                "TRANSIENT_LOSS_SUSPICIOUS",
                "Transient proxy dropped beyond the accepted guard.",
                f"before={before_transient:.6f} after={after_transient:.6f} ratio={ratio:.3f}",
                "Back off compression/DeAI/limiting, render a punch-preserve candidate, and rerun QC.",
                findings,
                affected_file=str(after),
                failed_assumption="Processing preserved punch.",
                command_to_rerun=f"python3 -m harness.audio_qc --before {before} --after {after} --json",
                human_listening_required=True,
            )

    side_mid_delta = comparison["delta"].get("side_mid_ratio_db")
    if side_mid_delta is not None and abs(side_mid_delta) > _target(profile, "max_acceptable_side_mid_change_db"):
        add_finding(
            "WARN",
            "SIDE_MID_CHANGE_SUSPICIOUS",
            "Stereo side/mid ratio changed beyond the accepted guard.",
            f"side_mid_delta_db={side_mid_delta:.2f}",
            "Audit M/S EQ and stereo width processing; rerun QC and mono/stereo listening.",
            findings,
            affected_file=str(after),
            failed_assumption="Stereo image was preserved intentionally.",
            command_to_rerun=f"python3 -m harness.audio_qc --before {before} --after {after} --json",
            human_listening_required=True,
        )

    comparison["max_severity"] = max_severity(findings)
    comparison["claim_status"] = "not_final_warn_plus" if has_warn_plus(findings) else "qc_passed_for_metrics_available"
    return comparison


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run before/after audio QC for WAV files.")
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    findings: list[Finding] = []
    comparison = compare_before_after(args.before, args.after, findings)
    payload = {"comparison": comparison, "findings": findings_to_dicts(findings)}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"max_severity={max_severity(findings)} claim_status={comparison['claim_status']}")
    return 2 if has_warn_plus(findings) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
