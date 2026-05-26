#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

try:
    import numpy as np
    from scipy import signal
    from scipy.io import wavfile
except ImportError as error:  # pragma: no cover - local render helper.
    raise SystemExit(
        "This one-off render script needs the local NumPy/SciPy runtime that is already "
        f"available in this workspace. Missing import: {error}"
    ) from error


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from final_verify import verify_final_wav  # noqa: E402
from loudness_estimation import linear_to_db  # noqa: E402
from paths import ensure_folder_structure  # noqa: E402
from audio_metrics import (  # noqa: E402
    BAND_RANGES as METRIC_BAND_RANGES,
    clipping_count as metric_clipping_count,
    mono_compatibility as metric_mono_compatibility,
    normalize_peak as metric_normalize_peak,
    normalize_rms as metric_normalize_rms,
    one_second_rms_percentiles as metric_one_second_rms_percentiles,
    peak_db as metric_peak_db,
    rms_db as metric_rms_db,
    side_mid_db as metric_side_mid_db,
    spectral_band_profile as metric_spectral_band_profile,
)
from deesser import deess as module_deess  # noqa: E402
from delay_fx import DelaySettings, delay_send  # noqa: E402
from dynamic_eq import DynamicEQBand, apply_vocal_triggered_beat_ducking, dynamic_band_process as module_dynamic_band_process  # noqa: E402
from masking_analysis import masking_score as module_masking_score  # noqa: E402
from master_bus import master_bus_process  # noqa: E402
from mix_balance import add_to_mix as module_add_to_mix  # noqa: E402
from ms_eq import mono_compatibility_metrics as ms_mono_compatibility_metrics  # noqa: E402
from ms_eq import safe_mid_side_process  # noqa: E402
from multiband_dynamics import CompressorBand, multiband_compress as module_multiband_compress  # noqa: E402
from reference_matcher import apply_tone_aware_reference_correction, compare_to_reference, load_reference_average  # noqa: E402
from reverb_fx import SchroederReverbSettings, schroeder_reverb  # noqa: E402
from sample_arranger import arrange_samples_musically  # noqa: E402
from saturation import soft_saturate  # noqa: E402
from vocal_tone_designer import design_vocal_tone  # noqa: E402


SAMPLE_RATE = 48_000
BPM = 136.0

PLUGG_DIR = Path("/Users/hantaeheuk/Desktop/plugg")
SAMPLE_DIR = Path("/Users/hantaeheuk/Desktop/음악샘플")

BEAT_PATH = PLUGG_DIR / "SahBabii-Type-Beat---BLUE-SQUID_1.wav"
SAMPLE_PATH = SAMPLE_DIR / "15_U.N.Owen_source.mp3"
DECODED_SAMPLE_PATH = PROJECT_ROOT / "04_PROCESSED_AUDIO" / "plugg_un_owen_sample_source_48k.wav"

PRE_MASTER_PATH = PROJECT_ROOT / "09_MIX_MASTER" / "plugg_reference_matched_v4_pre_master.wav"
FINAL_MASTER_PATH = PROJECT_ROOT / "05_FINAL_WAV" / "plugg_reference_matched_v4_24bit_48k.wav"
PREVIEW_PATH = PROJECT_ROOT / "05_FINAL_WAV" / "plugg_reference_matched_v4_preview.m4a"
QC_JSON_PATH = PROJECT_ROOT / "06_QC_REPORT" / "plugg_reference_matched_v4_qc.json"
QC_METRICS_PATH = PROJECT_ROOT / "06_QC_REPORT" / "plugg_reference_matched_v4_metrics.json"
QC_MD_PATH = PROJECT_ROOT / "06_QC_REPORT" / "plugg_reference_matched_v4_qc.md"

REFERENCE_ANALYSIS_PATH = PROJECT_ROOT / "08_REFERENCE_MATCH" / "reference_texture_analysis.json"
REFERENCE_MATCH_REPORT_PATH = PROJECT_ROOT / "08_REFERENCE_MATCH" / "reference_match_report.json"
SAMPLE_ARRANGEMENT_REPORT_PATH = PROJECT_ROOT / "08_REFERENCE_MATCH" / "sample_arrangement_report.json"
SELECTED_SAMPLES_PATH = PROJECT_ROOT / "08_REFERENCE_MATCH" / "selected_samples.json"
SECTION_SAMPLE_PLAN_PATH = PROJECT_ROOT / "08_REFERENCE_MATCH" / "section_sample_plan.json"
BAND_RANGES = {
    "sub_20_60": (20.0, 60.0),
    "bass_60_150": (60.0, 150.0),
    "low_mid_150_400": (150.0, 400.0),
    "mid_400_1500": (400.0, 1_500.0),
    "presence_1500_4500": (1_500.0, 4_500.0),
    "bite_4500_8000": (4_500.0, 8_000.0),
    "air_8000_16000": (8_000.0, 16_000.0),
}
assert BAND_RANGES == METRIC_BAND_RANGES


VOCAL_TRACKS: list[dict[str, Any]] = [
    {
        "name": "lead_main2",
        "path": PLUGG_DIR / "main2_1.wav",
        "gain_db": 2.5,
        "pan": 0.0,
        "highpass_hz": 105.0,
        "lowpass_hz": 14_500.0,
        "compress_threshold_db": -25.0,
        "compress_ratio": 3.8,
        "makeup_db": 5.5,
        "target_peak_db": -3.2,
        "delay_send_db": -18.5,
        "room_send_db": -27.0,
        "hard_tune_blend": 0.16,
        "role": "lead",
    },
    {
        "name": "lead_main1_support",
        "path": PLUGG_DIR / "main 1_1.wav",
        "gain_db": -1.8,
        "pan": 0.04,
        "highpass_hz": 110.0,
        "lowpass_hz": 13_500.0,
        "compress_threshold_db": -24.0,
        "compress_ratio": 3.3,
        "makeup_db": 4.5,
        "target_peak_db": -4.8,
        "delay_send_db": -20.5,
        "room_send_db": -28.0,
        "hard_tune_blend": 0.10,
        "role": "lead",
    },
    {
        "name": "male_double",
        "path": PLUGG_DIR / "doub_1.wav",
        "gain_db": -6.4,
        "pan": -0.28,
        "highpass_hz": 125.0,
        "lowpass_hz": 9_500.0,
        "compress_threshold_db": -24.0,
        "compress_ratio": 3.5,
        "makeup_db": 3.8,
        "target_peak_db": -6.2,
        "delay_send_db": -22.0,
        "room_send_db": -28.0,
        "role": "double",
    },
    {
        "name": "girl_double_1",
        "path": PLUGG_DIR / "doub1 girl_1.wav",
        "gain_db": -8.8,
        "pan": 0.52,
        "highpass_hz": 155.0,
        "lowpass_hz": 10_500.0,
        "compress_threshold_db": -24.0,
        "compress_ratio": 3.0,
        "makeup_db": 2.5,
        "target_peak_db": -6.8,
        "delay_send_db": -22.5,
        "room_send_db": -28.0,
        "role": "adlib",
    },
    {
        "name": "girl_double_2",
        "path": PLUGG_DIR / "doub2 girl_1.wav",
        "gain_db": -9.0,
        "pan": -0.50,
        "highpass_hz": 155.0,
        "lowpass_hz": 10_500.0,
        "compress_threshold_db": -24.0,
        "compress_ratio": 3.0,
        "makeup_db": 2.5,
        "target_peak_db": -6.8,
        "delay_send_db": -23.0,
        "room_send_db": -28.5,
        "role": "adlib",
    },
]


def db_to_linear(value: float) -> float:
    return 10.0 ** (value / 20.0)


def rms_db(samples: np.ndarray) -> float:
    if samples.size == 0:
        return float("-inf")
    return linear_to_db(float(np.sqrt(np.mean(np.square(samples, dtype=np.float64)))))


def wav_metadata(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as wav_file:
        return {
            "sample_rate": wav_file.getframerate(),
            "channels": wav_file.getnchannels(),
            "sample_width": wav_file.getsampwidth(),
            "frames": wav_file.getnframes(),
            "duration_seconds": wav_file.getnframes() / wav_file.getframerate(),
        }


def read_audio(path: Path, start_frame: int = 0, frame_count: int | None = None) -> tuple[int, np.ndarray]:
    sample_rate, data = wavfile.read(path)
    if sample_rate != SAMPLE_RATE:
        raise ValueError(f"{path} sample rate is {sample_rate}, expected {SAMPLE_RATE}")
    if data.ndim == 1:
        data = data[:, None]
    if frame_count is not None or start_frame:
        start = max(0, min(start_frame, data.shape[0]))
        end = data.shape[0] if frame_count is None else min(data.shape[0], start + max(0, frame_count))
        data = data[start:end]
    if np.issubdtype(data.dtype, np.floating):
        audio = data.astype(np.float32, copy=False)
    elif data.dtype == np.int16:
        audio = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        audio = data.astype(np.float32) / 2147483648.0
    elif data.dtype == np.uint8:
        audio = (data.astype(np.float32) - 128.0) / 128.0
    else:
        raise ValueError(f"Unsupported audio dtype for {path}: {data.dtype}")
    return sample_rate, np.clip(audio, -1.0, 1.0)


def write_wav24(path: Path, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if audio.ndim == 1:
        audio = audio[:, None]
    clipped = np.clip(audio, -1.0, 1.0)
    scaled = np.where(clipped >= 0.0, clipped * 8_388_607.0, clipped * 8_388_608.0)
    ints = np.rint(scaled).astype("<i4", copy=False)
    pcm24 = ints.reshape(-1).view(np.uint8).reshape(-1, 4)[:, :3].reshape(-1).tobytes()
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(audio.shape[1])
        wav_file.setsampwidth(3)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm24)


def normalize_peak(audio: np.ndarray, target_db: float, max_gain_db: float = 12.0) -> tuple[np.ndarray, float]:
    current_peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if current_peak <= 0.0:
        return audio, 1.0
    gain = db_to_linear(target_db) / current_peak
    gain = min(gain, db_to_linear(max_gain_db))
    return audio * gain, gain


def normalize_rms(audio: np.ndarray, target_db: float, max_gain_db: float = 8.0) -> tuple[np.ndarray, float]:
    current = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64)))) if audio.size else 0.0
    if current <= 0.0:
        return audio, 1.0
    gain = db_to_linear(target_db) / current
    gain = min(gain, db_to_linear(max_gain_db))
    return (audio * gain).astype(np.float32), gain


def filter_audio(audio: np.ndarray, highpass_hz: float, lowpass_hz: float) -> np.ndarray:
    output = audio.astype(np.float32, copy=False)
    if highpass_hz > 0.0:
        sos = signal.butter(2, highpass_hz / (SAMPLE_RATE / 2), btype="highpass", output="sos")
        output = signal.sosfilt(sos, output, axis=0).astype(np.float32)
    if 0.0 < lowpass_hz < SAMPLE_RATE / 2:
        sos = signal.butter(2, lowpass_hz / (SAMPLE_RATE / 2), btype="lowpass", output="sos")
        output = signal.sosfilt(sos, output, axis=0).astype(np.float32)
    return output


def band_eq(audio: np.ndarray, low_hz: float, high_hz: float, gain_db: float) -> np.ndarray:
    if gain_db == 0.0 or low_hz <= 0.0 or high_hz >= SAMPLE_RATE / 2 or low_hz >= high_hz:
        return audio.astype(np.float32, copy=False)
    sos = signal.butter(2, [low_hz / (SAMPLE_RATE / 2), high_hz / (SAMPLE_RATE / 2)], btype="bandpass", output="sos")
    band = signal.sosfilt(sos, audio, axis=0).astype(np.float32)
    return (audio + band * (db_to_linear(gain_db) - 1.0)).astype(np.float32)


def bandpass(audio: np.ndarray, low_hz: float, high_hz: float, order: int = 2) -> np.ndarray:
    if low_hz <= 0.0 or high_hz >= SAMPLE_RATE / 2 or low_hz >= high_hz:
        return audio.astype(np.float32, copy=False)
    sos = signal.butter(order, [low_hz / (SAMPLE_RATE / 2), high_hz / (SAMPLE_RATE / 2)], btype="bandpass", output="sos")
    return signal.sosfilt(sos, audio, axis=0).astype(np.float32)


def envelope_follower(
    detector: np.ndarray,
    attack_ms: float = 8.0,
    release_ms: float = 85.0,
    lookahead_ms: float = 0.0,
) -> np.ndarray:
    mono_detector = np.abs(mono(detector)).astype(np.float32)
    if lookahead_ms > 0.0 and mono_detector.size:
        shift = int((lookahead_ms / 1000.0) * SAMPLE_RATE)
        if 0 < shift < mono_detector.shape[0]:
            mono_detector = np.concatenate((mono_detector[shift:], np.zeros(shift, dtype=np.float32)))
    attack = math.exp(-1.0 / max(1.0, (attack_ms / 1000.0) * SAMPLE_RATE))
    release = math.exp(-1.0 / max(1.0, (release_ms / 1000.0) * SAMPLE_RATE))
    output = np.zeros_like(mono_detector, dtype=np.float32)
    state = 0.0
    for index, value in enumerate(mono_detector):
        coefficient = attack if value > state else release
        state = coefficient * state + (1.0 - coefficient) * float(value)
        output[index] = state
    return output


def dynamic_band_process(
    audio: np.ndarray,
    detector: np.ndarray,
    low_hz: float,
    high_hz: float,
    threshold_db: float,
    range_db: float,
    attack_ms: float,
    release_ms: float,
    q: float = 1.0,
    lookahead_ms: float = 0.0,
) -> tuple[np.ndarray, dict[str, float]]:
    if audio.size == 0:
        return audio.astype(np.float32, copy=False), {"max_gain_reduction_db": 0.0, "mean_gain_reduction_db": 0.0, "q": q}
    band = bandpass(audio, low_hz, high_hz, order=2)
    detect_band = bandpass(to_stereo(detector), low_hz, high_hz, order=2)
    env = envelope_follower(detect_band, attack_ms=attack_ms, release_ms=release_ms, lookahead_ms=lookahead_ms)
    env_db = np.array([linear_to_db(float(value) + 1e-9) for value in env], dtype=np.float32)
    over = np.clip((env_db - threshold_db) / 18.0, 0.0, 1.0)
    gain_reduction_db = -abs(range_db) * over
    gain = np.power(10.0, gain_reduction_db / 20.0).astype(np.float32)
    if gain.shape[0] < audio.shape[0]:
        gain = np.pad(gain, (0, audio.shape[0] - gain.shape[0]), constant_values=1.0)
    gain = gain[: audio.shape[0]]
    processed = audio + band * (gain[:, None] - 1.0)
    active = gain_reduction_db[gain_reduction_db < -0.05]
    return processed.astype(np.float32), {
        "low_hz": low_hz,
        "high_hz": high_hz,
        "threshold_db": threshold_db,
        "range_db": range_db,
        "attack_ms": attack_ms,
        "release_ms": release_ms,
        "q": q,
        "max_gain_reduction_db": round(float(np.min(gain_reduction_db)) if gain_reduction_db.size else 0.0, 2),
        "mean_active_gain_reduction_db": round(float(np.mean(active)) if active.size else 0.0, 2),
    }


def envelope_compress(
    audio: np.ndarray,
    threshold_db: float,
    ratio: float,
    attack_ms: float,
    release_ms: float,
    makeup_db: float = 0.0,
) -> tuple[np.ndarray, dict[str, float]]:
    env = envelope_follower(audio, attack_ms=attack_ms, release_ms=release_ms)
    env_db = np.array([linear_to_db(float(value) + 1e-9) for value in env], dtype=np.float32)
    over_db = np.maximum(env_db - threshold_db, 0.0)
    reduction_db = -(over_db - over_db / max(ratio, 1.0))
    gain = np.power(10.0, (reduction_db + makeup_db) / 20.0).astype(np.float32)
    if gain.shape[0] < audio.shape[0]:
        gain = np.pad(gain, (0, audio.shape[0] - gain.shape[0]), constant_values=db_to_linear(makeup_db))
    output = audio * gain[: audio.shape[0], None]
    active = reduction_db[reduction_db < -0.05]
    return output.astype(np.float32), {
        "threshold_db": threshold_db,
        "ratio": ratio,
        "attack_ms": attack_ms,
        "release_ms": release_ms,
        "makeup_db": makeup_db,
        "max_gain_reduction_db": round(float(np.min(reduction_db)) if reduction_db.size else 0.0, 2),
        "mean_active_gain_reduction_db": round(float(np.mean(active)) if active.size else 0.0, 2),
    }


def multiband_compress(audio: np.ndarray, bands: list[dict[str, float]]) -> tuple[np.ndarray, list[dict[str, float]]]:
    output = np.zeros_like(audio, dtype=np.float32)
    reports: list[dict[str, float]] = []
    for band_config in bands:
        band = bandpass(audio, band_config["low_hz"], band_config["high_hz"], order=2)
        processed, report = envelope_compress(
            band,
            threshold_db=band_config["threshold_db"],
            ratio=band_config["ratio"],
            attack_ms=band_config["attack_ms"],
            release_ms=band_config["release_ms"],
            makeup_db=band_config.get("makeup_db", 0.0),
        )
        output += processed
        reports.append({**band_config, **report})
    residual = audio - sum((bandpass(audio, config["low_hz"], config["high_hz"], order=2) for config in bands), np.zeros_like(audio))
    output += residual * 0.72
    return output.astype(np.float32), reports


def mid_side_eq(audio: np.ndarray, mid_moves: list[tuple[float, float, float]], side_moves: list[tuple[float, float, float]]) -> np.ndarray:
    stereo = to_stereo(audio)
    mid = ((stereo[:, 0] + stereo[:, 1]) * 0.5)[:, None]
    side = ((stereo[:, 0] - stereo[:, 1]) * 0.5)[:, None]
    for low_hz, high_hz, gain_db in mid_moves:
        mid = band_eq(mid, low_hz, high_hz, gain_db)
    for low_hz, high_hz, gain_db in side_moves:
        side = band_eq(side, low_hz, high_hz, gain_db)
    return np.column_stack((mid[:, 0] + side[:, 0], mid[:, 0] - side[:, 0])).astype(np.float32)


def apply_stutter_gate(audio: np.ndarray, step_beats: float = 0.5, duty: float = 0.84, depth: float = 0.62) -> np.ndarray:
    step_frames = max(1, int((60.0 / BPM) * step_beats * SAMPLE_RATE))
    active_frames = max(1, int(step_frames * duty))
    frame_positions = np.arange(audio.shape[0]) % step_frames
    envelope_values = np.where(frame_positions < active_frames, 1.0, depth).astype(np.float32)
    return (audio * envelope_values[:, None]).astype(np.float32)


def frame_for_bar(bar: float) -> int:
    return int(bar * 4.0 * (60.0 / BPM) * SAMPLE_RATE)


def arrange_beat(beat: np.ndarray) -> tuple[np.ndarray, list[str]]:
    arranged = np.zeros_like(beat)
    notes: list[str] = []
    sections = [
        (0.0, 4.0, -13.0, 24.0, 4_800.0, False, "intro filtered low, sample leads"),
        (4.0, 12.0, -7.8, 24.0, 17_500.0, True, "hook with light gated beat under sample melody"),
        (12.0, 20.0, -8.9, 28.0, 15_000.0, False, "verse pocket, vocal center stays clear"),
        (20.0, 24.0, -12.0, 36.0, 6_200.0, True, "pre-bridge filtered break"),
        (24.0, 28.0, -18.0, 45.0, 2_200.0, False, "sample bridge, original beat heavily reduced"),
        (28.0, 36.0, -7.9, 24.0, 18_000.0, True, "second hook with wider top"),
        (36.0, 44.0, -8.2, 24.0, 17_000.0, True, "sample-forward final hook"),
        (44.0, 999.0, -11.0, 32.0, 10_500.0, False, "outro tail"),
    ]
    for start_bar, end_bar, gain_db, highpass_hz, lowpass_hz, gate, note in sections:
        start = min(beat.shape[0], frame_for_bar(start_bar))
        end = min(beat.shape[0], frame_for_bar(end_bar))
        if end <= start:
            continue
        segment = filter_audio(beat[start:end], highpass_hz, lowpass_hz)
        segment = band_eq(segment, 180.0, 360.0, -0.8)
        segment = band_eq(segment, 1_450.0, 4_400.0, -1.55)
        segment = band_eq(segment, 6_500.0, 11_500.0, 1.4)
        if gate:
            segment = apply_stutter_gate(segment)
        arranged[start:end] += segment * db_to_linear(gain_db)
        notes.append(f"{start_bar:g}-{end_bar:g} bars: {note}, beat gain {gain_db:g} dB")
    return arranged.astype(np.float32), notes


def compress(audio: np.ndarray, threshold_db: float, ratio: float, makeup_db: float) -> np.ndarray:
    threshold = db_to_linear(threshold_db)
    value = np.abs(audio)
    compressed = np.where(value > threshold, threshold + (value - threshold) / ratio, value)
    return (np.sign(audio) * compressed * db_to_linear(makeup_db)).astype(np.float32)


def saturate(audio: np.ndarray, drive: float, output_gain: float = 0.98) -> np.ndarray:
    if drive <= 1.0:
        return audio
    return (np.tanh(audio * drive) / math.tanh(drive) * output_gain).astype(np.float32)


def tune_gloss(audio: np.ndarray, blend: float) -> np.ndarray:
    if blend <= 0.0:
        return audio
    mono_vocal = mono(audio)
    centered = mono_vocal - signal.medfilt(mono_vocal, kernel_size=401)
    gloss = centered[:, None]
    gloss, _report = envelope_compress(gloss, -31.0, 2.4, attack_ms=5.0, release_ms=70.0, makeup_db=3.6)
    gloss = band_eq(gloss, 700.0, 1_500.0, -0.8)
    gloss = band_eq(gloss, 1_800.0, 3_700.0, 1.35)
    gloss = band_eq(gloss, 5_200.0, 8_400.0, -0.75)
    gloss = band_eq(gloss, 8_800.0, 13_600.0, 1.7)
    gloss = saturate(gloss, 1.055, 0.94)
    gloss = filter_audio(gloss, 150.0, 14_000.0)
    return (audio * (1.0 - blend) + gloss * blend).astype(np.float32)


def soften_comb_tone(audio: np.ndarray) -> np.ndarray:
    softened = band_eq(audio, 520.0, 900.0, -0.8)
    softened = band_eq(softened, 2_600.0, 4_200.0, -0.55)
    softened, _report = dynamic_band_process(
        softened,
        softened,
        5_300.0,
        8_400.0,
        threshold_db=-31.5,
        range_db=2.4,
        attack_ms=2.5,
        release_ms=62.0,
        ratio_slope=0.35,
    )
    return softened.astype(np.float32)


def apply_fades(audio: np.ndarray, fade_in_seconds: float, fade_out_seconds: float) -> np.ndarray:
    output = audio.copy()
    frames = output.shape[0]
    fade_in_frames = min(frames, int(fade_in_seconds * SAMPLE_RATE))
    fade_out_frames = min(frames, int(fade_out_seconds * SAMPLE_RATE))
    if fade_in_frames:
        output[:fade_in_frames] *= np.linspace(0.0, 1.0, fade_in_frames, endpoint=False, dtype=np.float32)[:, None]
    if fade_out_frames:
        output[-fade_out_frames:] *= np.linspace(1.0, 0.0, fade_out_frames, endpoint=False, dtype=np.float32)[:, None]
    return output


def limit(audio: np.ndarray, ceiling_db: float) -> np.ndarray:
    ceiling = db_to_linear(ceiling_db)
    return np.clip(audio, -ceiling, ceiling).astype(np.float32)


def soft_limiter(audio: np.ndarray, ceiling_db: float = -0.78, drive: float = 1.0) -> tuple[np.ndarray, dict[str, float]]:
    ceiling = db_to_linear(ceiling_db)
    driven = audio * drive
    overs = np.maximum(np.abs(driven) - ceiling * 0.72, 0.0)
    reduction = 1.0 / (1.0 + overs * 4.6)
    limited = driven * reduction
    limited = np.tanh(limited / ceiling * 0.92) * ceiling
    limited = np.clip(limited, -ceiling, ceiling).astype(np.float32)
    peak_before = linear_to_db(float(np.max(np.abs(audio))) + 1e-12)
    peak_after = linear_to_db(float(np.max(np.abs(limited))) + 1e-12)
    return limited, {"ceiling_db": ceiling_db, "drive": drive, "peak_before_dbfs": round(peak_before, 2), "peak_after_dbfs": round(peak_after, 2)}


def widen_above(audio: np.ndarray, cutoff_hz: float = 145.0, side_gain: float = 2.35) -> np.ndarray:
    stereo = to_stereo(audio)
    low_mono = mono(filter_audio(stereo, 0.0, cutoff_hz))[:, None]
    low = np.repeat(low_mono, 2, axis=1)
    high = stereo - low
    mid = (high[:, 0] + high[:, 1]) * 0.5
    side_part = (high[:, 0] - high[:, 1]) * 0.5 * side_gain
    high_wide = np.column_stack((mid + side_part, mid - side_part)).astype(np.float32)
    return (low + high_wide).astype(np.float32)


def mono(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        return audio.astype(np.float32)
    return np.mean(audio, axis=1, dtype=np.float32)


def pan_mono(samples: np.ndarray, pan: float) -> np.ndarray:
    clamped = max(-1.0, min(1.0, pan))
    angle = (clamped + 1.0) * math.pi / 4.0
    left_gain = math.cos(angle)
    right_gain = math.sin(angle)
    return np.column_stack((samples * left_gain, samples * right_gain)).astype(np.float32)


def to_stereo(audio: np.ndarray, pan: float | None = None) -> np.ndarray:
    if pan is not None:
        return pan_mono(mono(audio), pan)
    if audio.ndim == 1:
        return np.column_stack((audio, audio)).astype(np.float32)
    if audio.shape[1] == 1:
        return np.repeat(audio, 2, axis=1).astype(np.float32)
    return audio[:, :2].astype(np.float32)


def add_to_mix(mix: np.ndarray, source: np.ndarray, gain: float, start_frame: int = 0, pan: float | None = None) -> None:
    stereo = to_stereo(source, pan)
    dst_start = start_frame
    src_start = 0
    if dst_start < 0:
        src_start = -dst_start
        dst_start = 0
    if src_start >= stereo.shape[0] or dst_start >= mix.shape[0]:
        return
    count = min(mix.shape[0] - dst_start, stereo.shape[0] - src_start)
    mix[dst_start : dst_start + count] += stereo[src_start : src_start + count] * gain


def envelope(samples: np.ndarray, block_size: int) -> np.ndarray:
    usable = (samples.shape[0] // block_size) * block_size
    if usable <= 0:
        return np.array([], dtype=np.float32)
    blocks = np.abs(samples[:usable]).reshape(-1, block_size).mean(axis=1)
    std = float(np.std(blocks)) or 1.0
    return ((blocks - float(np.mean(blocks))) / std).astype(np.float32)


def best_alignment_shift(reference: np.ndarray, target: np.ndarray, max_shift_ms: float = 120.0) -> tuple[int, float]:
    block_size = 480
    ref_env = envelope(reference, block_size)
    target_env = envelope(target, block_size)
    if ref_env.size == 0 or target_env.size == 0:
        return 0, 0.0
    max_blocks = max(1, int((max_shift_ms / 1000.0) * SAMPLE_RATE / block_size))
    best_shift = 0
    best_score = -1.0
    for shift in range(-max_blocks, max_blocks + 1):
        if shift >= 0:
            ref_slice = ref_env[shift:]
            target_slice = target_env[: ref_slice.shape[0]]
        else:
            target_slice = target_env[-shift:]
            ref_slice = ref_env[: target_slice.shape[0]]
        count = min(ref_slice.shape[0], target_slice.shape[0])
        if count < 25:
            continue
        ref_slice = ref_slice[:count]
        target_slice = target_slice[:count]
        denominator = float(np.linalg.norm(ref_slice) * np.linalg.norm(target_slice)) or 1.0
        score = float(np.dot(ref_slice, target_slice) / denominator)
        if score > best_score:
            best_score = score
            best_shift = shift
    if best_score < 0.05:
        return 0, best_score
    return best_shift * block_size, best_score


def process_vocal_track(track: dict[str, Any], beat_bus: np.ndarray | None = None) -> tuple[np.ndarray, dict[str, Any]]:
    _sample_rate, audio = read_audio(track["path"])
    vocal = mono(audio)[:, None]
    vocal, normalize_gain = normalize_peak(vocal, -12.0)
    vocal, tone_report = design_vocal_tone(vocal, SAMPLE_RATE, tune_blend=float(track.get("hard_tune_blend", 0.0)), beat_bus=beat_bus, role=str(track.get("role", "lead")))
    vocal, safety_gain = normalize_peak(vocal, track["target_peak_db"], max_gain_db=6.0)
    return vocal.astype(np.float32), {
        "input": str(track["path"]),
        "duration_seconds": vocal.shape[0] / SAMPLE_RATE,
        "normalize_gain": normalize_gain,
        "safety_gain": safety_gain,
        "target_peak_db": track["target_peak_db"],
        "pan": track["pan"],
        "hard_tune_blend": track.get("hard_tune_blend", 0.0),
        "role": track.get("role", "lead"),
        "vocal_leveler": tone_report["vocal_rider"],
        "harshness_dynamic_eq": tone_report["harshness_dynamic_eq"],
        "deesser": tone_report["deesser"],
        "second_deesser": tone_report.get("second_deesser"),
        "pitch": tone_report["pitch"],
        "tone": tone_report,
    }


def add_delay_sends(delay_return: np.ndarray, vocal_fx_return: np.ndarray, source: np.ndarray, track: dict[str, Any], start_shift: int) -> list[dict[str, Any]]:
    role = str(track.get("role", "lead"))
    fx_length = max(0, delay_return.shape[0] - start_shift)
    if role == "lead":
        delay_settings = DelaySettings(mode="tempo", beat_fraction=0.5, feedback=0.16, wet=0.075, ping_pong=False, duck_range_db=-4.0)
        reverb_settings = SchroederReverbSettings(pre_delay_ms=38.0, decay_seconds=1.05, wet=0.08, return_highpass_hz=240.0, return_lowpass_hz=8_000.0, duck_range_db=-4.5)
    elif role == "double":
        delay_settings = DelaySettings(mode="slap", slap_ms=95.0, feedback=0.12, wet=0.11, ping_pong=False, duck_range_db=-3.0)
        reverb_settings = SchroederReverbSettings(pre_delay_ms=30.0, decay_seconds=1.2, wet=0.12, return_highpass_hz=260.0, return_lowpass_hz=7_500.0, duck_range_db=-3.0, stereo_spread_ms=15.0)
    else:
        delay_settings = DelaySettings(mode="tempo", beat_fraction=0.25, feedback=0.22, wet=0.14, ping_pong=True, duck_range_db=-2.5)
        reverb_settings = SchroederReverbSettings(pre_delay_ms=28.0, decay_seconds=1.35, wet=0.15, return_highpass_hz=280.0, return_lowpass_hz=7_000.0, duck_range_db=-2.5, stereo_spread_ms=18.0)
    delay_bus, delay_report = delay_send(source, SAMPLE_RATE, BPM, delay_settings, duck_source=source, length=fx_length)
    module_add_to_mix(delay_return, delay_bus, 1.0, start_shift)
    room_bus, reverb_report = schroeder_reverb(source, SAMPLE_RATE, reverb_settings, duck_source=source, length=fx_length)
    module_add_to_mix(vocal_fx_return, room_bus, 1.0, start_shift)
    return [{"role": role, "delay": delay_report, "reverb": reverb_report}]


def ensure_decoded_sample() -> dict[str, Any]:
    afconvert = shutil.which("afconvert")
    if not afconvert:
        return {"decoded": False, "reason": "afconvert unavailable", "path": str(DECODED_SAMPLE_PATH)}
    if DECODED_SAMPLE_PATH.exists() and DECODED_SAMPLE_PATH.stat().st_mtime >= SAMPLE_PATH.stat().st_mtime:
        return {"decoded": True, "reused": True, "path": str(DECODED_SAMPLE_PATH)}
    DECODED_SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [afconvert, "-f", "WAVE", "-d", f"LEI24@{SAMPLE_RATE}", str(SAMPLE_PATH), str(DECODED_SAMPLE_PATH)],
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "decoded": result.returncode == 0,
        "reused": False,
        "path": str(DECODED_SAMPLE_PATH),
        "stderr": result.stderr.strip(),
    }


def prepare_sample_chops() -> tuple[list[np.ndarray], dict[str, Any]]:
    decode_status = ensure_decoded_sample()
    if not decode_status.get("decoded"):
        return [], {"decode_status": decode_status, "chops": []}
    _sample_rate, sample_audio = read_audio(DECODED_SAMPLE_PATH)
    beat_seconds = 60.0 / BPM
    chop_seconds = beat_seconds * 0.94
    segment_offsets = [42.0, 42.5, 43.0, 43.75, 44.25, 45.0]
    chops: list[np.ndarray] = []
    chop_notes: list[dict[str, Any]] = []
    for index, seconds in enumerate(segment_offsets):
        start = int(seconds * SAMPLE_RATE)
        end = min(sample_audio.shape[0], start + int(chop_seconds * SAMPLE_RATE))
        chop = mono(sample_audio[start:end])[:, None]
        chop = filter_audio(chop, 180.0, 12_500.0)
        chop = band_eq(chop, 2_000.0, 5_500.0, 1.6)
        chop = band_eq(chop, 7_500.0, 13_500.0, 3.2)
        chop = compress(chop, -18.5, 1.7, 2.0)
        chop = saturate(chop, 1.08, 0.96)
        chop = apply_fades(chop, 0.006, 0.028)
        chop, _gain = normalize_peak(chop, -8.8, max_gain_db=10.0)
        chops.append(chop.astype(np.float32))
        chop_notes.append({"index": index, "source_start_seconds": seconds, "duration_seconds": round(chop_seconds, 3)})
    return chops, {"decode_status": decode_status, "source": str(SAMPLE_PATH), "chops": chop_notes}


def pitch_variant(chop: np.ndarray, semitones: float) -> np.ndarray:
    if semitones == 0.0 or chop.shape[0] < 8:
        return chop
    factor = 2.0 ** (semitones / 12.0)
    target_frames = max(8, int(chop.shape[0] / factor))
    shifted = signal.resample(chop[:, 0], target_frames).astype(np.float32)
    if target_frames < chop.shape[0]:
        shifted = np.pad(shifted, (0, chop.shape[0] - target_frames))
    else:
        shifted = shifted[: chop.shape[0]]
    shifted = apply_fades(shifted[:, None], 0.004, 0.025)
    shifted, _gain = normalize_peak(shifted, -9.2, max_gain_db=6.0)
    return shifted.astype(np.float32)


def add_sample_motif(mix: np.ndarray, chops: list[np.ndarray], beat_context: np.ndarray | None = None, vocal_context: np.ndarray | None = None) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    return arrange_samples_musically(
        mix,
        chops,
        SAMPLE_RATE,
        BPM,
        beat_context=beat_context,
        vocal_context=vocal_context,
        ownership_status="unknown",
        policy_blocks_unknown=False,
        key_confidence=0.0,
    )


def build_preview() -> dict[str, Any]:
    afconvert = shutil.which("afconvert")
    if not afconvert:
        return {"created": False, "reason": "afconvert unavailable", "path": str(PREVIEW_PATH)}
    result = subprocess.run(
        [afconvert, "-f", "m4af", "-d", "aac", "-b", "256000", str(FINAL_MASTER_PATH), str(PREVIEW_PATH)],
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "created": result.returncode == 0 and PREVIEW_PATH.exists(),
        "path": str(PREVIEW_PATH),
        "stderr": result.stderr.strip(),
    }


def side_mid_db(audio: np.ndarray) -> float:
    stereo = to_stereo(audio)
    mid = (stereo[:, 0] + stereo[:, 1]) * 0.5
    side = (stereo[:, 0] - stereo[:, 1]) * 0.5
    mid_rms = float(np.sqrt(np.mean(np.square(mid, dtype=np.float64)))) + 1e-12
    side_rms = float(np.sqrt(np.mean(np.square(side, dtype=np.float64)))) + 1e-12
    return round(linear_to_db(side_rms / mid_rms), 2)


def spectral_band_profile(audio: np.ndarray) -> dict[str, float]:
    return metric_spectral_band_profile(audio, SAMPLE_RATE)


def one_second_rms_percentiles(audio: np.ndarray) -> list[float]:
    return metric_one_second_rms_percentiles(audio, SAMPLE_RATE)


def mono_compatibility(audio: np.ndarray) -> dict[str, float]:
    return metric_mono_compatibility(audio)


def masking_score(vocal_bus: np.ndarray, instrumental_bus: np.ndarray) -> dict[str, float]:
    return module_masking_score(vocal_bus, instrumental_bus, SAMPLE_RATE)


def reference_average_profile() -> dict[str, Any]:
    return load_reference_average(REFERENCE_ANALYSIS_PATH)


def render_audio_metrics(master: np.ndarray, vocal_bus: np.ndarray, instrumental_bus: np.ndarray) -> dict[str, Any]:
    reference = reference_average_profile()
    metrics = {
        **compare_to_reference(master, SAMPLE_RATE, reference),
        "one_sec_rms_p10_p50_p90": one_second_rms_percentiles(master),
        "mono_compatibility": mono_compatibility(master),
        "mono_compatibility_ms": ms_mono_compatibility_metrics(master, SAMPLE_RATE),
        "vocal_beat_masking_score": masking_score(vocal_bus, instrumental_bus),
        "clipping_count": metric_clipping_count(master),
        "reference_average": reference,
    }
    return metrics


def render_report(qc: dict[str, Any]) -> str:
    verification = qc["verification"]
    sample_report = qc["sample_report"]
    extended = qc.get("extended_metrics", {})
    mono_report = extended.get("mono_compatibility", {})
    ms_mono_report = extended.get("mono_compatibility_ms", {})
    masking = extended.get("vocal_beat_masking_score", {})
    band_delta = extended.get("band_delta_vs_reference_average_db", {})
    processing = qc.get("processing", {})
    dynamic_eq = processing.get("dynamic_eq", {})
    deess_stats = [track.get("deesser", {}) for track in qc.get("track_reports", [])]
    pitch_stats = [track.get("pitch", {}) for track in qc.get("track_reports", [])]
    reference_match = processing.get("reference_match_report", {})
    track_lines = [
        "- {name}: gain {gain} dB, pan {pan}, shift {shift_ms} ms, align score {score}, tune-gloss blend {tune}".format(
            name=Path(track["input"]).name,
            gain=track["mix_gain_db"],
            pan=track["pan"],
            shift_ms=track["alignment_shift_ms"],
            score=track["alignment_score"],
            tune=track.get("hard_tune_blend", 0.0),
        )
        for track in qc["track_reports"]
    ]
    return "\n".join(
        [
            "# Plugg Digicore Mix QC",
            "",
            "## Status",
            f"- final master verification ok: {str(bool(verification.get('ok'))).lower()}",
            f"- final master: {qc['outputs']['final_master']}",
            f"- pre-master: {qc['outputs']['pre_master']}",
            f"- AAC preview: {qc['outputs']['preview'] or 'not created'}",
            f"- metrics JSON: {qc['outputs'].get('metrics_json')}",
            f"- duration: {qc['duration_seconds']:.2f}s",
            f"- sample rate: {verification.get('sample_rate')}",
            f"- bit depth: {verification.get('bit_depth')}",
            f"- peak: {verification.get('peak_dbfs'):.2f} dBFS",
            f"- rms: {verification.get('rms_dbfs'):.2f} dBFS",
            f"- clipping count: {verification.get('clipping_count')}",
            "",
            "## Extended Metrics",
            f"- crest: {extended.get('crest_db')} dB",
            f"- side/mid: {extended.get('side_mid_db')} dB",
            f"- one-second RMS p10/p50/p90: {extended.get('one_sec_rms_p10_p50_p90')}",
            f"- mono level delta: {mono_report.get('mono_level_delta_db')} dB",
            f"- L/R correlation: {mono_report.get('left_right_correlation')}",
            f"- M/S low side-mid below 150 Hz: {ms_mono_report.get('low_side_mid_ratio_below_150hz_db')} dB",
            f"- mono fold peak/RMS change: {ms_mono_report.get('mono_fold_peak_change_db')} / {ms_mono_report.get('mono_fold_rms_change_db')} dB",
            f"- masking score low-mid/mid/presence: {masking.get('low_mid_150_400')}, {masking.get('mid_400_1500')}, {masking.get('presence_1500_4500')} dB",
            "",
            "## Spectral Delta vs Reference Average",
            *[f"- {name}: {value:+.2f} dB" for name, value in band_delta.items()],
            "",
            "## Mix Moves",
            *[f"- {note}" for note in qc["processing"]["notes"]],
            f"- reference analysis: {qc['processing'].get('reference_analysis_path')}",
            "",
            "## Bus Architecture",
            f"- buses: {', '.join(processing.get('bus_architecture', []))}",
            f"- order: {' -> '.join(processing.get('processing_order', []))}",
            "",
            "## Actually Applied",
            *[f"- {item}" for item in processing.get("applied", [])],
            "",
            "## Approximated / Not Applied",
            *[f"- approximated: {item}" for item in processing.get("approximated", [])],
            f"- Antares applied: {str(bool(processing.get('antares_applied'))).lower()}",
            "",
            "## Dynamic EQ / De-Ess / Pitch Stats",
            f"- beat ducking bands: {len(dynamic_eq.get('vocal_triggered_beat_ducking', {}).get('bands_applied', []))}",
            f"- beat ducking gain reductions: {[(band.get('low_hz'), band.get('high_hz'), band.get('average_gain_reduction_db'), band.get('max_gain_reduction_db')) for band in dynamic_eq.get('vocal_triggered_beat_ducking', {}).get('bands_applied', [])]}",
            f"- sample pocket max gain reduction: {dynamic_eq.get('sample_vocal_pocket', {}).get('max_gain_reduction_db')} dB",
            f"- vocal bus de-ess sibilance delta: {processing.get('vocal_bus_deess', {}).get('sibilance_delta_db')} dB",
            f"- track de-ess reports: {len(deess_stats)}",
            f"- pitch approximation reports: {len(pitch_stats)}",
            "",
            "## Reference Matching",
            f"- correction amounts: {reference_match.get('correction_amounts', [])}",
            f"- warnings: {reference_match.get('warnings', [])}",
            "",
            "## Arrangement",
            *[f"- {note}" for note in qc["processing"].get("arrangement_notes", [])],
            "",
            "## Vocal Stem Balancing",
            *track_lines,
            "",
            "## Sample Motif",
            f"- source: {sample_report.get('source')}",
            f"- decoded: {str(bool(sample_report.get('decode_status', {}).get('decoded'))).lower()}",
            f"- chops used: {len(sample_report.get('chops', []))}",
            f"- motif placements: {len(sample_report.get('motif_placements', []))}",
            "",
            "## Limits / Honesty Notes",
            f"- true pitch correction applied: {str(bool(qc['processing']['true_pitch_correction_applied'])).lower()}",
            f"- hard-tune style layer applied: {str(bool(qc['processing'].get('hard_tune_style_layer_applied'))).lower()}",
            f"- tune gloss layer applied: {str(bool(qc['processing'].get('tune_gloss_layer_applied'))).lower()}",
            f"- pitch note: {qc['processing']['pitch_note']}",
            f"- rights note: {qc['processing']['rights_note']}",
            *[f"- limitation: {item}" for item in processing.get("remaining_limitations", [])],
            "- exact System Seoul/Nate Sib/artist clone claimed: false",
            "",
            "## Verification Errors",
            *(f"- {error}" for error in verification.get("errors", [])),
            "" if verification.get("errors") else "- none",
            "",
        ]
    )


def render() -> dict[str, Any]:
    ensure_folder_structure(PROJECT_ROOT)
    (PROJECT_ROOT / "09_MIX_MASTER").mkdir(parents=True, exist_ok=True)

    missing = [str(path) for path in [BEAT_PATH, SAMPLE_PATH, *(track["path"] for track in VOCAL_TRACKS)] if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing input files: {missing}")

    beat_meta = wav_metadata(BEAT_PATH)
    if beat_meta["sample_rate"] != SAMPLE_RATE:
        raise ValueError(f"Beat sample rate is {beat_meta['sample_rate']}, expected {SAMPLE_RATE}")
    max_vocal_frames = max(wav_metadata(track["path"])["frames"] for track in VOCAL_TRACKS)
    tail_frames = int((60.0 / BPM) * 4.0 * 6.0 * SAMPLE_RATE)
    output_frames = min(int(beat_meta["frames"]), int(max_vocal_frames + tail_frames))

    # Bus architecture:
    # ingest -> beat/sample/lead/double/adlib buses -> music/vocal buses -> premaster -> master.
    _sample_rate, beat = read_audio(BEAT_PATH, frame_count=output_frames)
    beat_ingest = filter_audio(to_stereo(beat), 24.0, 19_000.0)
    beat_ingest = saturate(beat_ingest, 1.025, 0.985)
    beat_bus, arrangement_notes = arrange_beat(beat_ingest)
    sample_bus = np.zeros_like(beat_bus)
    lead_vocal_bus = np.zeros_like(beat_bus)
    double_vocal_bus = np.zeros_like(beat_bus)
    adlib_or_girl_double_bus = np.zeros_like(beat_bus)
    vocal_fx_return = np.zeros_like(beat_bus)
    delay_return = np.zeros_like(beat_bus)

    lead_reference: np.ndarray | None = None
    track_reports: list[dict[str, Any]] = []
    for track in VOCAL_TRACKS:
        processed, report = process_vocal_track(track, beat_bus=beat_bus)
        processed_mono = mono(processed)
        shift_frames = 0
        shift_score = 0.0
        if track["name"] == "lead_main2":
            lead_reference = processed_mono
        elif lead_reference is not None:
            shift_frames, shift_score = best_alignment_shift(lead_reference, processed_mono)
        role = str(track.get("role", "lead"))
        target_vocal_bus = lead_vocal_bus if role == "lead" else double_vocal_bus if role == "double" else adlib_or_girl_double_bus
        add_to_mix(target_vocal_bus, processed, db_to_linear(track["gain_db"]), shift_frames, track["pan"])
        delay_notes = add_delay_sends(delay_return, vocal_fx_return, processed, track, shift_frames)
        report.update(
            {
                "mix_gain_db": track["gain_db"],
                "alignment_shift_frames": shift_frames,
                "alignment_shift_ms": round(shift_frames / SAMPLE_RATE * 1000.0, 2),
                "alignment_score": round(shift_score, 4),
                "delay_and_room_taps": delay_notes,
            }
        )
        track_reports.append(report)

    raw_vocal_bus = lead_vocal_bus + double_vocal_bus + adlib_or_girl_double_bus
    chops, sample_report = prepare_sample_chops()
    motif_placements, sample_arrangement_report, selected_samples, section_sample_plan = add_sample_motif(sample_bus, chops, beat_bus, raw_vocal_bus)
    sample_report["motif_placements"] = motif_placements
    sample_report["candidate_analysis"] = sample_arrangement_report.get("candidate_analysis", [])
    sample_report["selected_samples"] = selected_samples
    sample_report["section_sample_plan"] = section_sample_plan

    dynamic_reports: dict[str, Any] = {}
    beat_bus, dynamic_reports["vocal_triggered_beat_ducking"] = apply_vocal_triggered_beat_ducking(beat_bus, raw_vocal_bus, SAMPLE_RATE)
    sample_bus, dynamic_reports["sample_vocal_pocket"] = module_dynamic_band_process(
        sample_bus,
        raw_vocal_bus,
        DynamicEQBand(1_600.0, 5_200.0, threshold_db=-35.0, range_db=-2.4, ratio_slope=0.32, attack_ms=4.0, release_ms=135.0, mode="cut", detector="rms"),
        SAMPLE_RATE,
    )

    sample_bus = widen_above(sample_bus, cutoff_hz=900.0, side_gain=1.08)
    music_bus = beat_bus + sample_bus
    music_bus = soft_saturate(music_bus, 1.012, 0.992)
    music_bus, dynamic_reports["music_bus_glue"] = module_multiband_compress(
        music_bus,
        SAMPLE_RATE,
        [
            CompressorBand(40.0, 160.0, -21.0, 1.35, 28.0, 150.0, 0.15),
            CompressorBand(160.0, 1_200.0, -24.0, 1.32, 14.0, 120.0, 0.1),
            CompressorBand(1_200.0, 7_500.0, -27.5, 1.25, 6.0, 90.0, 0.05),
        ],
    )

    vocal_bus = lead_vocal_bus + double_vocal_bus + adlib_or_girl_double_bus
    vocal_bus, vocal_bus_deess_report = module_deess(vocal_bus, SAMPLE_RATE, range_db=-2.0)
    vocal_bus, vocal_bus_comp_report = module_multiband_compress(
        vocal_bus,
        SAMPLE_RATE,
        [
            CompressorBand(120.0, 650.0, -26.0, 1.35, 12.0, 100.0, 0.1),
            CompressorBand(650.0, 4_800.0, -28.5, 1.28, 5.0, 85.0, 0.1),
            CompressorBand(4_800.0, 12_000.0, -31.0, 1.2, 2.0, 70.0, 0.0),
        ],
    )
    vocal_returns_bus = vocal_fx_return + delay_return

    premaster_bus = music_bus + vocal_bus + vocal_returns_bus
    premaster_bus = band_eq(premaster_bus, 20.0, 55.0, -2.2)
    premaster_bus = band_eq(premaster_bus, 62.0, 155.0, 2.3)
    premaster_bus = band_eq(premaster_bus, 170.0, 420.0, 0.9)
    premaster_bus = band_eq(premaster_bus, 4_600.0, 8_200.0, 2.6)
    premaster_bus = band_eq(premaster_bus, 8_500.0, 15_500.0, 3.8)
    premaster_bus, ms_report = safe_mid_side_process(
        premaster_bus,
        SAMPLE_RATE,
        side_low_cut_hz=140.0,
        side_upper_width_db=1.35,
        side_air_lift_db=0.85,
        mid_moves=[(140.0, 380.0, 0.75), (1_700.0, 3_800.0, 0.55), (6_500.0, 10_500.0, -0.35)],
    )
    premaster_bus, dynamic_reports["premaster_multiband"] = module_multiband_compress(
        premaster_bus,
        SAMPLE_RATE,
        [
            CompressorBand(20.0, 120.0, -19.5, 1.65, 26.0, 160.0, 0.35),
            CompressorBand(120.0, 850.0, -23.0, 1.55, 13.0, 120.0, 0.25),
            CompressorBand(850.0, 5_800.0, -25.0, 1.42, 7.0, 90.0, 0.2),
            CompressorBand(5_800.0, 16_000.0, -28.0, 1.35, 3.5, 70.0, 0.15),
        ],
    )
    reference_profile = reference_average_profile()
    premaster_bus, reference_match_report = apply_tone_aware_reference_correction(premaster_bus, SAMPLE_RATE, reference_profile)
    premaster_bus = widen_above(premaster_bus, cutoff_hz=145.0, side_gain=1.52)
    premaster_bus = apply_fades(premaster_bus, 0.025, 3.5)
    premaster_bus, pre_master_gain = normalize_peak(premaster_bus, -6.0, max_gain_db=6.0)
    write_wav24(PRE_MASTER_PATH, premaster_bus, SAMPLE_RATE)

    master_processing = [
        "original beat was section-arranged with intro filtering, hooks, bridge drop, and outro tail",
        "v4 keeps the broad reference texture target but avoids exact artist or song cloning",
        "vocal-triggered dynamic EQ ducks beat presence and low-mid bands only when the vocal needs space",
        "harshness-triggered dynamic EQ catches vocal bite spikes before air is restored",
        "mid/side EQ keeps low-end center stable while widening upper texture",
        "multiband compression and density bus replace the flatter static EQ/clip-only master feel",
        "lead and doubles were made vocal-forward with smoother tune gloss and less comb-like hard-tune color",
        "doubles aligned against the lead using envelope cross-correlation when confidence was usable",
        "sample chops were reworked into call-response motifs so the hook has its own identity",
        "master tonal match controls sub-only weight while preserving bass, bite, and air bands",
        "tone-aware reference matcher applies capped broad-band correction and rejects harshness/clipping regressions",
        "master bus now uses low cleanup, seven-band glue/density, subtle native saturation, M/S safety, and an oversampled lookahead limiter",
    ]
    master_bus = widen_above(premaster_bus, cutoff_hz=160.0, side_gain=1.02)
    master_bus, master_report = master_bus_process(master_bus, SAMPLE_RATE, target_rms_db=-9.25, ceiling_db=-1.0)
    density_report = master_report["density_bus_multiband"]
    bus_comp_report = master_report["master_bus_compressor"]
    limiter_report = master_report["soft_limiter"]
    rms_gain = master_report["rms_match_gain"]
    master_gain = 1.0
    post_limiter_gain = master_report["post_limiter_gain"]
    write_wav24(FINAL_MASTER_PATH, master_bus, SAMPLE_RATE)

    verification = verify_final_wav(FINAL_MASTER_PATH, "wav24_48k")
    preview = build_preview()
    qc = {
        "style_target": "digicore_hyperpop_system_seoul_nate_sib_adjacent_broad_target_no_clone",
        "exact_artist_clone_claimed": False,
        "tempo_bpm": BPM,
        "duration_seconds": master_bus.shape[0] / SAMPLE_RATE,
        "input_files": {
            "beat": str(BEAT_PATH),
            "sample": str(SAMPLE_PATH),
            "vocals": [str(track["path"]) for track in VOCAL_TRACKS],
        },
        "outputs": {
            "pre_master": str(PRE_MASTER_PATH),
            "final_master": str(FINAL_MASTER_PATH),
            "preview": str(PREVIEW_PATH) if preview.get("created") else None,
            "qc_json": str(QC_JSON_PATH),
            "metrics_json": str(QC_METRICS_PATH),
            "qc_markdown": str(QC_MD_PATH),
        },
        "processing": {
            "bus_architecture": [
                "beat_bus",
                "sample_bus",
                "lead_vocal_bus",
                "double_vocal_bus",
                "adlib_or_girl_double_bus",
                "vocal_fx_return",
                "delay_return",
                "music_bus",
                "vocal_bus",
                "premaster_bus",
                "master_bus",
            ],
            "processing_order": [
                "ingest/convert/resample",
                "align vocals and beat",
                "gain staging",
                "sample arrangement",
                "lead vocal rider",
                "native pitch-correction approximation / tuned support layer",
                "vocal tone chain",
                "doubles/adlibs tone + width",
                "reverb/delay sends",
                "beat dynamic EQ ducked by vocal",
                "sample/synth width",
                "music bus saturation/glue",
                "vocal bus compression/de-ess",
                "premaster balance",
                "reference tone matching, gentle",
                "master bus",
                "final 24-bit 48k WAV export",
                "verification",
                "QC report",
            ],
            "applied": [
                "native Python/NumPy/SciPy vocal tone chain",
                "vocal-triggered beat dynamic EQ",
                "sample arrangement section plan",
                "bus-level vocal de-ess/compression",
                "music bus saturation/glue",
                "tone-aware reference correction",
                "oversampled limiter and final WAV verification",
            ],
            "approximated": [
                "native pitch-correction approximation / tuned support layer",
                "LUFS-like loudness proxy",
                "true-peak proxy via oversampling",
            ],
            "pre_master_gain": pre_master_gain,
            "rms_match_gain": rms_gain,
            "master_gain": master_gain,
            "dynamic_eq": dynamic_reports,
            "mid_side_eq": ms_report,
            "vocal_bus_deess": vocal_bus_deess_report,
            "vocal_bus_compression": vocal_bus_comp_report,
            "density_bus_multiband": density_report,
            "master_bus_compressor": bus_comp_report,
            "master_saturation": master_report.get("master_saturation", {}),
            "master_bus_quality_metrics": master_report.get("quality_metrics", {}),
            "soft_limiter": limiter_report,
            "post_limiter_gain": post_limiter_gain,
            "notes": master_processing,
            "arrangement_notes": arrangement_notes,
            "reference_analysis_path": str(REFERENCE_ANALYSIS_PATH),
            "reference_match_report_path": str(REFERENCE_MATCH_REPORT_PATH),
            "reference_match_report": reference_match_report,
            "sample_arrangement_report_path": str(SAMPLE_ARRANGEMENT_REPORT_PATH),
            "selected_samples_path": str(SELECTED_SAMPLES_PATH),
            "section_sample_plan_path": str(SECTION_SAMPLE_PLAN_PATH),
            "reference_match_targets": {
                "rms_dbfs_range": [-9.7, -8.4],
                "side_mid_db_range": [-13.6, -7.95],
                "restore_bite_air": True,
                "avoid_exact_copy": True,
            },
            "true_pitch_correction_applied": False,
            "hard_tune_style_layer_applied": False,
            "tune_gloss_layer_applied": True,
            "antares_applied": False,
            "pitch_note": "No verified Auto-Tune plugin or note-by-note pitch editor is available here; this render uses a native pitch-correction approximation as a low-blend tuned support layer, level-aware tune gloss, harshness control, formant-ish low-mid protection, doubled width, and timing alignment without claiming true pitch correction.",
            "rights_note": "Local sample file was used for a demo render; release use still needs sample/license clearance.",
            "remaining_limitations": [
                "Antares/Auto-Tune was not applied because no verified command-line plugin processing is available",
                "source beat is a stereo mix, so beat processing is bus-level rather than stem-level",
                "local sample source still requires rights clearance for release use",
                "native pitch correction is an approximation, not professional note-by-note tuning",
            ],
        },
        "track_reports": track_reports,
        "sample_report": sample_report,
        "preview": preview,
        "master_metrics": {
            "peak_dbfs": linear_to_db(float(np.max(np.abs(master_bus)))),
            "rms_dbfs": rms_db(master_bus.reshape(-1)),
            "clipping_count": int(np.sum(np.abs(master_bus) >= 0.999969)),
        },
        "bus_metrics": {
            "beat_bus": {"peak_dbfs": metric_peak_db(beat_bus), "rms_dbfs": metric_rms_db(beat_bus)},
            "sample_bus": {"peak_dbfs": metric_peak_db(sample_bus), "rms_dbfs": metric_rms_db(sample_bus)},
            "lead_vocal_bus": {"peak_dbfs": metric_peak_db(lead_vocal_bus), "rms_dbfs": metric_rms_db(lead_vocal_bus)},
            "double_vocal_bus": {"peak_dbfs": metric_peak_db(double_vocal_bus), "rms_dbfs": metric_rms_db(double_vocal_bus)},
            "adlib_or_girl_double_bus": {"peak_dbfs": metric_peak_db(adlib_or_girl_double_bus), "rms_dbfs": metric_rms_db(adlib_or_girl_double_bus)},
            "vocal_fx_return": {"peak_dbfs": metric_peak_db(vocal_fx_return), "rms_dbfs": metric_rms_db(vocal_fx_return)},
            "delay_return": {"peak_dbfs": metric_peak_db(delay_return), "rms_dbfs": metric_rms_db(delay_return)},
            "music_bus": {"peak_dbfs": metric_peak_db(music_bus), "rms_dbfs": metric_rms_db(music_bus)},
            "vocal_bus": {"peak_dbfs": metric_peak_db(vocal_bus), "rms_dbfs": metric_rms_db(vocal_bus)},
            "premaster_bus": {"peak_dbfs": metric_peak_db(premaster_bus), "rms_dbfs": metric_rms_db(premaster_bus)},
            "master_bus": {"peak_dbfs": metric_peak_db(master_bus), "rms_dbfs": metric_rms_db(master_bus)},
        },
        "extended_metrics": render_audio_metrics(master_bus, vocal_bus, music_bus),
        "verification": verification,
    }
    SAMPLE_ARRANGEMENT_REPORT_PATH.write_text(json.dumps(sample_arrangement_report, indent=2) + "\n", encoding="utf-8")
    SELECTED_SAMPLES_PATH.write_text(json.dumps(selected_samples, indent=2) + "\n", encoding="utf-8")
    SECTION_SAMPLE_PLAN_PATH.write_text(json.dumps(section_sample_plan, indent=2) + "\n", encoding="utf-8")
    REFERENCE_MATCH_REPORT_PATH.write_text(json.dumps(reference_match_report, indent=2) + "\n", encoding="utf-8")
    QC_JSON_PATH.write_text(json.dumps(qc, indent=2) + "\n", encoding="utf-8")
    QC_METRICS_PATH.write_text(json.dumps(qc, indent=2) + "\n", encoding="utf-8")
    QC_MD_PATH.write_text(render_report(qc), encoding="utf-8")
    return qc


def main() -> int:
    qc = render()
    print(f"Wrote final master: {qc['outputs']['final_master']}")
    print(f"Verification ok: {qc['verification'].get('ok')}")
    print(f"Wrote QC report: {qc['outputs']['qc_markdown']}")
    return 0 if qc["verification"].get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
