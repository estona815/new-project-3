from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from audio_analysis import read_wav_float
from audio_metrics import bandpass, clipping_count, db_to_linear, peak_db, to_stereo
from export_audio import verify_wav, write_float_wav
from vocal_texture_classifier import has_bad_vocal_lead_role


STEM_MODES = {"stems", "vocal_stem", "separate_vocal", "vocal_plus_beat"}


def has_separate_vocal_control(mode: str | None, vocal_stem_path: str | Path | None = None) -> bool:
    if vocal_stem_path and Path(vocal_stem_path).expanduser().exists():
        return True
    return str(mode or "").lower() in STEM_MODES


def build_vocal_texture_actions(
    issues: list[dict[str, Any]],
    *,
    mode: str | None = None,
    has_vocal_stem: bool = False,
    new_lead_available: bool = True,
) -> list[dict[str, Any]]:
    if not issues:
        return [
            {
                "type": "monitor_texture",
                "method": "manual_listening_check",
                "target": "vocal-like texture windows",
                "reason": "no high-risk vocal texture issue was detected",
            }
        ]

    stereo_only = not has_vocal_stem and str(mode or "").lower() in {"full_song_stereo", "unknown", ""}
    actions: list[dict[str, Any]] = []
    if has_vocal_stem:
        actions.extend(
            [
                {
                    "type": "demote_texture",
                    "method": "clip_gain_tone_shaping_deess",
                    "target": "lead vocal/chop stem",
                    "reason": "separate vocal control exists, so reduce unstable texture without damaging the full mix",
                    "manual_logic_required": False,
                },
                {
                    "type": "push_back_texture",
                    "method": "short_reverb_or_delay_send_with_lower_dry_level",
                    "target": "unstable vocal phrase tails",
                    "reason": "preserve atmosphere while stopping the texture from acting as the main hook",
                    "manual_logic_required": True,
                },
            ]
        )
    else:
        actions.extend(
            [
                {
                    "type": "demote_texture",
                    "method": "dynamic_eq_or_volume_automation",
                    "target": "300Hz-3kHz",
                    "reason": "vocal texture should not be main lead",
                    "manual_logic_required": stereo_only,
                },
                {
                    "type": "center_band_soft_attenuation",
                    "method": "mid_side_center_band_demotion",
                    "target": "center-heavy 300Hz-3kHz vocal-like band",
                    "reason": "full stereo source can only reduce attention, not remove the texture",
                    "manual_logic_required": stereo_only,
                },
            ]
        )

    if new_lead_available and has_bad_vocal_lead_role(issues):
        actions.append(
            {
                "type": "replace_role_with_synth_lead",
                "method": "generated lead motif",
                "target": "main hook identity",
                "reason": "new lead/hook should carry the song while vocal texture becomes atmosphere",
                "manual_logic_required": True,
            }
        )

    actions.append(
        {
            "type": "preserve_atmosphere",
            "method": "avoid_destructive_removal",
            "target": "usable emotional texture",
            "reason": "bad AI vocal texture may still contain mood, so only demote the role",
        }
    )
    return actions


def _channels_to_audio(channel_samples: list[list[float]]) -> np.ndarray:
    if not channel_samples:
        return np.zeros((0, 2), dtype=np.float32)
    frame_count = min(len(channel) for channel in channel_samples)
    if frame_count <= 0:
        return np.zeros((0, len(channel_samples)), dtype=np.float32)
    return np.column_stack([np.asarray(channel[:frame_count], dtype=np.float32) for channel in channel_samples])


def _audio_to_channels(audio: np.ndarray, channel_count: int) -> list[list[float]]:
    samples = np.asarray(audio, dtype=np.float32)
    if samples.ndim == 1:
        samples = samples[:, None]
    keep = max(1, min(channel_count, samples.shape[1]))
    return [samples[:, index].astype(float).tolist() for index in range(keep)]


def _issue_gain_envelope(
    issues: list[dict[str, Any]],
    frame_count: int,
    sample_rate: int,
    *,
    gain_value: float,
    fade_ms: float = 18.0,
) -> np.ndarray:
    gain = np.ones(frame_count, dtype=np.float32)
    fade_frames = max(1, int(sample_rate * fade_ms / 1000.0))
    for issue in issues:
        start_seconds = float(issue.get("start", 0.0) or 0.0)
        end_seconds = float(issue.get("end", start_seconds + 1.0) or start_seconds + 1.0)
        start = max(0, min(frame_count, int(start_seconds * sample_rate)))
        end = max(start + 1, min(frame_count, int(end_seconds * sample_rate)))
        segment = np.full(end - start, gain_value, dtype=np.float32)
        fade = min(fade_frames, len(segment) // 2)
        if fade > 0:
            segment[:fade] = np.linspace(1.0, gain_value, fade, dtype=np.float32)
            segment[-fade:] = np.linspace(gain_value, 1.0, fade, dtype=np.float32)
        gain[start:end] = np.minimum(gain[start:end], segment)
    return gain


def _safe_output(audio: np.ndarray) -> tuple[np.ndarray, float]:
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak <= 0.98:
        return audio.astype(np.float32), 1.0
    gain = 0.98 / peak
    return (audio * gain).astype(np.float32), gain


def _process_stereo_center_band(audio: np.ndarray, sample_rate: int, issues: list[dict[str, Any]]) -> tuple[np.ndarray, dict[str, Any]]:
    stereo = to_stereo(audio)
    left = stereo[:, 0]
    right = stereo[:, 1]
    mid = (left + right) * 0.5
    side = (left - right) * 0.5
    target_band = bandpass(mid[:, None], 300.0, 3_000.0, sample_rate, order=2)[:, 0]
    gain = _issue_gain_envelope(issues, len(mid), sample_rate, gain_value=db_to_linear(-3.2))
    new_mid = mid + target_band * (gain - 1.0)
    processed = np.column_stack((new_mid + side, new_mid - side)).astype(np.float32)
    return processed, {
        "method": "mid_side_center_band_demotion",
        "target": "300Hz-3kHz center band",
        "max_band_gain_reduction_db": -3.2,
    }


def _process_stem_demote(audio: np.ndarray, sample_rate: int, issues: list[dict[str, Any]]) -> tuple[np.ndarray, dict[str, Any]]:
    samples = np.asarray(audio, dtype=np.float32)
    if samples.ndim == 1:
        samples = samples[:, None]
    target_band = bandpass(samples, 300.0, 4_500.0, sample_rate, order=2)
    band_gain = _issue_gain_envelope(issues, samples.shape[0], sample_rate, gain_value=db_to_linear(-3.8))
    clip_gain = _issue_gain_envelope(issues, samples.shape[0], sample_rate, gain_value=db_to_linear(-2.2))
    processed = samples * clip_gain[:, None] + target_band * (band_gain[:, None] - 1.0)
    return processed.astype(np.float32), {
        "method": "clip_gain_plus_broad_vocal_band_demotion",
        "target": "300Hz-4.5kHz vocal stem band",
        "max_clip_gain_reduction_db": -2.2,
        "max_band_gain_reduction_db": -3.8,
    }


def process_vocal_texture_demotion(
    input_path: str | Path,
    output_path: str | Path,
    issues: list[dict[str, Any]],
    *,
    mode: str | None = "full_song_stereo",
) -> dict[str, Any]:
    source = Path(input_path).expanduser()
    output = Path(output_path)
    if not source.exists():
        return {
            "created": False,
            "input_path": str(source),
            "output_path": str(output),
            "reason": "input audio not found",
            "claim_guard": {
                "vocal_removal_performed": False,
                "stem_level_control_claimed": False,
            },
        }
    if not issues:
        return {
            "created": False,
            "input_path": str(source),
            "output_path": str(output),
            "reason": "no vocal texture issues to process",
            "claim_guard": {
                "vocal_removal_performed": False,
                "stem_level_control_claimed": False,
            },
        }

    metadata, channels = read_wav_float(source)
    audio = _channels_to_audio(channels)
    input_peak = peak_db(audio)
    separate_control = has_separate_vocal_control(mode)
    if separate_control:
        processed, operation = _process_stem_demote(audio, metadata["sample_rate"], issues)
        stem_claimed = True
    else:
        processed, operation = _process_stereo_center_band(audio, metadata["sample_rate"], issues)
        stem_claimed = False
    processed, safety_gain = _safe_output(processed)
    write_float_wav(output, _audio_to_channels(processed, metadata["channels"]), metadata["sample_rate"])
    verification = verify_wav(output)
    return {
        "created": True,
        "input_path": str(source),
        "output_path": str(output),
        "mode": mode or "unknown",
        "input_peak_dbfs": round(float(input_peak), 2),
        "operation": operation,
        "safety_gain": round(float(safety_gain), 6),
        "verification": verification,
        "clipping_count": clipping_count(processed),
        "claim_guard": {
            "vocal_removal_performed": False,
            "stem_level_control_claimed": stem_claimed,
            "stem_level_control_from_stereo_claimed": False,
            "full_stereo_processing_is_demote_only": not separate_control,
        },
        "limitations": [
            "Processing demotes attention to vocal-like texture; it does not remove vocals.",
            "Full stereo processing cannot provide stem-level vocal control.",
        ],
    }
