from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy import signal

from audio_analysis import read_wav_float
from audio_metrics import bandpass, clipping_count, db_to_linear, filter_audio, normalize_peak, peak_db, rms_db, side_mid_db, to_stereo
from dynamic_eq import DynamicEQBand, dynamic_band_process
from export_audio import verify_wav, write_float_wav
from simple_synth_renderer import render_motifs_to_audio


TARGET_SAMPLE_RATE = 48_000


def channels_to_audio(channels: list[list[float]]) -> np.ndarray:
    if not channels:
        return np.zeros((0, 2), dtype=np.float32)
    frame_count = min((len(channel) for channel in channels), default=0)
    if frame_count <= 0:
        return np.zeros((0, 2), dtype=np.float32)
    return to_stereo(np.column_stack([np.asarray(channel[:frame_count], dtype=np.float32) for channel in channels]))


def read_audio_file(path: str | Path) -> tuple[dict[str, Any], np.ndarray]:
    metadata, channels = read_wav_float(Path(path).expanduser())
    audio = channels_to_audio(channels)
    return metadata, audio


def resample_audio(audio: np.ndarray, source_rate: int, target_rate: int = TARGET_SAMPLE_RATE) -> np.ndarray:
    samples = to_stereo(audio)
    if source_rate == target_rate or samples.size == 0:
        return samples.astype(np.float32)
    gcd = math.gcd(int(source_rate), int(target_rate))
    up = int(target_rate // gcd)
    down = int(source_rate // gcd)
    return signal.resample_poly(samples, up, down, axis=0).astype(np.float32)


def write_wav24(path: str | Path, audio: np.ndarray, sample_rate: int = TARGET_SAMPLE_RATE) -> dict[str, Any]:
    stereo = to_stereo(audio)
    output, safety_gain = normalize_peak(stereo, -1.2, max_gain_db=0.0)
    write_float_wav(Path(path), [output[:, 0].astype(float).tolist(), output[:, 1].astype(float).tolist()], sample_rate, bit_depth=24)
    verification = verify_wav(Path(path))
    return {
        "path": str(path),
        "sample_rate": sample_rate,
        "bit_depth": 24,
        "safety_gain": round(float(safety_gain), 6),
        "verification": verification,
    }


def _sections(arrangement_plan: dict[str, Any] | None) -> list[dict[str, Any]]:
    sections = list((arrangement_plan or {}).get("sections") or [])
    if sections:
        return sections
    return [
        {"name": "intro_hook_hint", "start_time": 0.0, "duration": 4.0, "energy": 3},
        {"name": "main_hook", "start_time": 4.0, "duration": 16.0, "energy": 5},
        {"name": "verse_groove", "start_time": 20.0, "duration": 16.0, "energy": 2},
        {"name": "hook_return", "start_time": 36.0, "duration": 16.0, "energy": 5},
        {"name": "breakdown_filtered_lead", "start_time": 52.0, "duration": 16.0, "energy": 2},
        {"name": "final_hook", "start_time": 68.0, "duration": 20.0, "energy": 5},
        {"name": "clean_outro_or_loop", "start_time": 88.0, "duration": 12.0, "energy": 1},
    ]


def target_duration_seconds(arrangement_plan: dict[str, Any] | None, fallback: float = 100.0) -> float:
    ends: list[float] = []
    for section in _sections(arrangement_plan):
        start = section.get("start_time", section.get("start", 0.0))
        duration = section.get("duration")
        end = section.get("end")
        try:
            ends.append(float(start) + float(duration if duration is not None else 0.0))
        except (TypeError, ValueError):
            if end is not None:
                try:
                    ends.append(float(end))
                except (TypeError, ValueError):
                    pass
    return min(max(4.0, max(ends) if ends else fallback), 120.0)


def _fade_edges(audio: np.ndarray, sample_rate: int, fade_ms: float = 18.0) -> np.ndarray:
    samples = audio.astype(np.float32, copy=True)
    fade = min(max(1, int(sample_rate * fade_ms / 1000.0)), samples.shape[0] // 3 if samples.shape[0] else 0)
    if fade > 0:
        samples[:fade] *= np.linspace(0.0, 1.0, fade, dtype=np.float32)[:, None]
        samples[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)[:, None]
    return samples


def _fit_segment(source: np.ndarray, start_frame: int, frame_count: int) -> np.ndarray:
    if frame_count <= 0:
        return np.zeros((0, 2), dtype=np.float32)
    if source.size == 0:
        return np.zeros((frame_count, 2), dtype=np.float32)
    start = max(0, min(source.shape[0], start_frame))
    end = min(source.shape[0], start + frame_count)
    segment = source[start:end]
    if segment.shape[0] >= frame_count:
        return segment[:frame_count].astype(np.float32)
    repeats = int(np.ceil(frame_count / max(1, source.shape[0])))
    tiled = np.tile(source, (repeats + 1, 1))
    return tiled[:frame_count].astype(np.float32)


def build_source_music_bus(source_audio: np.ndarray, sample_rate: int, arrangement_plan: dict[str, Any] | None) -> tuple[np.ndarray, dict[str, Any]]:
    sections = _sections(arrangement_plan)
    total_frames = int(target_duration_seconds(arrangement_plan) * sample_rate)
    source = to_stereo(source_audio)
    bus = np.zeros((total_frames, 2), dtype=np.float32)
    placements: list[dict[str, Any]] = []
    source_frames = max(1, source.shape[0])
    for index, section in enumerate(sections):
        name = str(section.get("name", f"section_{index}"))
        start_time = float(section.get("start_time", section.get("start", 0.0)) or 0.0)
        duration = float(section.get("duration") or max(0.0, float(section.get("end", start_time + 4.0)) - start_time))
        start_frame = int(start_time * sample_rate)
        frame_count = max(1, int(duration * sample_rate))
        source_start = int((index / max(1, len(sections))) * source_frames)
        if "hook" in name.lower() and source.shape[0] > frame_count:
            source_start = int(min(source.shape[0] - frame_count, source.shape[0] * 0.18))
        segment = _fit_segment(source, source_start, frame_count)
        segment = _fade_edges(segment, sample_rate)
        energy = int(section.get("energy", 3) or 3)
        gain_db = {-1: -13.0, 0: -13.0, 1: -11.0, 2: -10.5, 3: -9.5, 4: -8.7, 5: -8.0}.get(energy, -9.5)
        if "intro" in name.lower() or "breakdown" in name.lower() or "filtered" in name.lower():
            segment = filter_audio(segment, 80.0, 6_500.0, sample_rate, order=2)
            gain_db -= 1.0
        if "outro" in name.lower():
            gain_db -= 3.0
        end_frame = min(bus.shape[0], start_frame + segment.shape[0])
        if end_frame > start_frame:
            bus[start_frame:end_frame] += segment[: end_frame - start_frame] * db_to_linear(gain_db)
            placements.append(
                {
                    "section": name,
                    "start_time": round(start_time, 3),
                    "duration": round(duration, 3),
                    "source_start_seconds": round(source_start / sample_rate, 3),
                    "gain_db": gain_db,
                }
            )
    return bus.astype(np.float32), {
        "created": True,
        "bus": "source_music_bus",
        "target_duration_seconds": round(total_frames / sample_rate, 3),
        "placements": placements,
        "restructure_applied": True,
    }


def _overlay(target: np.ndarray, clip: np.ndarray, start_frame: int, gain_db: float = 0.0) -> int:
    if start_frame >= target.shape[0] or clip.size == 0:
        return 0
    stereo = to_stereo(clip) * db_to_linear(gain_db)
    end = min(target.shape[0], start_frame + stereo.shape[0])
    if end <= start_frame:
        return 0
    target[start_frame:end] += stereo[: end - start_frame]
    return end - start_frame


def build_generated_lead_bus(
    lead_plan: dict[str, Any] | None,
    arrangement_plan: dict[str, Any] | None,
    *,
    target_frames: int,
    sample_rate: int = TARGET_SAMPLE_RATE,
) -> tuple[np.ndarray, dict[str, Any]]:
    bus = np.zeros((target_frames, 2), dtype=np.float32)
    if not lead_plan:
        return bus, {"created": False, "bus": "generated_lead_bus", "reason": "no lead plan"}
    motif_audio = render_motifs_to_audio(
        lead_plan.get("motifs", []),
        tempo_bpm=float(lead_plan.get("tempo_bpm", 148)),
        sound_design=lead_plan.get("sound_design", {}),
        sample_rate=sample_rate,
    )
    placements: list[dict[str, Any]] = []
    for section in _sections(arrangement_plan):
        name = str(section.get("name", "section"))
        lower = name.lower()
        if "hook" not in lower and "intro" not in lower and "breakdown" not in lower:
            continue
        start = float(section.get("start_time", section.get("start", 0.0)) or 0.0)
        duration = float(section.get("duration") or 4.0)
        gain_db = -8.8 if "hook" in lower else -13.5
        cursor = 0.0
        while cursor < duration:
            frame = int((start + cursor) * sample_rate)
            written = _overlay(bus, motif_audio, frame, gain_db=gain_db)
            if written:
                placements.append({"section": name, "time": round(start + cursor, 3), "gain_db": gain_db})
            cursor += max(2.0, min(duration, motif_audio.shape[0] / sample_rate))
            if len(placements) > 48:
                break
    bus, lead_safety_gain = normalize_peak(bus, -6.5, max_gain_db=0.0)
    return bus.astype(np.float32), {
        "created": bool(placements),
        "bus": "generated_lead_bus",
        "motif_ids": [motif.get("motif_id") for motif in lead_plan.get("motifs", [])],
        "placements": placements,
        "safety_gain": round(float(lead_safety_gain), 6),
        "new_lead_hook_rendered": bool(placements),
    }


def fit_optional_bus(audio: np.ndarray | None, source_rate: int, target_frames: int, target_rate: int = TARGET_SAMPLE_RATE) -> tuple[np.ndarray, dict[str, Any]]:
    bus = np.zeros((target_frames, 2), dtype=np.float32)
    if audio is None or audio.size == 0:
        return bus, {"created": False, "bus": "sample_motif_bus", "reason": "no sample motif audio"}
    rendered = resample_audio(audio, source_rate, target_rate)
    count = min(target_frames, rendered.shape[0])
    bus[:count] += rendered[:count] * db_to_linear(-2.0)
    bus, safety_gain = normalize_peak(bus, -9.0, max_gain_db=0.0)
    return bus.astype(np.float32), {
        "created": count > 0,
        "bus": "sample_motif_bus",
        "frames_used": int(count),
        "safety_gain": round(float(safety_gain), 6),
    }


def _issue_gain_envelope(issues: list[dict[str, Any]], frame_count: int, sample_rate: int, gain_db: float) -> np.ndarray:
    gain = np.ones(frame_count, dtype=np.float32)
    target = db_to_linear(gain_db)
    fade = max(1, int(0.02 * sample_rate))
    for issue in issues:
        start = max(0, min(frame_count, int(float(issue.get("start", 0.0) or 0.0) * sample_rate)))
        end = max(start + 1, min(frame_count, int(float(issue.get("end", (start / sample_rate) + 1.0) or 1.0) * sample_rate)))
        segment = np.full(end - start, target, dtype=np.float32)
        edge = min(fade, len(segment) // 2)
        if edge > 0:
            segment[:edge] = np.linspace(1.0, target, edge, dtype=np.float32)
            segment[-edge:] = np.linspace(target, 1.0, edge, dtype=np.float32)
        gain[start:end] = np.minimum(gain[start:end], segment)
    return gain


def demote_vocal_texture_in_source(source_bus: np.ndarray, sample_rate: int, vocal_texture_plan: dict[str, Any] | None) -> tuple[np.ndarray, dict[str, Any]]:
    issues = list((vocal_texture_plan or {}).get("detected_issues") or [])
    if not issues:
        return source_bus.astype(np.float32), {
            "created": False,
            "bus": "vocal_texture_bus",
            "reason": "no detected vocal texture issue",
            "claim_guard": {"vocal_removal_performed": False, "stem_level_control_from_stereo_claimed": False},
        }
    stereo = to_stereo(source_bus)
    mid = (stereo[:, 0] + stereo[:, 1]) * 0.5
    side = (stereo[:, 0] - stereo[:, 1]) * 0.5
    target_band = bandpass(mid[:, None], 300.0, 3_000.0, sample_rate, order=2)[:, 0]
    envelope = _issue_gain_envelope(issues, len(mid), sample_rate, gain_db=-3.0)
    new_mid = mid + target_band * (envelope - 1.0)
    demoted = np.column_stack((new_mid + side, new_mid - side)).astype(np.float32)
    return demoted, {
        "created": True,
        "bus": "vocal_texture_bus",
        "method": "center-band demotion on source_music_bus",
        "issue_count": len(issues),
        "claim_guard": {
            "vocal_removal_performed": False,
            "stem_level_control_from_stereo_claimed": False,
            "full_stereo_processing_is_demote_only": True,
        },
    }


def duck_source_under_lead(source_bus: np.ndarray, lead_bus: np.ndarray, sample_rate: int) -> tuple[np.ndarray, dict[str, Any]]:
    if lead_bus.size == 0 or float(np.max(np.abs(lead_bus))) <= 1e-5:
        return source_bus.astype(np.float32), {"created": False, "reason": "lead bus absent or silent"}
    band = DynamicEQBand(900.0, 5_500.0, -42.0, -2.4, ratio_slope=0.38, attack_ms=6.0, release_ms=120.0, mode="cut", detector="rms")
    processed, report = dynamic_band_process(source_bus, lead_bus, band, sample_rate)
    return processed.astype(np.float32), {"created": True, "method": "lead-pocket dynamic EQ", "report": report}


def mono_sub_and_upper_width(audio: np.ndarray, sample_rate: int, width: float = 1.08) -> tuple[np.ndarray, dict[str, Any]]:
    stereo = to_stereo(audio)
    low = bandpass(stereo, 20.0, 140.0, sample_rate, order=2)
    residual = stereo - low
    mono_low = np.mean(low, axis=1, dtype=np.float32)
    mid = (residual[:, 0] + residual[:, 1]) * 0.5
    side = (residual[:, 0] - residual[:, 1]) * 0.5 * width
    processed = np.column_stack((mid + side + mono_low, mid - side + mono_low)).astype(np.float32)
    return processed, {"created": True, "method": "sub mono + restrained upper width", "width_factor": width}


def rescue_premaster(audio: np.ndarray, sample_rate: int, *, final_mode: bool = False) -> tuple[np.ndarray, dict[str, Any]]:
    cleaned = filter_audio(to_stereo(audio), 24.0, min(18_000.0, sample_rate / 2 - 100), sample_rate, order=2)
    cleaned = np.tanh(cleaned * 1.04).astype(np.float32) / math.tanh(1.04)
    target = -1.2 if final_mode else -3.0
    mastered, safety_gain = normalize_peak(cleaned, target, max_gain_db=3.0)
    mastered = np.clip(mastered, -0.98, 0.98).astype(np.float32)
    return mastered, {
        "created": True,
        "target_peak_dbfs": target,
        "safety_gain": round(float(safety_gain), 6),
        "peak_dbfs": round(peak_db(mastered), 2),
        "rms_dbfs": round(rms_db(mastered), 2),
        "clipping_count": clipping_count(mastered),
    }


def build_rescue_mix(
    *,
    source_audio: np.ndarray,
    source_sample_rate: int,
    arrangement_plan: dict[str, Any] | None,
    lead_plan: dict[str, Any] | None = None,
    sample_motif_audio: np.ndarray | None = None,
    sample_motif_sample_rate: int = TARGET_SAMPLE_RATE,
    vocal_texture_plan: dict[str, Any] | None = None,
    final_mode: bool = False,
) -> dict[str, Any]:
    source = resample_audio(source_audio, source_sample_rate, TARGET_SAMPLE_RATE)
    source_bus, source_report = build_source_music_bus(source, TARGET_SAMPLE_RATE, arrangement_plan)
    target_frames = source_bus.shape[0]
    lead_bus, lead_report = build_generated_lead_bus(lead_plan, arrangement_plan, target_frames=target_frames, sample_rate=TARGET_SAMPLE_RATE)
    sample_bus, sample_report = fit_optional_bus(sample_motif_audio, sample_motif_sample_rate, target_frames, TARGET_SAMPLE_RATE)
    source_bus, vocal_report = demote_vocal_texture_in_source(source_bus, TARGET_SAMPLE_RATE, vocal_texture_plan)
    ducked_source, duck_report = duck_source_under_lead(source_bus, lead_bus, TARGET_SAMPLE_RATE)
    fx_returns = (lead_bus * 0.08 + sample_bus * 0.05).astype(np.float32)
    premaster = ducked_source + lead_bus + sample_bus + fx_returns
    premaster, ms_report = mono_sub_and_upper_width(premaster, TARGET_SAMPLE_RATE)
    master, master_report = rescue_premaster(premaster, TARGET_SAMPLE_RATE, final_mode=final_mode)
    return {
        "audio": master,
        "sample_rate": TARGET_SAMPLE_RATE,
        "bus_architecture": [
            "source_music_bus",
            "generated_lead_bus",
            "sample_motif_bus",
            "vocal_texture_bus if separable",
            "fx_returns",
            "premaster",
            "master",
        ],
        "bus_reports": {
            "source_music_bus": source_report,
            "generated_lead_bus": lead_report,
            "sample_motif_bus": sample_report,
            "vocal_texture_bus": vocal_report,
            "dynamic_eq": duck_report,
            "mid_side": ms_report,
            "master": master_report,
        },
        "claim_guard": {
            "stem_level_remix_claimed": False,
            "vocal_removal_claimed": False,
            "kick_replacement_claimed": False,
            "drum_rewrite_claimed": False,
            "plugin_insertion_claimed": False,
            "logic_automation_success_claimed": False,
        },
        "metrics": {
            "duration_seconds": round(master.shape[0] / TARGET_SAMPLE_RATE, 3),
            "peak_dbfs": round(peak_db(master), 2),
            "rms_dbfs": round(rms_db(master), 2),
            "clipping_count": clipping_count(master),
            "side_mid_db": side_mid_db(master),
        },
    }
