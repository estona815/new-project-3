from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]

REQUIRED_DIRECTORIES = (
    "00_INPUT_SUNO",
    "01_ANALYSIS",
    "02_EDIT_PLAN",
    "03_LOGIC_PROJECT",
    "04_PROCESSED_AUDIO",
    "05_FINAL_WAV",
    "06_QC_REPORT",
    "tools",
    "scripts",
    "src",
    "tests",
)

SUPPORTED_INPUT_EXTENSIONS = {".mp3", ".wav"}


@dataclass(frozen=True)
class SessionOptions:
    input_file: str | None = None
    final_length: str = "under 2 minutes"
    vocal_handling: str = "suppress vocal chops / no vocal texture"
    melody_forwardness: str = "main melody forward"
    drum_808_intensity: str = "strong but not covering melody"
    export_format: str = "WAV 24-bit 48kHz"
    save_logic_project: bool = True


def ensure_project_directories(project_dir: Path = PROJECT_DIR) -> list[Path]:
    created_or_existing: list[Path] = []
    for relative in REQUIRED_DIRECTORIES:
        directory = project_dir / relative
        directory.mkdir(parents=True, exist_ok=True)
        created_or_existing.append(directory)
    return created_or_existing


def sanitize_filename(filename: str) -> str:
    stem = Path(filename).stem.strip()
    suffix = Path(filename).suffix.lower()
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem)
    safe_stem = re.sub(r"_+", "_", safe_stem).strip("._-")
    if not safe_stem:
        safe_stem = "suno_input"
    return f"{safe_stem}{suffix}"


def unique_destination(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2
    while True:
        numbered = directory / f"{stem}_{counter}{suffix}"
        if not numbered.exists():
            return numbered
        counter += 1


def copy_input_file(input_path: Path, project_dir: Path = PROJECT_DIR) -> Path:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    if input_path.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
        raise ValueError("Input file must be an MP3 or WAV file.")

    input_dir = project_dir / "00_INPUT_SUNO"
    input_dir.mkdir(parents=True, exist_ok=True)
    destination = unique_destination(input_dir, sanitize_filename(input_path.name))
    shutil.copy2(input_path, destination)
    return destination


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_session_files(options: SessionOptions, project_dir: Path = PROJECT_DIR) -> None:
    ensure_project_directories(project_dir)

    session_payload = asdict(options)
    write_json(project_dir / "01_ANALYSIS" / "session_options.json", session_payload)

    analysis = {
        "status": "pending_audio_analysis",
        "note": "Detailed audio analysis will be implemented in the audio-analysis branch.",
        "required_metrics": [
            "duration",
            "sample_rate",
            "channels",
            "peak",
            "rms",
            "lufs_estimate",
            "clipping",
            "silence",
            "over_compressed_sections",
            "excessive_low_end",
            "vocal_like_texture_candidates",
            "melody_buried_candidates",
            "intro_hook_drop_outro_candidates",
        ],
    }
    write_json(project_dir / "01_ANALYSIS" / "analysis.json", analysis)

    (project_dir / "01_ANALYSIS" / "analysis_summary.md").write_text(
        "# Analysis Summary\n\n"
        "Status: pending detailed audio analysis.\n\n"
        "The scaffold records the required metrics but does not yet claim measured values.\n",
        encoding="utf-8",
    )

    (project_dir / "02_EDIT_PLAN" / "edit_plan.md").write_text(
        "# Edit Plan\n\n"
        "## Production Intent\n\n"
        "- Preserve the main melody and original emotional atmosphere.\n"
        "- Treat the source as an instrumental sketch.\n"
        "- Suppress vocal chops, fake vocal textures, or voice-like leads if they dominate.\n"
        "- Keep drums and 808 strong without covering the melody.\n"
        "- Leave headroom and target a final true peak around -1.0 dBTP or lower.\n\n"
        "## Logic Pro Manual Fallback\n\n"
        "Automation support has not been implemented in this scaffold branch. If Logic Pro automation "
        "is unavailable, import `04_PROCESSED_AUDIO/working_input.wav`, rebuild or reinforce the main "
        "melody, clean AI smear with EQ and arrangement edits, reduce vocal-like textures, balance drums "
        "below the lead, keep sub mostly mono below 100-120 Hz, then export the verified final WAV.\n",
        encoding="utf-8",
    )

    (project_dir / "06_QC_REPORT" / "qc_report.md").write_text(
        "# QC Report\n\n"
        "1. input filename: pending\n"
        "2. final export filename: pending\n"
        "3. total duration: pending\n"
        "4. processing summary: scaffold only; final audio not exported\n"
        "5. melody preservation: pending verification\n"
        "6. vocal chop / AI texture suppression: pending verification\n"
        "7. drum / 808 balance: pending verification\n"
        "8. clipping / loudness issues: pending verification\n"
        "9. remaining issues: final WAV does not exist yet\n"
        "10. next improvement options: implement analysis, processing/export, Logic automation fallback, and QC verification branches\n",
        encoding="utf-8",
    )


def verify_final_wav_not_claimed(project_dir: Path = PROJECT_DIR) -> bool:
    final_dir = project_dir / "05_FINAL_WAV"
    return not any(final_dir.glob("final_suno_logic_processed_24bit_*.wav"))

