from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from audio_analysis import read_wav_float
from export_audio import verify_wav, write_float_wav
from loudness_estimation import db_to_linear, linear_to_db
from vocal_effects_ffmpeg import detect_ffmpeg_effect_support
from vocal_export import mix_vocals_with_beat
from vocal_fx_intent import build_vocal_fx_intent
from vocal_mix_autopilot import build_vocal_mix_chain


PROCESSED_NAMES = {
    "lead_vocal": "processed_lead_vocal.wav",
    "adlibs": "processed_adlibs.wav",
    "backing_vocals": "processed_backing_vocals.wav",
}


def _peak(channels: list[list[float]]) -> float:
    return max((abs(sample) for channel in channels for sample in channel), default=0.0)


def _gain_stage(channels: list[list[float]], target_peak_dbfs: float = -6.0) -> tuple[list[list[float]], float, str]:
    peak = _peak(channels)
    if peak <= 0.0:
        return channels, 1.0, "silent or near-silent input; gain unchanged"
    target = db_to_linear(target_peak_dbfs)
    if peak > target:
        gain = target / peak
        return [[sample * gain for sample in channel] for channel in channels], gain, f"trimmed to conservative {target_peak_dbfs:.1f} dBFS working peak"
    if peak < db_to_linear(-18.0):
        gain = min(target / peak, 2.0)
        return [[sample * gain for sample in channel] for channel in channels], gain, "raised very quiet vocal cautiously, capped at +6 dB"
    return channels, 1.0, "input peak already safe; gain unchanged"


def _high_pass_channel(samples: list[float], sample_rate: int, cutoff_hz: float) -> list[float]:
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
        previous_output = value
        previous_input = sample
    return output


def _high_pass(channels: list[list[float]], sample_rate: int, cutoff_hz: float) -> list[list[float]]:
    return [_high_pass_channel(channel, sample_rate, cutoff_hz) for channel in channels]


def _compress_sample(sample: float, threshold: float, ratio: float) -> float:
    sign = -1.0 if sample < 0.0 else 1.0
    value = abs(sample)
    if value <= threshold:
        return sample
    compressed = threshold + (value - threshold) / ratio
    return sign * compressed


def _level_compress(channels: list[list[float]], style: str) -> tuple[list[list[float]], str]:
    if style == "aggressive":
        threshold = db_to_linear(-18.0)
        ratio = 2.2
    elif style == "rap_forward":
        threshold = db_to_linear(-17.0)
        ratio = 2.0
    else:
        threshold = db_to_linear(-14.0)
        ratio = 1.55
    processed = [[_compress_sample(sample, threshold, ratio) for sample in channel] for channel in channels]
    return processed, f"basic sample-level leveling compression, threshold about {linear_to_db(threshold):.1f} dBFS, ratio {ratio:.2f}:1"


def _soft_deess(channels: list[list[float]], analysis_item: dict[str, Any], strength: str) -> tuple[list[list[float]], str]:
    candidates = analysis_item.get("sibilance_candidates", [])
    if not candidates:
        return channels, "no sibilance candidates detected; de-essing left manual/listening-based"
    gain = {"light": 0.94, "medium": 0.9, "strong": 0.86}.get(strength, 0.9)
    processed = [list(channel) for channel in channels]
    # This is a conservative broad attenuation on candidate windows, not a true split-band de-esser.
    sample_rate = analysis_item.get("metrics", {}).get("sample_rate", 0)
    for candidate in candidates:
        start = int(candidate["start"] * sample_rate)
        end = int(candidate["end"] * sample_rate)
        for channel in processed:
            for index in range(max(0, start), min(len(channel), end)):
                channel[index] *= gain
    return processed, "conservative candidate-window attenuation applied; true split-band de-essing should be checked in Logic"


def _saturate(channels: list[list[float]], style: str) -> tuple[list[list[float]], str]:
    if style not in {"hyperpop", "digicore", "aggressive"}:
        return channels, "saturation bypassed for conservative/natural vocal safety"
    drive = 1.08 if style in {"hyperpop", "digicore"} else 1.12
    normalizer = math.tanh(drive)
    processed = [[math.tanh(sample * drive) / normalizer * 0.96 for sample in channel] for channel in channels]
    return processed, f"subtle soft saturation applied for {style}; output kept below clipping"


def _request_text(options: dict[str, Any]) -> str:
    brief = options.get("creative_brief") or {}
    pieces = [
        options.get("vocal_fx_request"),
        options.get("reference_text"),
        options.get("creative_target"),
        options.get("vocal_direction"),
        brief.get("creative_target"),
        brief.get("vocal_direction"),
    ]
    return " ".join(str(piece) for piece in pieces if piece)


def _low_level_eq_plan(analysis_item: dict[str, Any]) -> list[str]:
    notes = ["high-pass rumble removal applied with a conservative first-order filter"]
    if analysis_item.get("low_rumble"):
        notes.append("low rumble candidates detected; high-pass is warranted")
    if analysis_item.get("harshness_candidates"):
        notes.append("harshness candidates detected; manual Logic resonance control recommended before boosting air")
    metrics = analysis_item.get("metrics", {})
    if metrics.get("noise_floor_estimate", {}).get("estimated_noise_floor_dbfs") is not None:
        notes.append("noise floor estimated; no destructive denoise applied in fallback processor")
    return notes


def _process_one_vocal(
    label: str,
    input_path: Path,
    output_path: Path,
    analysis_item: dict[str, Any],
    options: dict[str, Any],
) -> dict[str, Any]:
    metadata, channels = read_wav_float(input_path)
    steps: list[str] = []
    processed, gain, gain_note = _gain_stage(channels)
    steps.append(gain_note)
    cutoff = 95.0 if label == "lead_vocal" else 120.0
    if options.get("vocal_style") == "rap_forward":
        cutoff = 80.0 if label == "lead_vocal" else cutoff
    processed = _high_pass(processed, metadata["sample_rate"], cutoff)
    steps.extend(_low_level_eq_plan(analysis_item))
    processed, compression_note = _level_compress(processed, options.get("vocal_style", "polished"))
    steps.append(compression_note)
    processed, deess_note = _soft_deess(processed, analysis_item, options.get("deess", "medium"))
    steps.append(deess_note)
    processed, saturation_note = _saturate(processed, options.get("vocal_style", "polished"))
    steps.append(saturation_note)
    processed, safety_gain, safety_note = _gain_stage(processed, target_peak_dbfs=-3.5)
    steps.append(f"final safety pass: {safety_note}")
    write_float_wav(output_path, processed, metadata["sample_rate"])
    verification = verify_wav(output_path)
    return {
        "label": label,
        "input_path": str(input_path),
        "output_path": str(output_path),
        "created": True,
        "input_sample_rate": metadata["sample_rate"],
        "input_channels": metadata["channels"],
        "gain_stage_gain": gain,
        "final_safety_gain": safety_gain,
        "steps": steps,
        "verification": verification,
    }


def _existing_direct_vocals(options: dict[str, Any]) -> dict[str, Path]:
    pairs = {
        "lead_vocal": options.get("lead_vocal_file") or options.get("vocal_file"),
        "adlibs": options.get("adlib_file"),
        "backing_vocals": options.get("backing_vocal_file"),
    }
    existing: dict[str, Path] = {}
    for label, path_text in pairs.items():
        if path_text:
            path = Path(path_text).expanduser()
            if path.exists():
                existing[label] = path
    return existing


def process_vocal_assets(options: dict[str, Any], vocal_analysis: dict[str, Any], project_root: Path) -> dict[str, Any]:
    mode = options.get("mode", "instrumental_beat")
    vocal_dir = project_root / "07_VOCAL_PROCESSING"
    mix_dir = project_root / "09_MIX_MASTER"
    vocal_dir.mkdir(parents=True, exist_ok=True)
    mix_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_support = detect_ffmpeg_effect_support()
    vocal_fx_intent = build_vocal_fx_intent(_request_text(options))
    result: dict[str, Any] = {
        "mode": mode,
        "processed_vocals": {},
        "pre_master": {"created": False, "path": str(mix_dir / "pre_master.wav")},
        "ffmpeg_effect_support": ffmpeg_support.__dict__,
        "vocal_fx_intent": vocal_fx_intent,
        "vocal_mix_autopilot": build_vocal_mix_chain(
            input_mode=mode,
            pitch_guide=(vocal_analysis.get("vocal_to_code") or {}).get("pitch_correction_guide"),
            requested_style=options.get("vocal_style", "polished"),
        ),
        "manual_logic_instructions": [
            "Build high-quality reverb/delay as sends in Logic Pro rather than baking heavy fallback FX.",
            "Use manual clip gain for breaths, plosives, and phrase endings before final compression.",
        ],
        "limitations": [],
    }
    plugin_instruction = vocal_fx_intent.get("plugin_application", {}).get("manual_logic_instruction")
    if plugin_instruction:
        result["manual_logic_instructions"].append(plugin_instruction)
    plugin_claim = vocal_fx_intent.get("plugin_application", {}).get("claim_language")
    if plugin_claim:
        result["manual_logic_instructions"].append(plugin_claim)
    if vocal_fx_intent.get("plugin_application", {}).get("fallback") == "generic saturation approximation":
        result["manual_logic_instructions"].append(
            "If fallback saturation is used, label it generic saturation approximation, not Decapitator applied."
        )

    if mode == "full_song_stereo":
        result["limitations"].extend(
            [
                "Full stereo song mode does not create processed isolated vocal files.",
                "Only broad mix/master processing is appropriate without separate vocals or stems.",
            ]
        )
        return result
    if mode not in {"vocal_plus_beat", "stems"}:
        result["limitations"].append("No separate vocal file was provided; vocal processing was skipped.")
        return result

    direct_vocals = _existing_direct_vocals(options)
    for label, input_path in direct_vocals.items():
        analysis_item = vocal_analysis.get("files", {}).get(label, {})
        if analysis_item.get("analysis_error"):
            result["processed_vocals"][label] = {
                "created": False,
                "input_path": str(input_path),
                "reason": f"input could not be analyzed safely: {analysis_item['analysis_error']}",
            }
            continue
        output_path = vocal_dir / PROCESSED_NAMES[label]
        try:
            result["processed_vocals"][label] = _process_one_vocal(label, input_path, output_path, analysis_item, options)
        except (OSError, ValueError) as error:
            result["processed_vocals"][label] = {"created": False, "input_path": str(input_path), "reason": str(error)}

    processed_paths = {
        label: Path(item["output_path"])
        for label, item in result["processed_vocals"].items()
        if item.get("created") and item.get("output_path")
    }
    beat_text = options.get("beat_file")
    if beat_text and processed_paths:
        beat_path = Path(beat_text).expanduser()
        if beat_path.exists():
            try:
                result["pre_master"] = mix_vocals_with_beat(beat_path, processed_paths, mix_dir / "pre_master.wav", vocal_analysis)
            except (OSError, ValueError) as error:
                result["pre_master"] = {"created": False, "path": str(mix_dir / "pre_master.wav"), "reason": str(error)}
        else:
            result["pre_master"] = {"created": False, "path": str(mix_dir / "pre_master.wav"), "reason": "beat file missing"}
    elif processed_paths:
        result["pre_master"] = {
            "created": False,
            "path": str(mix_dir / "pre_master.wav"),
            "reason": "processed vocal exists, but no beat file was provided for vocal+beat mixing",
        }
    return result
