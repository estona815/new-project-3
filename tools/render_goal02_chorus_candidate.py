#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy import signal
from scipy.io import wavfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "configs" / "goal02_8_reference_manifest.json"
DEFAULT_ANALYSIS = ROOT / "reports" / "goal02_8_reference_match" / "goal02_reference_match.json"
DEFAULT_RENDER_DIR = ROOT / "renders" / "goal02_chorus_v01"
DEFAULT_REPORT_DIR = ROOT / "reports" / "goal02_chorus_v01"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def db_to_linear(db: float) -> float:
    return 10.0 ** (db / 20.0)


def linear_to_db(value: float | None, floor: float = -120.0) -> float:
    if value is None or value <= 1.0e-12 or not math.isfinite(value):
        return floor
    return 20.0 * math.log10(float(value))


def normalize_audio_array(data: Any) -> np.ndarray:
    data = np.asarray(data)
    if data.ndim == 1:
        data = data[:, None]
    if data.dtype.kind == "f":
        return data.astype(np.float64)
    if data.dtype.kind == "u":
        midpoint = float(np.iinfo(data.dtype).max + 1) / 2.0
        return (data.astype(np.float64) - midpoint) / midpoint
    if data.dtype.kind == "i":
        peak = float(np.max(np.abs(data))) if data.size else 0.0
        if data.dtype == np.int32 and peak > 32768.0:
            scale = float(2**31)
        else:
            info = np.iinfo(data.dtype)
            scale = float(max(abs(info.min), info.max))
        return data.astype(np.float64) / max(scale, 1.0)
    return data.astype(np.float64)


def resolve_path(root: Path, value: str | None) -> Path:
    if not value:
        raise ValueError("empty path")
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path


def read_wav_slice(path: Path, start_seconds: float, duration_seconds: float | None = None) -> tuple[int, np.ndarray]:
    try:
        sample_rate, data = wavfile.read(str(path), mmap=True)
    except Exception:
        sample_rate, data = wavfile.read(str(path), mmap=False)
    start = max(0, int(round(start_seconds * sample_rate)))
    stop = data.shape[0] if duration_seconds is None else start + max(1, int(round(duration_seconds * sample_rate)))
    sliced = normalize_audio_array(data[start:stop])
    if sliced.shape[1] == 1:
        sliced = np.repeat(sliced, 2, axis=1)
    return int(sample_rate), np.clip(sliced[:, :2], -8.0, 8.0)


def write_float_wav(path: Path, sample_rate: int, data: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(path), int(sample_rate), np.asarray(np.clip(data, -1.0, 1.0), dtype=np.float32))


def pad_or_trim(data: np.ndarray, frames: int) -> np.ndarray:
    if data.shape[0] == frames:
        return data
    if data.shape[0] > frames:
        return data[:frames]
    pad = np.zeros((frames - data.shape[0], data.shape[1]), dtype=data.dtype)
    return np.vstack([data, pad])


def sos_filter(data: np.ndarray, sample_rate: int, kind: str, cutoff: float | tuple[float, float], order: int = 2) -> np.ndarray:
    nyq = sample_rate * 0.5
    if isinstance(cutoff, tuple):
        low = max(20.0, min(cutoff[0], nyq - 100.0))
        high = max(low + 20.0, min(cutoff[1], nyq - 50.0))
        wn: float | list[float] = [low / nyq, high / nyq]
    else:
        wn = max(20.0, min(float(cutoff), nyq - 50.0)) / nyq
    sos = signal.butter(order, wn, btype=kind, output="sos")
    try:
        return signal.sosfiltfilt(sos, data, axis=0).astype(np.float64)
    except ValueError:
        return signal.sosfilt(sos, data, axis=0).astype(np.float64)


def highpass(data: np.ndarray, sample_rate: int, hz: float, order: int = 2) -> np.ndarray:
    return sos_filter(data, sample_rate, "highpass", hz, order)


def lowpass(data: np.ndarray, sample_rate: int, hz: float, order: int = 2) -> np.ndarray:
    return sos_filter(data, sample_rate, "lowpass", hz, order)


def bandpass(data: np.ndarray, sample_rate: int, low_hz: float, high_hz: float, order: int = 2) -> np.ndarray:
    return sos_filter(data, sample_rate, "bandpass", (low_hz, high_hz), order)


def db_gain(data: np.ndarray, gain_db: float) -> np.ndarray:
    return data * db_to_linear(gain_db)


def mid_side(data: np.ndarray, side_gain_db: float = 0.0, mid_gain_db: float = 0.0) -> np.ndarray:
    left = data[:, 0]
    right = data[:, 1]
    mid = (left + right) * 0.5 * db_to_linear(mid_gain_db)
    side = (left - right) * 0.5 * db_to_linear(side_gain_db)
    return np.column_stack([mid + side, mid - side])


def mono_below(data: np.ndarray, sample_rate: int, cutoff_hz: float = 120.0) -> np.ndarray:
    low = lowpass(data, sample_rate, cutoff_hz, 3)
    high = data - low
    mono_low = np.mean(low, axis=1, keepdims=True)
    return high + np.repeat(mono_low, 2, axis=1)


def soft_clip(data: np.ndarray, drive: float = 1.5) -> np.ndarray:
    drive = max(1.0, float(drive))
    return np.tanh(data * drive) / np.tanh(drive)


def simple_compressor(
    data: np.ndarray,
    sample_rate: int,
    threshold_db: float,
    ratio: float,
    attack_ms: float,
    release_ms: float,
    makeup_db: float = 0.0,
) -> np.ndarray:
    detector = np.max(np.abs(data), axis=1)
    attack_coeff = math.exp(-1.0 / max(1.0, sample_rate * attack_ms / 1000.0))
    release_coeff = math.exp(-1.0 / max(1.0, sample_rate * release_ms / 1000.0))
    env = np.zeros_like(detector)
    current = 0.0
    for index, value in enumerate(detector):
        coeff = attack_coeff if value > current else release_coeff
        current = coeff * current + (1.0 - coeff) * value
        env[index] = current
    level_db = np.array([linear_to_db(value) for value in env])
    over = np.maximum(0.0, level_db - threshold_db)
    gain_db = -(over - over / max(ratio, 1.0)) + makeup_db
    gain = np.power(10.0, gain_db / 20.0)
    return data * gain[:, None]


def band_trim(data: np.ndarray, sample_rate: int, low_hz: float, high_hz: float, trim_db: float) -> np.ndarray:
    band = bandpass(data, sample_rate, low_hz, high_hz, 2)
    return data + band * (db_to_linear(trim_db) - 1.0)


def rms(data: np.ndarray) -> float:
    mono = np.mean(data, axis=1)
    return float(np.sqrt(np.mean(np.square(mono)))) if mono.size else 0.0


def peak(data: np.ndarray) -> float:
    return float(np.max(np.abs(data))) if data.size else 0.0


def true_peak_estimate(data: np.ndarray) -> float:
    try:
        up = signal.resample_poly(data, 4, 1, axis=0)
        return peak(up)
    except Exception:
        return peak(data)


def limit_peak(data: np.ndarray, ceiling_db: float = -1.0) -> np.ndarray:
    limit = db_to_linear(ceiling_db)
    current = peak(data)
    if current > limit:
        return data * (limit / max(current, 1.0e-12))
    return data


def limit_true_peak_estimate(data: np.ndarray, ceiling_db: float = -1.0) -> np.ndarray:
    limit = db_to_linear(ceiling_db)
    current = true_peak_estimate(data)
    if current > limit:
        return data * (limit / max(current, 1.0e-12))
    return data


def rms_match_to(source: np.ndarray, target_rms_db: float, max_gain_db: float = 24.0) -> np.ndarray:
    current_db = linear_to_db(rms(source))
    gain_db = max(-max_gain_db, min(max_gain_db, target_rms_db - current_db))
    return db_gain(source, gain_db)


def band_energy_ratio(mono: np.ndarray, sample_rate: int, low_hz: float, high_hz: float) -> float:
    if mono.size <= 1:
        return 0.0
    centered = mono - float(np.mean(mono))
    spectrum = np.abs(np.fft.rfft(centered * np.hanning(centered.size))) ** 2
    freqs = np.fft.rfftfreq(centered.size, 1.0 / sample_rate)
    total = float(np.sum(spectrum)) or 1.0
    return float(np.sum(spectrum[(freqs >= low_hz) & (freqs < high_hz)]) / total)


def spectral_centroid_rolloff(mono: np.ndarray, sample_rate: int) -> tuple[float, float]:
    if mono.size <= 1:
        return 0.0, 0.0
    centered = mono - float(np.mean(mono))
    spectrum = np.abs(np.fft.rfft(centered * np.hanning(centered.size)))
    freqs = np.fft.rfftfreq(centered.size, 1.0 / sample_rate)
    total = float(np.sum(spectrum))
    if total <= 0.0:
        return 0.0, 0.0
    centroid = float(np.sum(freqs * spectrum) / total)
    cumsum = np.cumsum(spectrum)
    roll_idx = int(np.searchsorted(cumsum, total * 0.85))
    return centroid, float(freqs[min(roll_idx, len(freqs) - 1)])


def transient_density_per_second(mono: np.ndarray, sample_rate: int) -> float:
    if mono.size < 3:
        return 0.0
    diff = np.abs(np.diff(mono))
    threshold = max(float(np.percentile(diff, 98.5)), float(np.median(diff)) + 8.0 * float(np.median(np.abs(diff - np.median(diff)))) + 1.0e-12)
    hits = np.flatnonzero(diff >= threshold)
    if hits.size == 0:
        return 0.0
    min_gap = max(1, int(round(sample_rate * 0.018)))
    grouped = 1
    last = int(hits[0])
    for hit in hits[1:]:
        if int(hit) - last >= min_gap:
            grouped += 1
            last = int(hit)
    return float(grouped / max(mono.size / sample_rate, 1.0e-9))


def metrics(name: str, data: np.ndarray, sample_rate: int, path: Path | None = None) -> dict[str, Any]:
    mono = np.mean(data, axis=1)
    pk = peak(data)
    tp = true_peak_estimate(data)
    rm = rms(data)
    corr: float | None
    if data.shape[1] >= 2 and np.std(data[:, 0]) > 1.0e-12 and np.std(data[:, 1]) > 1.0e-12:
        corr = float(np.corrcoef(data[:, 0], data[:, 1])[0, 1])
    else:
        corr = None
    centroid, rolloff = spectral_centroid_rolloff(mono, sample_rate)
    peak_density = float(np.mean(np.abs(data) >= db_to_linear(-1.0)) * 100.0)
    return {
        "name": name,
        "path": str(path) if path else "",
        "sample_rate": sample_rate,
        "channels": int(data.shape[1]),
        "duration_seconds": round(data.shape[0] / sample_rate, 3),
        "rms_dbfs": round(linear_to_db(rm), 3),
        "sample_peak_dbfs": round(linear_to_db(pk), 3),
        "true_peak_estimate_4x_dbTP": round(linear_to_db(tp), 3),
        "crest_factor_db": round(linear_to_db(pk / max(rm, 1.0e-12)), 3),
        "peak_density_over_minus1db_pct": round(peak_density, 6),
        "transient_density_per_second": round(transient_density_per_second(mono, sample_rate), 6),
        "spectral_centroid_hz": round(centroid, 3),
        "spectral_rolloff_hz": round(rolloff, 3),
        "low_energy_ratio_20_120": round(band_energy_ratio(mono, sample_rate, 20.0, 120.0), 6),
        "low_mid_energy_ratio_120_350": round(band_energy_ratio(mono, sample_rate, 120.0, 350.0), 6),
        "mid_energy_ratio_350_2500": round(band_energy_ratio(mono, sample_rate, 350.0, 2500.0), 6),
        "presence_energy_ratio_2500_6000": round(band_energy_ratio(mono, sample_rate, 2500.0, 6000.0), 6),
        "sibilance_energy_ratio_5000_10000": round(band_energy_ratio(mono, sample_rate, 5000.0, 10000.0), 6),
        "air_energy_ratio_10000_16000": round(band_energy_ratio(mono, sample_rate, 10000.0, 16000.0), 6),
        "high_energy_ratio_2500_16000": round(band_energy_ratio(mono, sample_rate, 2500.0, 16000.0), 6),
        "stereo_correlation": round(corr, 6) if corr is not None else None,
        "integrated_lufs": None,
        "integrated_lufs_status": "unavailable_pyloudnorm_not_installed",
    }


def stem_role(path: Path) -> str:
    name = path.stem.lower()
    if name.startswith("0 "):
        return "full_mix_reference_excluded"
    if "bass" in name or "808" in name:
        return "bass"
    if "drum" in name:
        return "drums"
    if "vocal" in name or "backing" in name:
        return "vocals"
    if "fx" in name:
        return "fx"
    if "synth" in name:
        return "synth"
    if "keyboard" in name:
        return "keyboard"
    if "guitar" in name:
        return "guitar"
    return "music"


def process_vocals(vocals: list[np.ndarray], sample_rate: int, frames: int) -> np.ndarray:
    if not vocals:
        return np.zeros((frames, 2), dtype=np.float64)
    bus = sum(pad_or_trim(item, frames) for item in vocals)
    bus = band_trim(bus, sample_rate, 220.0, 350.0, -1.3)
    bus = band_trim(bus, sample_rate, 5000.0, 10000.0, -1.0)
    bus = simple_compressor(bus, sample_rate, threshold_db=-25.0, ratio=2.1, attack_ms=8.0, release_ms=120.0, makeup_db=4.5)
    return limit_peak(bus, -4.0)


def process_bass(items: list[np.ndarray], sample_rate: int, frames: int) -> np.ndarray:
    if not items:
        return np.zeros((frames, 2), dtype=np.float64)
    bus = sum(pad_or_trim(item, frames) for item in items)
    bus = mono_below(bus, sample_rate, 140.0)
    sub = lowpass(bus, sample_rate, 140.0, 3)
    harmonic = highpass(soft_clip(bus * 3.0, 1.6), sample_rate, 130.0, 2)
    harmonic = lowpass(harmonic, sample_rate, 2600.0, 2)
    bus = db_gain(sub, 6.5) + harmonic * 0.22
    bus = simple_compressor(bus, sample_rate, threshold_db=-19.0, ratio=1.6, attack_ms=18.0, release_ms=90.0, makeup_db=0.5)
    return limit_peak(soft_clip(bus, 1.25), -3.0)


def process_drums(items: list[np.ndarray], sample_rate: int, frames: int) -> np.ndarray:
    if not items:
        return np.zeros((frames, 2), dtype=np.float64)
    bus = sum(pad_or_trim(item, frames) for item in items)
    bus = db_gain(bus, 3.5)
    bus = band_trim(bus, sample_rate, 6000.0, 10000.0, -0.8)
    bus = soft_clip(bus, 1.55)
    return limit_peak(bus, -3.2)


def process_music(groups: dict[str, list[np.ndarray]], sample_rate: int, frames: int) -> tuple[np.ndarray, list[dict[str, Any]]]:
    trace: list[dict[str, Any]] = []
    bus = np.zeros((frames, 2), dtype=np.float64)
    for role in ("fx", "synth", "keyboard", "guitar", "music"):
        for item in groups.get(role, []):
            stem = pad_or_trim(item, frames)
            if role == "fx":
                stem = highpass(stem, sample_rate, 220.0, 2)
                stem = lowpass(stem, sample_rate, 9500.0, 2)
                stem = mid_side(stem, side_gain_db=-8.0)
                stem = db_gain(stem, -6.0)
            elif role == "keyboard":
                stem = highpass(stem, sample_rate, 160.0, 2)
                stem = mid_side(stem, side_gain_db=-7.0)
                stem = db_gain(stem, -5.0)
            elif role == "synth":
                stem = highpass(stem, sample_rate, 120.0, 2)
                stem = band_trim(stem, sample_rate, 220.0, 350.0, -1.5)
                stem = band_trim(stem, sample_rate, 700.0, 1500.0, -1.2)
                stem = mid_side(stem, side_gain_db=-3.0)
                stem = db_gain(stem, -1.0)
            else:
                stem = highpass(stem, sample_rate, 120.0, 2)
                stem = db_gain(stem, -3.0)
            bus += stem
            trace.append({"role": role, "action": "phase_safe_music_fx_processing"})
    return bus, trace


def master_bus(mix: np.ndarray, sample_rate: int) -> np.ndarray:
    mix = mono_below(mix, sample_rate, 120.0)
    mix = band_trim(mix, sample_rate, 120.0, 350.0, -0.8)
    mix = simple_compressor(mix, sample_rate, threshold_db=-17.5, ratio=1.35, attack_ms=20.0, release_ms=180.0, makeup_db=1.6)
    mix = soft_clip(mix, 1.45)
    current_rms = linear_to_db(rms(mix))
    gain_db = min(10.0, -10.8 - current_rms)
    mix = db_gain(mix, gain_db)
    mix = soft_clip(mix, 1.15)
    return limit_true_peak_estimate(limit_peak(mix, -1.2), -1.0)


def build_candidate(stems: dict[str, list[np.ndarray]], sample_rate: int, frames: int) -> tuple[np.ndarray, list[dict[str, Any]], dict[str, dict[str, Any]]]:
    trace: list[dict[str, Any]] = [
        {"stage": "policy", "action": "excluded_full_mix_stem_from_active_candidate_path"},
        {"stage": "policy", "action": "python_dsp_preview_not_reaper_runtime_plugin_trace"},
    ]
    vocal_bus = process_vocals(stems.get("vocals", []), sample_rate, frames)
    bass_bus = process_bass(stems.get("bass", []), sample_rate, frames)
    drum_bus = process_drums(stems.get("drums", []), sample_rate, frames)
    music_bus, music_trace = process_music(stems, sample_rate, frames)
    trace.extend(
        [
            {"stage": "vox_bus", "chain": "de-mud -> de-ess -> compressor -> output guard", "implemented_as": "python_dsp_preview"},
            {"stage": "808_bass_bus", "chain": "mono low -> harmonic saturation -> compression -> clip guard", "implemented_as": "python_dsp_preview"},
            {"stage": "drum_bus", "chain": "gain -> high guard -> soft clip", "implemented_as": "python_dsp_preview"},
            {"stage": "music_bus", "chain": "phase-safe filtering, side trim, low-mid trim", "implemented_as": "python_dsp_preview"},
            *music_trace,
        ]
    )
    premaster = vocal_bus + bass_bus + drum_bus + music_bus
    candidate = master_bus(premaster, sample_rate)
    trace.append({"stage": "master_bus", "chain": "mono low -> low-mid trim -> glue -> clip -> peak guard", "implemented_as": "python_dsp_preview"})
    bus_metrics = {
        "vocal_bus": metrics("vocal_bus", vocal_bus, sample_rate),
        "bass_bus": metrics("bass_bus", bass_bus, sample_rate),
        "drum_bus": metrics("drum_bus", drum_bus, sample_rate),
        "music_bus": metrics("music_bus", music_bus, sample_rate),
        "premaster": metrics("premaster", premaster, sample_rate),
    }
    return candidate, trace, bus_metrics


def concatenate_with_silence(items: list[np.ndarray], sample_rate: int, silence_seconds: float = 0.4) -> np.ndarray:
    silence = np.zeros((int(round(sample_rate * silence_seconds)), 2), dtype=np.float64)
    parts: list[np.ndarray] = []
    for index, item in enumerate(items):
        if index:
            parts.append(silence)
        parts.append(item)
    return np.vstack(parts) if parts else silence


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, result: dict[str, Any]) -> None:
    m = {row["name"]: row for row in result["metrics"]}
    lines = [
        "# GOAL 02 Chorus v01 Python DSP Preview QC",
        "",
        f"- Created UTC: `{result['created_at']}`",
        f"- Status: `{result['status']}`",
        f"- Target window: `{result['target_window']['start_seconds']}`s to `{result['target_window']['end_seconds']}`s",
        "- Claim policy: `preview render only; not a REAPER runtime render; no listening claims`",
        "",
        "## Files",
        "",
    ]
    for label, value in result["files"].items():
        lines.append(f"- {label}: `{value}`")
    lines.extend(
        [
            "",
            "## Metrics",
            "",
            "| item | rms dBFS | sample peak | true peak est | crest | peak density | corr | low 20-120 | low-mid 120-350 | high 2.5-16k |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name in ("current_target", "candidate_pydsp_preview", "ref_06_matched", "ref_07_matched", "ref_03_matched"):
        row = m.get(name)
        if not row:
            continue
        lines.append(
            f"| `{name}` | `{row['rms_dbfs']}` | `{row['sample_peak_dbfs']}` | `{row['true_peak_estimate_4x_dbTP']}` | `{row['crest_factor_db']}` | `{row['peak_density_over_minus1db_pct']}` | `{row['stereo_correlation']}` | `{row['low_energy_ratio_20_120']}` | `{row['low_mid_energy_ratio_120_350']}` | `{row['high_energy_ratio_2500_16000']}` |"
        )
    lines.extend(
        [
            "",
            "## Processing Notes",
            "",
            "- The active candidate path excludes the raw full-mix stem and all reference audio.",
            "- References are only rendered as loudness/RMS-matched A/B comparison files.",
            "- The first-slot REAPER JSFX gate remains unverified for this preview; final delivery still needs actual REAPER runtime trace.",
            "- LUFS-I remains unavailable until `pyloudnorm`, REAPER metering, mvMeter2, or ClearMaster Audit evidence is collected.",
            "",
            "## Next REAPER Step",
            "",
            "Use this preview to transfer settings into the REAPER session, then render a REAPER print and run the Suno vocal chain gate plus final QC.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def render(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    manifest = load_json(args.manifest)
    analysis = load_json(args.analysis)
    render_dir = args.render_dir
    report_dir = args.report_dir
    if not render_dir.is_absolute():
        render_dir = root / render_dir
    if not report_dir.is_absolute():
        report_dir = root / report_dir

    target_start = float(analysis["target"]["analyzed_start_seconds"])
    duration = float(analysis["target"]["analyzed_duration_seconds"])
    target_path = resolve_path(root, manifest["target"]["path"])
    sample_rate, current = read_wav_slice(target_path, target_start, duration)
    frames = current.shape[0]

    stem_dir = resolve_path(root, manifest.get("target_stems", {}).get("path"))
    stems: dict[str, list[np.ndarray]] = {role: [] for role in ("vocals", "bass", "drums", "fx", "synth", "keyboard", "guitar", "music")}
    excluded_stems: list[str] = []
    for stem_path in sorted(stem_dir.glob("*.wav")):
        role = stem_role(stem_path)
        if role == "full_mix_reference_excluded":
            excluded_stems.append(str(stem_path))
            continue
        sr, stem_audio = read_wav_slice(stem_path, target_start, duration)
        if sr != sample_rate:
            raise RuntimeError(f"sample rate mismatch for {stem_path}: {sr} != {sample_rate}")
        stems.setdefault(role, []).append(pad_or_trim(stem_audio, frames))

    candidate, trace, bus_metrics = build_candidate(stems, sample_rate, frames)
    current = limit_true_peak_estimate(limit_peak(current, -1.2), -1.0)
    candidate = limit_true_peak_estimate(limit_peak(candidate, -1.2), -1.0)
    candidate_rms_db = linear_to_db(rms(candidate))

    files: dict[str, str] = {}
    current_path = render_dir / "goal02_chorus_v01_CURRENT_TARGET_20s.wav"
    candidate_path = render_dir / "goal02_chorus_v01_PYDSP_PREVIEW_20s.wav"
    write_float_wav(current_path, sample_rate, current)
    write_float_wav(candidate_path, sample_rate, candidate)
    files["current_target_20s"] = str(current_path)
    files["candidate_pydsp_preview_20s"] = str(candidate_path)

    metric_rows = [
        metrics("current_target", current, sample_rate, current_path),
        metrics("candidate_pydsp_preview", candidate, sample_rate, candidate_path),
    ]
    ab_items = [current, candidate]
    primary_ids = [item["id"] for item in analysis.get("primary_references", analysis.get("closest_references", [])[:3])]
    references_by_id = {row["id"]: row for row in analysis["references"]}
    manifest_refs_by_id = {row["id"]: row for row in manifest["references"]}
    for ref_id in primary_ids[:3]:
        ref_analysis = references_by_id[ref_id]
        ref_manifest = manifest_refs_by_id[ref_id]
        ref_path = resolve_path(root, ref_manifest["path"])
        ref_sr, ref_audio = read_wav_slice(ref_path, float(ref_analysis["analyzed_start_seconds"]), duration)
        if ref_sr != sample_rate:
            raise RuntimeError(f"reference sample rate mismatch for {ref_path}: {ref_sr} != {sample_rate}")
        ref_audio = pad_or_trim(ref_audio, frames)
        ref_matched = limit_true_peak_estimate(limit_peak(rms_match_to(ref_audio, candidate_rms_db, max_gain_db=18.0), -1.2), -1.0)
        ref_out = render_dir / f"goal02_chorus_v01_{ref_id.upper()}_RMS_MATCHED_TO_CANDIDATE_20s.wav"
        write_float_wav(ref_out, sample_rate, ref_matched)
        files[f"{ref_id}_rms_matched_20s"] = str(ref_out)
        metric_rows.append(metrics(f"{ref_id}_matched", ref_matched, sample_rate, ref_out))
        ab_items.extend([ref_matched, candidate])

    ab_path = render_dir / "goal02_chorus_v01_AB_CURRENT_CANDIDATE_PRIMARY_REFS.wav"
    ab_audio = limit_peak(concatenate_with_silence(ab_items, sample_rate), -1.0)
    write_float_wav(ab_path, sample_rate, ab_audio)
    files["ab_current_candidate_primary_refs"] = str(ab_path)
    metric_rows.append(metrics("ab_current_candidate_primary_refs", ab_audio, sample_rate, ab_path))

    trace_path = report_dir / "goal02_chorus_v01_pydsp_processing_trace.json"
    metrics_csv = report_dir / "goal02_chorus_v01_metrics.csv"
    qc_json = report_dir / "goal02_chorus_v01_qc.json"
    qc_md = report_dir / "goal02_chorus_v01_qc_report.md"

    result = {
        "schema": "goal02-chorus-pydsp-preview-v1",
        "created_at": now_utc(),
        "status": "PREVIEW_RENDERED_REAPER_RUNTIME_UNVERIFIED",
        "source_policy": {
            "excluded_full_mix_stems": excluded_stems,
            "references_not_in_active_candidate_path": True,
            "pydsp_preview_not_final_master": True,
            "no_listening_claims": True,
        },
        "target_window": {
            "start_seconds": target_start,
            "end_seconds": round(target_start + duration, 3),
            "duration_seconds": duration,
        },
        "primary_references": primary_ids[:3],
        "files": files,
        "metrics": metric_rows,
        "bus_metrics": bus_metrics,
        "processing_trace_path": str(trace_path),
        "remaining_gates": [
            "actual REAPER runtime plugin trace",
            "first-slot JS: Codex Vocal AI Artifact Split Tamer proof on main vocal",
            "mvMeter2/ClearMaster Audit LUFS-I and true-peak evidence",
            "user loudness-matched A/B approval",
        ],
    }
    report_dir.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(json.dumps({"schema": "goal02-pydsp-processing-trace-v1", "created_at": result["created_at"], "trace": trace}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv(metrics_csv, metric_rows)
    qc_json.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    write_report(qc_md, result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render GOAL 02 20-second Python DSP preview and reference A/B package.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--render-dir", type=Path, default=DEFAULT_RENDER_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = render(args)
    print(json.dumps({"status": result["status"], "files": result["files"], "report": str(args.report_dir)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
