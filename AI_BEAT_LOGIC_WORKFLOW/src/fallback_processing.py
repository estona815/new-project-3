from __future__ import annotations

import json
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from audio_analysis import ANALYSIS_JSON, WORKING_WAV, read_wav_float
from config import load_defaults
from export_audio import ffmpeg_path, run_command, verify_wav, write_float_wav
from ffmpeg_filters import build_filter_chain
from humanization_rubric import render_style_match_qc
from mix_master_autopilot import build_mix_master_plan
from paths import PROJECT_ROOT


FALLBACK_OUTPUT = PROJECT_ROOT / "04_PROCESSED_AUDIO" / "fallback_processed.wav"
PROCESSING_LOG = PROJECT_ROOT / "04_PROCESSED_AUDIO" / "processing_log.md"
REFERENCE_PROFILE = PROJECT_ROOT / "08_REFERENCE_MATCH" / "reference_target_profile.json"


@dataclass(frozen=True)
class FallbackDecision:
    start: float
    end: float
    fade_in: float
    fade_out: float
    reason: str


def load_analysis(path: Path = ANALYSIS_JSON) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_reference_profile(path: Path = REFERENCE_PROFILE) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def choose_section(analysis: dict[str, Any], options: dict[str, Any]) -> FallbackDecision:
    duration = float(analysis.get("metadata", {}).get("duration_seconds", 0.0) or 0.0)
    if duration <= 0:
        duration = 0.0
    length_mode = options.get("length_mode", "under_2min")
    arrangement = analysis.get("arrangement_candidates", {})
    hook = arrangement.get("first_hook_or_main_motif_entrance") or arrangement.get("main_melody_strongest_region") or {}
    silence = analysis.get("silence_detection", {})
    intro = silence.get("intro_silence")
    outro = silence.get("outro_silence")

    if length_mode == "specific_section_only" and options.get("section_start") is not None and options.get("section_end") is not None:
        start = max(0.0, float(options["section_start"]))
        end = min(duration, float(options["section_end"])) if duration else float(options["section_end"])
        return FallbackDecision(start, max(start, end), 0.02, 1.0, "user-provided specific section")

    if length_mode == "15sec_reels":
        hook_start = float(hook.get("start", 0.0) or 0.0)
        start = max(0.0, hook_start - 2.0)
        end = start + 15.0
        if duration and end > duration:
            end = duration
            start = max(0.0, end - 15.0)
        return FallbackDecision(start, end, 0.02, 0.8, "15-second reels section around strongest hook candidate")

    if length_mode == "keep_original":
        start = float(intro.get("end", 0.0)) if intro else 0.0
        end = float(outro.get("start", duration)) if outro else duration
        if end <= start:
            start, end = 0.0, duration
        return FallbackDecision(start, end, 0.02, 1.2, "keep original, trimming only detected intro/outro silence")

    start = float(intro.get("end", 0.0)) if intro else 0.0
    hook_start = float(hook.get("start", start) or start)
    if hook_start > 16.0:
        start = max(0.0, hook_start - 16.0)
    end = min(duration, start + 120.0) if duration else start + 120.0
    return FallbackDecision(start, end, 0.02, 1.5, "under-2-minute section keeping strongest melodic candidate early")


def apply_python_fallback(input_path: Path, output_path: Path, decision: FallbackDecision) -> list[str]:
    metadata, channels = read_wav_float(input_path)
    sample_rate = int(metadata["sample_rate"])
    start_frame = max(0, int(decision.start * sample_rate))
    end_frame = min(min(len(channel) for channel in channels), int(decision.end * sample_rate))
    if end_frame <= start_frame:
        raise ValueError("Fallback trim range is empty.")

    trimmed = [channel[start_frame:end_frame] for channel in channels]
    frame_count = end_frame - start_frame
    fade_in_frames = min(frame_count, int(decision.fade_in * sample_rate))
    fade_out_frames = min(frame_count, int(decision.fade_out * sample_rate))

    for channel in trimmed:
        for index in range(frame_count):
            gain = 1.0
            if fade_in_frames > 0 and index < fade_in_frames:
                gain *= index / fade_in_frames
            if fade_out_frames > 0 and index >= frame_count - fade_out_frames:
                gain *= max(0.0, (frame_count - index) / fade_out_frames)
            channel[index] *= gain

    peak = max((abs(sample) for channel in trimmed for sample in channel), default=0.0)
    if peak > 0:
        target = 10 ** (-3.0 / 20.0)
        gain = min(target / peak, 1.0 if peak > target else target / peak)
        for channel in trimmed:
            for index, sample in enumerate(channel):
                channel[index] = max(-0.999, min(0.999, sample * gain))
        gain_note = f"Python gain staging to target around -3 dBFS, gain factor {gain:.4f}"
    else:
        gain_note = "Python gain staging skipped because signal is silent"

    write_float_wav(output_path, trimmed, sample_rate)
    return [
        "ffmpeg unavailable; used Python stereo-only fallback",
        "trim/fade applied in Python",
        gain_note,
        "basic EQ/compression/limiter unavailable without ffmpeg in this branch",
    ]


def apply_ffmpeg_fallback(input_path: Path, output_path: Path, decision: FallbackDecision, analysis: dict[str, Any]) -> tuple[list[str], list[str]]:
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg is unavailable")
    duration = max(0.0, decision.end - decision.start)
    filter_chain, notes = build_filter_chain(analysis, decision.fade_in, decision.fade_out, duration)
    command = [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-ss",
        f"{decision.start:.3f}",
        "-t",
        f"{duration:.3f}",
        "-i",
        str(input_path),
        "-af",
        filter_chain,
        "-ar",
        str(analysis.get("metadata", {}).get("sample_rate", 48000)),
        "-acodec",
        "pcm_s24le",
        str(output_path),
    ]
    result = run_command(command)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg fallback command failed")
    return command, notes


def unique_backup_path(output_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = output_path.with_name(f"{output_path.stem}_backup_{timestamp}{output_path.suffix}")
    index = 1
    while candidate.exists():
        candidate = output_path.with_name(f"{output_path.stem}_backup_{timestamp}_{index:03d}{output_path.suffix}")
        index += 1
    return candidate


def write_processing_log(
    path: Path,
    decision: FallbackDecision,
    notes: list[str],
    verification: dict[str, Any],
    command: list[str] | None,
    reference_profile: dict[str, Any] | None = None,
) -> None:
    command_text = " ".join(command) if command else "No ffmpeg command used."
    note_text = "\n".join(f"- {note}" for note in notes)
    reference_text = ""
    if reference_profile:
        reference_text = (
            "\n## Reference Target Handling\n\n"
            "- Reference-inspired goals can guide broad low-end, transient, EQ, and arrangement decisions.\n"
            "- Stereo fallback cannot replace drum patterns, rewrite MIDI, or layer exact kick/snare/hat parts.\n"
            "- Manual Logic drum replacement or layering is required for real Love Blur-style drum programming changes.\n\n"
            f"{render_style_match_qc(reference_profile, stereo_only=True)}\n"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Fallback Processing Log\n\n"
        "This fallback output is a conservative stereo-only process. It does not claim full human arrangement, stem remixing, or Logic Pro mixing.\n\n"
        "## Commands Used\n\n"
        f"`{command_text}`\n\n"
        "## Trim Decisions\n\n"
        f"- start: {decision.start:.3f}s\n"
        f"- end: {decision.end:.3f}s\n"
        f"- reason: {decision.reason}\n\n"
        "## Gain / Fade / Filter Decisions\n\n"
        f"{note_text}\n\n"
        f"{reference_text}"
        "## Limitations\n\n"
        "- Cannot truly rewrite arrangement in separate stems.\n"
        "- Cannot manually remove random FX without section edits.\n"
        "- Cannot independently change drum patterns or rebalance stems from a single stereo file.\n"
        "- Vocal-like texture suppression is heuristic and stereo-only; no real vocal removal is claimed.\n\n"
        "## Verification\n\n"
        f"- output: `{verification['path']}`\n"
        f"- duration: {verification['duration_seconds']:.3f}s\n"
        f"- sample_rate: {verification['sample_rate']}\n"
        f"- channels: {verification['channels']}\n"
        f"- bit_depth: {verification['bit_depth']}\n"
        f"- peak_dbfs: {verification['peak_dbfs']:.3f}\n",
        encoding="utf-8",
    )


def run_fallback_processing(
    input_path: Path = WORKING_WAV,
    output_path: Path = FALLBACK_OUTPUT,
    analysis_path: Path = ANALYSIS_JSON,
    log_path: Path = PROCESSING_LOG,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not input_path.exists():
        raise FileNotFoundError(f"Fallback input missing: {input_path}")
    analysis = load_analysis(analysis_path)
    reference_profile = load_reference_profile()
    resolved_options = options or load_defaults()
    mix_plan = build_mix_master_plan(
        input_mode=resolved_options.get("mode", "instrumental_beat"),
        style_target=resolved_options.get("arrangement_genre", "commercial_digicore_hyperpop"),
        master_target_mode=resolved_options.get("master_loudness", "master_ready_headroom"),
    )
    decision = choose_section(analysis, resolved_options)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.replace(unique_backup_path(output_path))

    command: list[str] | None = None
    try:
        command, notes = apply_ffmpeg_fallback(input_path, output_path, decision, analysis)
    except (FileNotFoundError, RuntimeError) as error:
        notes = apply_python_fallback(input_path, output_path, decision)
        notes.append(f"ffmpeg path not used: {error}")

    verification = verify_wav(output_path)
    verification["status"] = "FALLBACK_AUDIO_EXPORTED_UNVERIFIED"
    verification["verified"] = False
    if verification["peak_dbfs"] > -0.1:
        raise ValueError("Fallback output peak is too close to clipping.")
    write_processing_log(log_path, decision, notes, verification, command, reference_profile)
    return {"decision": decision, "verification": verification, "notes": notes, "command": command, "mix_master_plan": mix_plan}


def main() -> int:
    result = run_fallback_processing()
    print(f"Wrote fallback output: {result['verification']['path']}")
    print(f"Peak: {result['verification']['peak_dbfs']:.2f} dBFS")
    print(f"Log: {PROCESSING_LOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
