from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from audio_analysis import read_wav_float
from config import load_defaults
from export_audio import ffmpeg_path, run_command
from final_verify import expected_final_name, expected_sample_rate, verify_final_export, write_verification_json
from paths import PROJECT_ROOT


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def choose_final_source(project_root: Path = PROJECT_ROOT) -> tuple[Path, str]:
    logic_source = project_root / "03_LOGIC_PROJECT" / "logic_export.wav"
    fallback_source = project_root / "04_PROCESSED_AUDIO" / "fallback_processed.wav"
    if logic_source.exists():
        return logic_source, "logic_export"
    if fallback_source.exists():
        return fallback_source, "fallback_processed"
    raise FileNotFoundError("No final source found. Expected Logic export or fallback_processed.wav.")


def convert_final_wav(source: Path, destination: Path, export_format: str) -> tuple[list[str], str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = expected_sample_rate(export_format)
    ffmpeg = ffmpeg_path()
    if ffmpeg:
        command = [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-i",
            str(source),
            "-ar",
            str(sample_rate),
            "-acodec",
            "pcm_s24le",
            str(destination),
        ]
        result = run_command(command)
        if result.returncode == 0:
            return command, "ffmpeg"

    afconvert = shutil.which("afconvert")
    if afconvert:
        command = [
            afconvert,
            "-f",
            "WAVE",
            "-d",
            f"LEI24@{sample_rate}",
            str(source),
            str(destination),
        ]
        result = run_command(command)
        if result.returncode == 0:
            return command, "afconvert"

    raise RuntimeError("Final WAV export requires ffmpeg or afconvert so the requested 24-bit output can be verified.")


def create_mp3_preview(final_wav: Path, project_root: Path = PROJECT_ROOT) -> tuple[Path | None, str]:
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        return None, "ffmpeg unavailable; MP3 preview skipped"
    preview_path = project_root / "05_FINAL_WAV" / "final_preview.mp3"
    command = [ffmpeg, "-hide_banner", "-y", "-i", str(final_wav), "-codec:a", "libmp3lame", "-b:a", "192k", str(preview_path)]
    result = run_command(command)
    if result.returncode != 0 or not preview_path.exists() or preview_path.stat().st_size <= 0:
        return None, "MP3 preview failed; final WAV remains valid if verification passed"
    return preview_path, "created with ffmpeg"


def original_filename(metadata: dict[str, Any]) -> str:
    original = metadata.get("original_path")
    return Path(original).name if original else "unknown"


def fmt_bool(value: bool) -> str:
    return "yes" if value else "no"


def build_qc_report(
    input_metadata: dict[str, Any],
    analysis: dict[str, Any],
    verification: dict[str, Any],
    final_path: Path,
    mp3_path: Path | None,
    source_type: str,
    conversion_tool: str,
    mp3_note: str,
) -> str:
    vocal = analysis.get("vocal_like_texture_candidates", [])
    low_end = analysis.get("low_end_excess_candidates", [])
    melody_buried = analysis.get("melody_buried_candidates", [])
    arrangement = analysis.get("arrangement_candidates", {})
    glitches = arrangement.get("ai_random_transition_or_glitch_candidates", [])
    repeated = arrangement.get("repeated_loop_blocks", [])
    warnings = verification.get("warnings", [])
    processing_truth = "fallback stereo processing was used" if source_type == "fallback_processed" else "Logic export source was used"

    return f"""# QC Report

## 1. Input File
- original filename: {original_filename(input_metadata)}
- copied input path: {input_metadata.get('copied_path', 'unknown')}
- working wav path: {input_metadata.get('working_wav_path', 'unknown')}

## 2. Final Export
- final WAV path: {final_path}
- MP3 preview path: {mp3_path if mp3_path else 'not created'} ({mp3_note})
- sample rate: {verification.get('sample_rate')}
- bit depth: {verification.get('bit_depth')}
- channels: {verification.get('channels')}
- duration: {verification.get('duration_seconds'):.3f}s
- file size: {verification.get('file_size')} bytes

## 3. Completed Processing Summary
- Source used for final export: {source_type}
- Conversion tool used: {conversion_tool}
- What actually happened: {processing_truth}. This report does not claim Logic mixing if fallback was used.
- Final verification passed: {fmt_bool(bool(verification.get('passed')))}

## 4. Melody Preservation
- Main melody centrality is estimated from analysis, not human listening.
- Melody-buried candidate count: {len(melody_buried)}
- Risk: {'melody may still be buried in flagged sections' if melody_buried else 'no strong melody-buried heuristic warning remained in analysis'}
- Fallback processing is broad stereo processing, so it protects melody mainly by conservative gain/fade/EQ choices rather than stem-level remixing.

## 5. Vocal Chop / AI Texture Suppression
- Detected vocal-like heuristic regions: {len(vocal)}
- What was done: stereo-only fallback may apply conservative global EQ/level treatment; no real vocal removal is claimed.
- What remains: fake voice textures may remain because this pipeline has not used stem separation or manual Logic region editing.

## 6. Drum / 808 Balance
- Low-end warning count: {len(low_end)}
- Kick/808 dominance risk: {'review flagged low-end sections manually' if low_end else 'no strong low-end dominance warning from heuristic analysis'}
- Melody coverage risk: {'possible in melody-buried sections' if melody_buried else 'not strongly flagged by current heuristics'}

## 7. Clipping / Loudness
- peak: {verification.get('peak_dbfs'):.3f} dBFS
- RMS: {verification.get('rms_dbfs'):.3f} dBFS
- clipping count: {verification.get('clipping_count')}
- warning if too loud: {'; '.join(warnings) if warnings else 'none'}
- headroom note: final peak should stay around -1.0 dBFS/dBTP approximation or safer.

## 8. AI-Generated Feel Reduction
- Intro cleanup: handled by fallback trim/fade if analysis or mode selected a shortened section.
- Transition smoothing: fallback can smooth edges with fades, but not detailed region crossfades.
- Random glitch/riser candidates: {len(glitches)}
- Repetition candidates: {len(repeated)}

## 9. Remaining Problems
- Single stereo file limits stem-level control.
- Vocal-like texture could not be fully removed without stem separation or manual editing.
- True drum/808 rearrangement requires stems or manual Logic editing.
- Logic automation may be unavailable, partial, or not used.
- This QC does not replace a human listening pass.

## 10. Next Improvement Options
- Provide stems.
- Run stem separation.
- Manual Logic region editing.
- Create 15-sec reels cut.
- Make alternate version with softer drums.
- Make alternate version with stronger 808.
- Master louder after final arrangement is finished.
"""


def run_final_export_and_qc(options: dict[str, Any] | None = None, project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    resolved_options = options or load_defaults()
    export_format = resolved_options.get("export_format", "wav24_48k")
    length_mode = resolved_options.get("length_mode", "under_2min")
    final_path = project_root / "05_FINAL_WAV" / expected_final_name(export_format)
    source, source_type = choose_final_source(project_root)
    command, conversion_tool = convert_final_wav(source, final_path, export_format)
    mp3_path, mp3_note = create_mp3_preview(final_path, project_root)
    verification = verify_final_export(final_path, export_format, length_mode)
    write_verification_json(verification, project_root / "06_QC_REPORT" / "final_verification.json")

    input_metadata = load_json(project_root / "01_ANALYSIS" / "input_metadata.json")
    analysis = load_json(project_root / "01_ANALYSIS" / "analysis.json")
    report = build_qc_report(input_metadata, analysis, verification, final_path, mp3_path, source_type, conversion_tool, mp3_note)
    report_path = project_root / "06_QC_REPORT" / "qc_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return {
        "final_path": final_path,
        "mp3_path": mp3_path,
        "qc_report": report_path,
        "verification": verification,
        "source_type": source_type,
        "conversion_tool": conversion_tool,
        "command": command,
        "complete": final_path.exists() and bool(verification.get("passed")) and report_path.exists(),
    }


def main() -> int:
    result = run_final_export_and_qc()
    print(f"Final WAV: {result['final_path']}")
    print(f"QC report: {result['qc_report']}")
    print("COMPLETE" if result["complete"] else "NOT COMPLETE")
    return 0 if result["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
