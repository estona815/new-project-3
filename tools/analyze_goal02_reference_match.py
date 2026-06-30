#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "configs" / "goal02_8_reference_manifest.json"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "goal02_8_reference_match"
SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".aif", ".aiff", ".flac"}
REFERENCE_REQUIRED = 8


@dataclass(frozen=True)
class AudioSlice:
    data: Any
    sample_rate: int
    channels: int
    start_seconds: float
    duration_seconds: float


FEATURE_FIELDS = [
    "id",
    "role",
    "path",
    "status",
    "reason",
    "sample_rate",
    "channels",
    "window_selection",
    "analyzed_start_seconds",
    "analyzed_duration_seconds",
    "lufs_i",
    "sample_peak_dbfs",
    "rms_dbfs",
    "crest_factor_db",
    "peak_density_over_minus1db_pct",
    "transient_density_per_second",
    "spectral_centroid_hz",
    "spectral_rolloff_hz",
    "low_energy_ratio_20_120",
    "low_mid_energy_ratio_120_350",
    "mid_energy_ratio_350_2500",
    "presence_energy_ratio_2500_6000",
    "sibilance_energy_ratio_5000_10000",
    "air_energy_ratio_10000_16000",
    "high_energy_ratio_2500_16000",
    "stereo_correlation",
]

CANDIDATE_FIELDS = [
    "group",
    "path",
    "size_mb",
    "duration_seconds",
    "sample_rate",
    "channels",
    "reason",
]


COMPARISON_SCALES = {
    "lufs_i": 6.0,
    "rms_dbfs": 6.0,
    "crest_factor_db": 8.0,
    "peak_density_over_minus1db_pct": 8.0,
    "transient_density_per_second": 18.0,
    "spectral_centroid_hz": 2500.0,
    "spectral_rolloff_hz": 4000.0,
    "low_energy_ratio_20_120": 0.18,
    "low_mid_energy_ratio_120_350": 0.16,
    "mid_energy_ratio_350_2500": 0.25,
    "presence_energy_ratio_2500_6000": 0.16,
    "sibilance_energy_ratio_5000_10000": 0.08,
    "air_energy_ratio_10000_16000": 0.08,
    "high_energy_ratio_2500_16000": 0.22,
    "stereo_correlation": 0.50,
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dbfs(value: float | None) -> float | None:
    if value is None or value <= 0.0 or not math.isfinite(value):
        return None
    return 20.0 * math.log10(value)


def db_to_linear(db: float) -> float:
    return 10.0 ** (db / 20.0)


def finite_number(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def round_or_blank(value: float | None, digits: int = 6) -> float | str:
    if value is None or not math.isfinite(value):
        return ""
    return round(float(value), digits)


def parse_float_or_default(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def resolve_path(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path


def default_manifest(root: Path) -> dict[str, Any]:
    refs = []
    roles = [
        "primary_reference",
        "vocal_balance_reference",
        "low_end_reference",
        "drum_energy_reference",
        "width_reference",
        "loudness_reference",
        "emotional_reference",
        "secondary_primary_reference",
    ]
    for index, role in enumerate(roles, start=1):
        refs.append(
            {
                "id": f"ref_{index:02d}",
                "role": role,
                "path": f"input/reference/ref_{index:02d}.wav",
                "weight": 1.0,
                "notes": "",
            }
        )
    return {
        "schema": "automix-goal02-8-reference-manifest-v1",
        "created_at": now_utc(),
        "project_name": "GOAL 02 chorus 20-second reference match",
        "target_profile": "digicore_hyperpop_hiphop_vocal_forward",
        "analysis_window": {"label": "chorus_20s", "selection": "fixed_start", "start_seconds": 0.0, "duration_seconds": 20.0},
        "target": {
            "id": "target_chorus",
            "role": "current_mix_or_chorus_print",
            "path": "input/target/target_chorus.wav",
            "notes": "",
        },
        "target_stems": {"path": "", "window_source": "target_chorus", "notes": ""},
        "references_required": REFERENCE_REQUIRED,
        "references": refs,
        "safety_constraints": {
            "reference_bus_policy": "Reference/full-mix material must stay muted, master-send disabled, and outside active master routing.",
            "do_not_infer_listening": True,
            "do_not_fabricate_missing_metrics": True,
        },
    }


def load_manifest(root: Path, manifest_path: Path | None) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    path = manifest_path or DEFAULT_MANIFEST
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        warnings.append(f"manifest_missing_used_default_template:{path}")
        return default_manifest(root), warnings
    with path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    return manifest, warnings


def _decode_pcm(raw: bytes, sample_width: int) -> list[int]:
    if sample_width == 1:
        return [item - 128 for item in raw]
    if sample_width == 2:
        return [int.from_bytes(raw[i : i + 2], "little", signed=True) for i in range(0, len(raw), 2)]
    if sample_width == 3:
        out = []
        for i in range(0, len(raw), 3):
            chunk = raw[i : i + 3]
            sign = 0xFF if chunk[2] & 0x80 else 0x00
            out.append(int.from_bytes(chunk + bytes([sign]), "little", signed=True))
        return out
    if sample_width == 4:
        return [int.from_bytes(raw[i : i + 4], "little", signed=True) for i in range(0, len(raw), 4)]
    raise ValueError(f"unsupported WAV sample width: {sample_width}")


def normalize_audio_array(data: Any) -> Any:
    import numpy as np

    data = np.asarray(data)
    if data.ndim == 1:
        data = data[:, None]
    if data.dtype.kind == "f":
        return data.astype(float)
    if data.dtype.kind not in {"i", "u"}:
        return data.astype(float)
    if data.dtype.kind == "u":
        midpoint = float(np.iinfo(data.dtype).max + 1) / 2.0
        return (data.astype(float) - midpoint) / midpoint
    # scipy stores 24-bit PCM in int32 containers, usually left-justified.
    peak = float(np.max(np.abs(data))) if data.size else 0.0
    if data.dtype == np.int32 and peak > 32768.0:
        scale = float(2**31)
    else:
        scale = float(max(abs(np.iinfo(data.dtype).min), np.iinfo(data.dtype).max))
    return data.astype(float) / max(scale, 1.0)


def read_audio_slice_with_scipy(path: Path, start_seconds: float, duration_seconds: float | None) -> AudioSlice:
    import numpy as np
    from scipy.io import wavfile

    sample_rate, data = wavfile.read(str(path), mmap=False)
    data = normalize_audio_array(data)
    start_frame = max(0, int(round(start_seconds * sample_rate)))
    end_frame = data.shape[0] if duration_seconds is None else start_frame + max(1, int(round(duration_seconds * sample_rate)))
    sliced = np.asarray(data[start_frame:end_frame], dtype=float)
    actual_duration = float(sliced.shape[0] / sample_rate) if sample_rate else 0.0
    channels = int(sliced.shape[1]) if sliced.ndim == 2 else 1
    return AudioSlice(data=sliced, sample_rate=int(sample_rate), channels=channels, start_seconds=start_seconds, duration_seconds=actual_duration)


def read_audio_slice(path: Path, start_seconds: float, duration_seconds: float | None) -> AudioSlice:
    try:
        import numpy as np
        import soundfile as sf

        info = sf.info(str(path))
        sample_rate = int(info.samplerate)
        start_frame = max(0, int(round(start_seconds * sample_rate)))
        frames = -1 if duration_seconds is None else max(1, int(round(duration_seconds * sample_rate)))
        data, sample_rate = sf.read(str(path), start=start_frame, frames=frames, always_2d=True, dtype="float64")
        data = np.asarray(data, dtype=float)
        actual_duration = float(data.shape[0] / sample_rate) if sample_rate else 0.0
        return AudioSlice(data=data, sample_rate=int(sample_rate), channels=int(data.shape[1]), start_seconds=start_seconds, duration_seconds=actual_duration)
    except Exception:
        try:
            return read_audio_slice_with_scipy(path, start_seconds, duration_seconds)
        except Exception:
            pass
        if path.suffix.lower() != ".wav":
            raise

    import numpy as np

    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        sample_width = wf.getsampwidth()
        start_frame = max(0, int(round(start_seconds * sample_rate)))
        frame_count = wf.getnframes()
        if start_frame:
            wf.setpos(min(start_frame, frame_count))
        frames_to_read = frame_count - start_frame if duration_seconds is None else max(1, int(round(duration_seconds * sample_rate)))
        raw = wf.readframes(max(0, frames_to_read))

    ints = _decode_pcm(raw, sample_width)
    scale = float(2 ** (8 * sample_width - 1))
    usable = len(ints) - (len(ints) % channels)
    if usable <= 0:
        data = np.zeros((0, channels), dtype=float)
    else:
        data = np.asarray(ints[:usable], dtype=float).reshape((-1, channels)) / scale
        data = np.clip(data, -1.0, 1.0)
    actual_duration = float(data.shape[0] / sample_rate) if sample_rate else 0.0
    return AudioSlice(data=data, sample_rate=sample_rate, channels=channels, start_seconds=start_seconds, duration_seconds=actual_duration)


def empty_row(
    entry: dict[str, Any],
    path: Path | None,
    status: str,
    reason: str,
    start_seconds: float,
    duration_seconds: float | None,
    window_selection: str,
) -> dict[str, Any]:
    row = {field: "" for field in FEATURE_FIELDS}
    row.update(
        {
            "id": entry.get("id", ""),
            "role": entry.get("role", ""),
            "path": str(path or entry.get("path") or ""),
            "status": status,
            "reason": reason,
            "window_selection": window_selection,
            "analyzed_start_seconds": start_seconds,
            "analyzed_duration_seconds": duration_seconds if duration_seconds is not None else "",
        }
    )
    return row


def band_energy_ratio(mono: Any, sample_rate: int, low_hz: float, high_hz: float) -> float:
    import numpy as np

    if mono.size <= 1 or sample_rate <= 0:
        return 0.0
    centered = mono - float(np.mean(mono))
    windowed = centered * np.hanning(centered.size)
    spectrum = np.abs(np.fft.rfft(windowed)) ** 2
    freqs = np.fft.rfftfreq(centered.size, 1.0 / sample_rate)
    total = float(np.sum(spectrum)) or 1.0
    mask = (freqs >= low_hz) & (freqs < high_hz)
    return float(np.sum(spectrum[mask]) / total)


def spectral_centroid_rolloff(mono: Any, sample_rate: int) -> tuple[float | None, float | None, str]:
    import numpy as np

    if mono.size <= 1 or sample_rate <= 0:
        return None, None, "empty_audio"
    try:
        import librosa

        centroid = librosa.feature.spectral_centroid(y=mono.astype(float), sr=sample_rate)
        rolloff = librosa.feature.spectral_rolloff(y=mono.astype(float), sr=sample_rate, roll_percent=0.85)
        return float(np.nanmean(centroid)), float(np.nanmean(rolloff)), "librosa"
    except Exception as exc:
        centered = mono - float(np.mean(mono))
        spectrum = np.abs(np.fft.rfft(centered * np.hanning(centered.size)))
        freqs = np.fft.rfftfreq(centered.size, 1.0 / sample_rate)
        total = float(np.sum(spectrum))
        if total <= 0.0:
            return None, None, f"fft_fallback_silent:{exc}"
        centroid = float(np.sum(freqs * spectrum) / total)
        cumsum = np.cumsum(spectrum)
        idx = int(np.searchsorted(cumsum, total * 0.85))
        idx = min(idx, len(freqs) - 1)
        return centroid, float(freqs[idx]), f"fft_fallback:{exc}"


def transient_density_per_second(mono: Any, sample_rate: int) -> float:
    import numpy as np

    if mono.size < 3 or sample_rate <= 0:
        return 0.0
    diff = np.abs(np.diff(mono))
    if diff.size == 0:
        return 0.0
    median = float(np.median(diff))
    mad = float(np.median(np.abs(diff - median))) + 1.0e-12
    threshold = max(float(np.percentile(diff, 98.5)), median + 8.0 * mad, 0.01)
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
    duration = mono.size / sample_rate
    return float(grouped / max(duration, 1.0e-9))


def auto_loudest_window_start(path: Path, duration_seconds: float, fallback_start_seconds: float) -> tuple[float, str]:
    import numpy as np

    try:
        audio = read_audio_slice(path, 0.0, None)
    except Exception as exc:
        return fallback_start_seconds, f"auto_window_failed:{exc}"
    if audio.data.size == 0 or audio.sample_rate <= 0:
        return fallback_start_seconds, "auto_window_failed:empty_audio"
    frames = audio.data.shape[0]
    window_frames = max(1, int(round(duration_seconds * audio.sample_rate)))
    if frames <= window_frames:
        return 0.0, "auto_loudest_full_file_shorter_than_window"
    mono = np.mean(audio.data, axis=1)
    energy = np.square(mono.astype(float))
    cumsum = np.concatenate(([0.0], np.cumsum(energy)))
    hop = max(1, int(round(audio.sample_rate * 0.5)))
    starts = np.arange(0, frames - window_frames + 1, hop, dtype=int)
    if starts.size == 0 or starts[-1] != frames - window_frames:
        starts = np.append(starts, frames - window_frames)
    window_energy = (cumsum[starts + window_frames] - cumsum[starts]) / window_frames
    best = int(starts[int(np.argmax(window_energy))])
    return round(best / audio.sample_rate, 3), "auto_loudest_rms_20s"


def resolve_entry_window(path: Path | None, selection: str, start_seconds: float, duration_seconds: float | None) -> tuple[float, str]:
    if path is None or not path.exists() or duration_seconds is None:
        return start_seconds, selection
    if selection in {"auto_loudest", "auto_loudest_20s", "auto_loudest_20s_per_file"}:
        return auto_loudest_window_start(path, duration_seconds, start_seconds)
    return start_seconds, selection or "fixed_start"


def analyze_entry(
    entry: dict[str, Any],
    root: Path,
    start_seconds: float,
    duration_seconds: float | None,
    window_selection: str = "fixed_start",
) -> dict[str, Any]:
    import numpy as np

    path = resolve_path(root, entry.get("path"))
    if path is None:
        return empty_row(entry, path, "missing", "path not supplied", start_seconds, duration_seconds, window_selection)
    if not path.exists():
        return empty_row(entry, path, "missing", "file does not exist", start_seconds, duration_seconds, window_selection)
    if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        return empty_row(entry, path, "unsupported", f"unsupported extension {path.suffix}", start_seconds, duration_seconds, window_selection)

    resolved_start_seconds, resolved_window_selection = resolve_entry_window(path, window_selection, start_seconds, duration_seconds)
    try:
        audio = read_audio_slice(path, resolved_start_seconds, duration_seconds)
    except Exception as exc:
        return empty_row(entry, path, "decode_failed", str(exc), resolved_start_seconds, duration_seconds, resolved_window_selection)

    data = audio.data
    if data.size == 0:
        return empty_row(entry, path, "decode_failed", "decoded audio is empty", resolved_start_seconds, duration_seconds, resolved_window_selection)

    mono = np.mean(data, axis=1)
    peak = float(np.max(np.abs(data)))
    rms = float(np.sqrt(np.mean(np.square(mono)))) if mono.size else 0.0
    crest = dbfs(peak / max(rms, 1.0e-12))
    peak_density = float(np.mean(np.abs(data) >= db_to_linear(-1.0)) * 100.0)
    centroid, rolloff, spectral_source = spectral_centroid_rolloff(mono, audio.sample_rate)
    lufs_i: float | None = None
    notes = []
    try:
        import pyloudnorm as pyln

        meter = pyln.Meter(audio.sample_rate)
        lufs_i = float(meter.integrated_loudness(data))
    except Exception as exc:
        notes.append(f"pyloudnorm_unavailable_or_failed:{exc}")
    if spectral_source != "librosa":
        notes.append(spectral_source)

    correlation: float | None = None
    if audio.channels >= 2:
        left = data[:, 0]
        right = data[:, 1]
        if float(np.std(left)) > 1.0e-12 and float(np.std(right)) > 1.0e-12:
            correlation = float(np.corrcoef(left, right)[0, 1])

    row = {
        "id": entry.get("id", ""),
        "role": entry.get("role", ""),
        "path": str(path),
        "status": "measured",
        "reason": "; ".join(notes),
        "sample_rate": audio.sample_rate,
        "channels": audio.channels,
        "window_selection": resolved_window_selection,
        "analyzed_start_seconds": round(audio.start_seconds, 3),
        "analyzed_duration_seconds": round(audio.duration_seconds, 3),
        "lufs_i": round_or_blank(lufs_i, 3),
        "sample_peak_dbfs": round_or_blank(dbfs(peak), 3),
        "rms_dbfs": round_or_blank(dbfs(rms), 3),
        "crest_factor_db": round_or_blank(crest, 3),
        "peak_density_over_minus1db_pct": round_or_blank(peak_density, 6),
        "transient_density_per_second": round_or_blank(transient_density_per_second(mono, audio.sample_rate), 6),
        "spectral_centroid_hz": round_or_blank(centroid, 3),
        "spectral_rolloff_hz": round_or_blank(rolloff, 3),
        "low_energy_ratio_20_120": round_or_blank(band_energy_ratio(mono, audio.sample_rate, 20.0, 120.0), 6),
        "low_mid_energy_ratio_120_350": round_or_blank(band_energy_ratio(mono, audio.sample_rate, 120.0, 350.0), 6),
        "mid_energy_ratio_350_2500": round_or_blank(band_energy_ratio(mono, audio.sample_rate, 350.0, 2500.0), 6),
        "presence_energy_ratio_2500_6000": round_or_blank(band_energy_ratio(mono, audio.sample_rate, 2500.0, 6000.0), 6),
        "sibilance_energy_ratio_5000_10000": round_or_blank(band_energy_ratio(mono, audio.sample_rate, 5000.0, 10000.0), 6),
        "air_energy_ratio_10000_16000": round_or_blank(band_energy_ratio(mono, audio.sample_rate, 10000.0, 16000.0), 6),
        "high_energy_ratio_2500_16000": round_or_blank(band_energy_ratio(mono, audio.sample_rate, 2500.0, 16000.0), 6),
        "stereo_correlation": round_or_blank(correlation, 6),
    }
    return row


def audio_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"duration_seconds": None, "sample_rate": None, "channels": None, "reason": "missing"}
    if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        return {"duration_seconds": None, "sample_rate": None, "channels": None, "reason": "unsupported"}
    try:
        try:
            import soundfile as sf

            info = sf.info(str(path))
            return {
                "duration_seconds": float(info.duration),
                "sample_rate": int(info.samplerate),
                "channels": int(info.channels),
                "reason": "soundfile",
            }
        except Exception:
            pass
        if path.suffix.lower() == ".wav":
            from scipy.io import wavfile

            try:
                sample_rate, data = wavfile.read(str(path), mmap=True)
            except Exception:
                sample_rate, data = wavfile.read(str(path), mmap=False)
            channels = int(data.shape[1]) if getattr(data, "ndim", 1) == 2 else 1
            return {
                "duration_seconds": float(data.shape[0] / sample_rate) if sample_rate else None,
                "sample_rate": int(sample_rate),
                "channels": channels,
                "reason": "scipy",
            }
    except Exception as exc:
        return {"duration_seconds": None, "sample_rate": None, "channels": None, "reason": str(exc)}
    return {"duration_seconds": None, "sample_rate": None, "channels": None, "reason": "metadata_unavailable"}


def candidate_row(group: str, path: Path, reason: str) -> dict[str, Any]:
    meta = audio_metadata(path)
    return {
        "group": group,
        "path": str(path),
        "size_mb": round(path.stat().st_size / 1_000_000.0, 3) if path.exists() else "",
        "duration_seconds": round(meta["duration_seconds"], 3) if meta.get("duration_seconds") is not None else "",
        "sample_rate": meta.get("sample_rate") or "",
        "channels": meta.get("channels") or "",
        "reason": f"{reason}; metadata={meta.get('reason')}",
    }


def numeric_average(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [finite_number(row.get(field)) for row in rows if row.get("status") == "measured"]
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def build_reference_average(reference_rows: list[dict[str, Any]]) -> dict[str, float | None]:
    return {field: round(value, 6) if value is not None else None for field in COMPARISON_SCALES for value in [numeric_average(reference_rows, field)]}


def row_distance(target_row: dict[str, Any], reference_row: dict[str, Any]) -> float | None:
    distances = []
    for field, scale in COMPARISON_SCALES.items():
        target_value = finite_number(target_row.get(field))
        reference_value = finite_number(reference_row.get(field))
        if target_value is None or reference_value is None:
            continue
        distances.append(min(abs(target_value - reference_value) / scale, 2.0))
    if not distances:
        return None
    return sum(distances) / len(distances)


def build_differences(target_row: dict[str, Any], reference_average: dict[str, float | None]) -> dict[str, Any]:
    diffs = {}
    for field, average in reference_average.items():
        target_value = finite_number(target_row.get(field))
        if target_value is None or average is None:
            diffs[field] = None
            continue
        diffs[field] = {
            "target": round(target_value, 6),
            "reference_average": round(float(average), 6),
            "delta_target_minus_reference": round(target_value - float(average), 6),
            "normalized_abs_delta": round(min(abs(target_value - float(average)) / COMPARISON_SCALES[field], 2.0), 6),
        }
    return diffs


def recommendations_from_differences(diffs: dict[str, Any], target_row: dict[str, Any], measured_ref_count: int) -> list[str]:
    if target_row.get("status") != "measured" or measured_ref_count < REFERENCE_REQUIRED:
        return [
            "Blocked: provide one target chorus print and eight reference files before making reference-match claims.",
            "Keep the current REAPER template/profile-only plan active until metrics are measured.",
        ]

    recs: list[str] = []

    def delta(field: str) -> float | None:
        item = diffs.get(field)
        return item.get("delta_target_minus_reference") if isinstance(item, dict) else None

    sibilance_delta = delta("sibilance_energy_ratio_5000_10000")
    air_delta = delta("air_energy_ratio_10000_16000")
    high_delta = delta("high_energy_ratio_2500_16000")
    low_delta = delta("low_energy_ratio_20_120")
    low_mid_delta = delta("low_mid_energy_ratio_120_350")
    crest_delta = delta("crest_factor_db")
    peak_density_delta = delta("peak_density_over_minus1db_pct")
    corr_delta = delta("stereo_correlation")
    lufs_delta = delta("lufs_i")
    transient_delta = delta("transient_density_per_second")

    if (air_delta is not None and air_delta > 0.025) or (high_delta is not None and high_delta > 0.055):
        recs.append("High-end cleanup first: use Artifact Split Tamer or dynamic EQ around 6-12 kHz before adding Fresh Air/Ozone air.")
    if sibilance_delta is not None and sibilance_delta > 0.018:
        recs.append("Sibilance guard: tame 5-10 kHz on VOX BUS before master limiting; avoid broadband high-shelf compensation.")
    if corr_delta is not None and corr_delta < -0.12:
        recs.append("Stereo safety: check mono collapse and low-end side energy before using Wider/Ozone Imager on MIX BUS.")
    if low_mid_delta is not None and low_mid_delta > 0.040:
        recs.append("De-mud before loudness: reduce 120-350 Hz buildup on vocal/music buses rather than cutting the master broadly.")
    if low_delta is not None and low_delta < -0.035:
        recs.append("808 support: strengthen 808/BASS BUS with controlled saturation or dynamic space, not master low-shelf boost.")
    if transient_delta is not None and transient_delta < -3.0:
        recs.append("Drum/hat definition: inspect DRUM BUS transient density and smeared cymbal cleanup before mix-bus clipping.")
    if crest_delta is not None and crest_delta < -1.8:
        recs.append("Over-compression watch: target crest is lower than references; reduce bus compression before pushing PREMASTER.")
    if peak_density_delta is not None and peak_density_delta > 2.0:
        recs.append("Limiter/clip density watch: FreeClip/ReaLimit should not stay in sustained >2 dB reduction; return to bus balances.")
    if lufs_delta is not None and lufs_delta < -1.5:
        recs.append("Loudness gap: close with bus clarity and controlled clipping only after vocal, drums, and 808 are stable.")
    if not recs:
        recs.append("Metrics do not show a large reference delta; proceed with gain-matched A/B and conservative bus-level moves.")
    return recs


def discover_unconfirmed_candidates(root: Path) -> dict[str, list[str]]:
    def files_under(directory: Path, recursive: bool = False) -> list[Path]:
        if not directory.exists():
            return []
        iterator = directory.rglob("*") if recursive else directory.glob("*")
        paths = [path for path in iterator if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS]
        return sorted(paths)[:24]

    top_level = [path for path in root.glob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS]
    source_stem_zeroes = [
        path
        for path in (root / "audio_work").rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS
        and path.name.lower().startswith("0 ")
        and path.parent.name in {"source_stems", "raw_stems"}
    ][:32]
    tmp_masters = [
        path
        for path in (root / "tmp").rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS and any(token in path.name.lower() for token in ("final", "master", "plateau", "gain"))
    ][:32]
    return {
        "input_target": [str(path) for path in files_under(root / "input" / "target")],
        "input_reference": [str(path) for path in files_under(root / "input" / "reference")],
        "top_level_unconfirmed": [str(path) for path in sorted(top_level)[:12]],
        "audio_work_full_mix_candidates": [str(path) for path in sorted(source_stem_zeroes)],
        "tmp_master_candidates": [str(path) for path in sorted(tmp_masters)],
        "work_renders_unconfirmed": [str(path) for path in files_under(root / "work" / "renders", recursive=True)],
    }


def build_candidate_inventory(root: Path) -> list[dict[str, Any]]:
    discovered = discover_unconfirmed_candidates(root)
    rows: list[dict[str, Any]] = []
    reasons = {
        "input_target": "configured target folder audio",
        "input_reference": "configured reference folder audio",
        "top_level_unconfirmed": "top-level audio candidate, role unconfirmed",
        "audio_work_full_mix_candidates": "audio_work source_stems/raw_stems track 0 candidate, role unconfirmed",
        "tmp_master_candidates": "tmp rendered/master candidate, role unconfirmed",
        "work_renders_unconfirmed": "work render candidate, role unconfirmed",
    }
    for group, paths in discovered.items():
        for item in paths:
            rows.append(candidate_row(group, Path(item), reasons.get(group, "unconfirmed audio candidate")))
    return rows


def stem_role_from_name(path: Path) -> str:
    name = path.stem.lower()
    if "bass" in name or "808" in name:
        return "808_bass_stem"
    if "drum" in name or "perc" in name:
        return "drum_stem"
    if "vocal" in name or "main vocal" in name or "backing" in name:
        return "vocal_stem"
    if "synth" in name or "keyboard" in name or "guitar" in name or "string" in name or "brass" in name or "woodwind" in name:
        return "music_stem"
    if name.startswith("0 "):
        return "full_mix_stem_reference"
    return "other_stem"


def analyze_target_stems(
    manifest: dict[str, Any],
    root: Path,
    target_start_seconds: float,
    duration_seconds: float | None,
) -> list[dict[str, Any]]:
    stem_config = manifest.get("target_stems") or {}
    stem_dir = resolve_path(root, stem_config.get("path"))
    if stem_dir is None or not stem_dir.exists() or not stem_dir.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    audio_files = [path for path in sorted(stem_dir.iterdir()) if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS]
    for index, path in enumerate(audio_files, start=1):
        entry = {
            "id": f"stem_{index:02d}",
            "role": stem_role_from_name(path),
            "path": str(path),
        }
        rows.append(analyze_entry(entry, root, target_start_seconds, duration_seconds, "target_chorus_aligned_20s"))
    return rows


def build_markdown_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    target = result["target"]
    refs = result["references"]
    lines = [
        "# GOAL 02 Chorus 20s 8-Reference Match Report",
        "",
        f"- Generated UTC: `{result['created_at']}`",
        f"- Status: `{summary['status']}`",
        f"- Target profile: `{result['manifest'].get('target_profile')}`",
        f"- Analysis window: `{summary['analysis_window_label']}` start `{summary['start_seconds']}`s, duration `{summary['duration_seconds']}`s",
        f"- Target measured: `{target.get('status') == 'measured'}`",
        f"- References measured: `{summary['references_measured']}/{summary['references_required']}`",
        f"- Claim policy: `metrics only; no listening claims`",
        "",
        "## Blocking State",
        "",
    ]
    if summary["status"].startswith("blocked"):
        lines.extend(
            [
                "- Reference matching is blocked until the target and eight references are present and decoded.",
                "- No release-quality, reference-matched, or finished-master claim is allowed from this report.",
            ]
        )
    else:
        lines.append("- Required target and eight references were measured. REAPER changes still need render/QC/user A/B evidence.")

    lines.extend(
        [
            "",
            "## Target",
            "",
            f"- id: `{target.get('id')}`",
            f"- path: `{target.get('path')}`",
            f"- status: `{target.get('status')}`",
            f"- LUFS-I: `{target.get('lufs_i')}`",
            f"- peak dBFS: `{target.get('sample_peak_dbfs')}`",
            f"- stereo correlation: `{target.get('stereo_correlation')}`",
            "",
            "## References",
            "",
            "| id | role | status | LUFS-I | peak dBFS | centroid Hz | corr |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in refs:
        lines.append(
            f"| `{row.get('id')}` | `{row.get('role')}` | `{row.get('status')}` | `{row.get('lufs_i')}` | `{row.get('sample_peak_dbfs')}` | `{row.get('spectral_centroid_hz')}` | `{row.get('stereo_correlation')}` |"
        )

    stems = result.get("target_stems", [])
    if stems:
        lines.extend(
            [
                "",
                "## Target Stem Window",
                "",
                "| id | role | peak dBFS | rms dBFS | low 20-120 | low-mid 120-350 | mid 350-2500 | high 2.5-16k | corr |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in stems:
            lines.append(
                f"| `{row.get('id')}` | `{row.get('role')}` | `{row.get('sample_peak_dbfs')}` | `{row.get('rms_dbfs')}` | `{row.get('low_energy_ratio_20_120')}` | `{row.get('low_mid_energy_ratio_120_350')}` | `{row.get('mid_energy_ratio_350_2500')}` | `{row.get('high_energy_ratio_2500_16000')}` | `{row.get('stereo_correlation')}` |"
            )

    lines.extend(["", "## Target Minus Reference Average", ""])
    diffs = result.get("target_minus_reference_average", {})
    for field in COMPARISON_SCALES:
        item = diffs.get(field)
        if isinstance(item, dict):
            lines.append(f"- `{field}`: delta `{item['delta_target_minus_reference']}` (normalized `{item['normalized_abs_delta']}`)")
        else:
            lines.append(f"- `{field}`: `unavailable`")

    lines.extend(["", "## Closest References", ""])
    closest = result.get("closest_references", [])
    if closest:
        for item in closest:
            lines.append(f"- `{item['id']}` similarity `{item['similarity_score']}` distance `{item['distance']}`")
    else:
        lines.append("- unavailable")

    lines.extend(["", "## Recommendations", ""])
    lines.extend([f"- {item}" for item in result.get("recommendations", [])])

    lines.extend(["", "## Unconfirmed Local Audio Candidates", ""])
    candidates = result.get("unconfirmed_audio_candidates", {})
    for group, paths in candidates.items():
        lines.append(f"- `{group}`: `{len(paths)}` candidate(s)")
        for path in paths[:8]:
            lines.append(f"  - `{path}`")
    inventory = result.get("candidate_inventory", [])
    if inventory:
        lines.extend(
            [
                "",
                "## Candidate Inventory Preview",
                "",
                "| group | duration | sr | ch | size MB | path |",
                "| --- | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for row in inventory[:24]:
            lines.append(
                f"| `{row['group']}` | `{row['duration_seconds']}` | `{row['sample_rate']}` | `{row['channels']}` | `{row['size_mb']}` | `{row['path']}` |"
            )

    lines.extend(
        [
            "",
            "## REAPER Application Order",
            "",
            "1. Route references only to muted `REF BUS` with master send disabled.",
            "2. Route target/stems to `VOX BUS`, `DRUM BUS`, `808/BASS BUS`, and `MUSIC BUS`.",
            "3. Fix vocal, 808, and drum deltas before PREMASTER.",
            "4. Use PREMASTER only for glue, clipping, limiting, and metering after bus fixes.",
            "5. Stop and return to the mix if master processing needs sustained reduction above 2 dB.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_outputs(result: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "goal02_reference_features.csv"
    inventory_csv_path = output_dir / "goal02_audio_candidate_inventory.csv"
    stem_csv_path = output_dir / "goal02_target_stem_features.csv"
    json_path = output_dir / "goal02_reference_match.json"
    report_path = output_dir / "GOAL02_CHORUS_REFERENCE_MATCH_REPORT.md"

    rows = [result["target"], *result["references"]]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FEATURE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    with inventory_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANDIDATE_FIELDS)
        writer.writeheader()
        writer.writerows(result.get("candidate_inventory", []))

    with stem_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FEATURE_FIELDS)
        writer.writeheader()
        writer.writerows(result.get("target_stems", []))

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")

    report_path.write_text(build_markdown_report(result), encoding="utf-8")
    return {
        "csv": str(csv_path),
        "candidate_inventory_csv": str(inventory_csv_path),
        "target_stem_csv": str(stem_csv_path),
        "json": str(json_path),
        "markdown": str(report_path),
    }


def analyze_goal02(root: Path, manifest_path: Path | None = None, output_dir: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    manifest, manifest_warnings = load_manifest(root, manifest_path)
    window = manifest.get("analysis_window", {})
    window_selection = str(window.get("selection") or "fixed_start")
    start_seconds = parse_float_or_default(window.get("start_seconds", 0.0), 0.0)
    duration_value = window.get("duration_seconds", 20.0)
    duration_seconds = None if duration_value in ("", None) else float(duration_value)
    target_row = analyze_entry(manifest.get("target", {}), root, start_seconds, duration_seconds, window_selection)
    reference_rows = [analyze_entry(item, root, start_seconds, duration_seconds, window_selection) for item in manifest.get("references", [])]
    target_window_start = parse_float_or_default(target_row.get("analyzed_start_seconds"), start_seconds)
    target_stems = analyze_target_stems(manifest, root, target_window_start, duration_seconds)
    measured_refs = [row for row in reference_rows if row.get("status") == "measured"]
    references_required = int(manifest.get("references_required", REFERENCE_REQUIRED) or REFERENCE_REQUIRED)
    reference_average = build_reference_average(reference_rows)
    diffs = build_differences(target_row, reference_average)
    closest = []
    if target_row.get("status") == "measured":
        for row in measured_refs:
            distance = row_distance(target_row, row)
            if distance is not None:
                closest.append(
                    {
                        "id": row.get("id"),
                        "role": row.get("role"),
                        "path": row.get("path"),
                        "distance": round(distance, 6),
                        "similarity_score": round(1.0 / (1.0 + distance), 6),
                    }
                )
    closest = sorted(closest, key=lambda item: item["distance"])[:5]
    primary_references = closest[:3]
    blocked_reasons = []
    if target_row.get("status") != "measured":
        blocked_reasons.append("target_chorus_missing_or_unmeasured")
    if len(measured_refs) < references_required:
        blocked_reasons.append("fewer_than_8_references_measured")
    status = "blocked_missing_inputs" if blocked_reasons else "measured_8_reference_profile_ready_for_reaper_plan"
    result = {
        "schema": "automix-goal02-8-reference-match-result-v1",
        "created_at": now_utc(),
        "root": str(root),
        "manifest": manifest,
        "manifest_warnings": manifest_warnings,
        "summary": {
            "status": status,
            "blocked_reasons": blocked_reasons,
            "analysis_window_label": window.get("label", "chorus_20s"),
            "analysis_window_selection": window_selection,
            "start_seconds": start_seconds,
            "duration_seconds": duration_seconds,
            "references_required": references_required,
            "references_configured": len(reference_rows),
            "references_measured": len(measured_refs),
            "references_missing_or_blocked": len(reference_rows) - len(measured_refs),
            "target_measured": target_row.get("status") == "measured",
            "no_listening_claims": True,
            "render_qc_required_before_delivery": True,
        },
        "target": target_row,
        "references": reference_rows,
        "target_stems": target_stems,
        "reference_average": reference_average,
        "target_minus_reference_average": diffs,
        "closest_references": closest,
        "primary_references": primary_references,
        "recommendations": recommendations_from_differences(diffs, target_row, len(measured_refs)),
        "unconfirmed_audio_candidates": discover_unconfirmed_candidates(root),
        "candidate_inventory": build_candidate_inventory(root),
    }
    if output_dir is not None:
        result["outputs"] = write_outputs(result, output_dir if output_dir.is_absolute() else root / output_dir)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze one target chorus against eight reference files for GOAL 02.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--root", type=Path, default=ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = analyze_goal02(root=args.root, manifest_path=args.manifest, output_dir=args.output_dir)
    print(json.dumps({"status": result["summary"]["status"], "outputs": result.get("outputs", {})}, indent=2, ensure_ascii=False))
    return 0 if not result["summary"]["blocked_reasons"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
