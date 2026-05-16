from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from paths import PROJECT_ROOT


SUPPORTED_INPUT_EXTENSIONS = {".mp3", ".wav", ".aiff", ".aif", ".flac", ".m4a"}


@dataclass(frozen=True)
class IngestResult:
    original_path: str
    copied_path: str
    working_wav_path: str
    source_extension: str
    conversion_tool_used: str
    conversion_command: list[str]
    file_size: int
    created_timestamp: str
    duration_seconds: float | None
    verification_tool_used: str | None


class ConversionError(RuntimeError):
    pass


def sanitize_filename(filename: str) -> str:
    source = Path(filename)
    extension = source.suffix.lower()
    stem = source.stem.lower().strip()
    stem = stem.replace(" ", "_")
    stem = re.sub(r"[^a-z0-9._-]+", "", stem)
    stem = re.sub(r"_+", "_", stem).strip("._-")
    if not stem:
        stem = "input"
    return f"{stem}{extension}"


def unique_path(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    index = 1
    while True:
        numbered = directory / f"{stem}_{index:03d}{suffix}"
        if not numbered.exists():
            return numbered
        index += 1


def copy_original_input(input_path: Path, project_root: Path = PROJECT_ROOT) -> Path:
    resolved_input = input_path.expanduser()
    if not resolved_input.exists():
        raise FileNotFoundError(f"Input file does not exist: {resolved_input}")
    if not resolved_input.is_file():
        raise FileNotFoundError(f"Input path is not a file: {resolved_input}")
    if resolved_input.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_INPUT_EXTENSIONS))
        raise ValueError(f"Unsupported input extension '{resolved_input.suffix}'. Allowed: {allowed}")

    input_dir = project_root / "00_INPUT_SUNO"
    input_dir.mkdir(parents=True, exist_ok=True)
    destination = unique_path(input_dir, sanitize_filename(resolved_input.name))
    shutil.copy2(resolved_input, destination)
    return destination


def sample_rate_for_export_format(export_format: str) -> int:
    if export_format == "wav24_44k":
        return 44100
    return 48000


def find_conversion_tool() -> str | None:
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    if shutil.which("afconvert"):
        return "afconvert"
    return None


def backup_existing_working_wav(working_wav_path: Path) -> Path | None:
    if not working_wav_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = working_wav_path.with_name(f"working_input_backup_{timestamp}.wav")
    index = 1
    while backup.exists():
        backup = working_wav_path.with_name(f"working_input_backup_{timestamp}_{index:03d}.wav")
        index += 1
    working_wav_path.replace(backup)
    return backup


def build_conversion_command(tool: str, copied_path: Path, working_wav_path: Path, sample_rate: int) -> list[str]:
    if tool == "ffmpeg":
        return [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            str(copied_path),
            "-ar",
            str(sample_rate),
            "-ac",
            "2",
            "-c:a",
            "pcm_f32le",
            str(working_wav_path),
        ]
    if tool == "afconvert":
        return [
            "afconvert",
            "-f",
            "WAVE",
            "-d",
            f"LEF32@{sample_rate}",
            str(copied_path),
            str(working_wav_path),
        ]
    raise ConversionError(f"Unsupported conversion tool: {tool}")


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def parse_ffprobe_duration(output: str) -> float | None:
    try:
        return float(output.strip())
    except ValueError:
        return None


def parse_afinfo_duration(output: str) -> float | None:
    for line in output.splitlines():
        if "estimated duration:" not in line.lower():
            continue
        match = re.search(r"estimated duration:\s*([0-9.]+)", line, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def verify_working_wav(working_wav_path: Path) -> tuple[float | None, str | None]:
    if not working_wav_path.exists():
        raise ConversionError(f"Working WAV was not created: {working_wav_path}")
    if working_wav_path.stat().st_size <= 0:
        raise ConversionError(f"Working WAV is empty: {working_wav_path}")

    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        command = [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(working_wav_path),
        ]
        result = run_command(command)
        if result.returncode == 0:
            return parse_ffprobe_duration(result.stdout), "ffprobe"

    afinfo = shutil.which("afinfo")
    if afinfo:
        result = run_command([afinfo, str(working_wav_path)])
        if result.returncode == 0:
            return parse_afinfo_duration(result.stdout), "afinfo"

    raise ConversionError("Could not verify duration with ffprobe or afinfo.")


def write_metadata(result: IngestResult, project_root: Path = PROJECT_ROOT) -> Path:
    metadata_path = project_root / "01_ANALYSIS" / "input_metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(asdict(result), indent=2) + "\n", encoding="utf-8")
    return metadata_path


def write_conversion_error(message: str, project_root: Path = PROJECT_ROOT) -> Path:
    error_path = project_root / "01_ANALYSIS" / "conversion_error.md"
    error_path.parent.mkdir(parents=True, exist_ok=True)
    error_path.write_text(f"# Conversion Error\n\n{message}\n", encoding="utf-8")
    return error_path


def ingest_and_convert(input_path: str, export_format: str, project_root: Path = PROJECT_ROOT) -> IngestResult:
    original_path = Path(input_path).expanduser()
    copied_path = copy_original_input(original_path, project_root)

    processed_dir = project_root / "04_PROCESSED_AUDIO"
    processed_dir.mkdir(parents=True, exist_ok=True)
    working_wav_path = processed_dir / "working_input.wav"

    tool = find_conversion_tool()
    if tool is None:
        raise ConversionError("No conversion tool found. Install ffmpeg or use macOS afconvert.")

    backup_existing_working_wav(working_wav_path)
    sample_rate = sample_rate_for_export_format(export_format)
    command = build_conversion_command(tool, copied_path, working_wav_path, sample_rate)
    result = run_command(command)
    if result.returncode != 0:
        raise ConversionError(
            "Conversion command failed.\n\n"
            f"Command: {' '.join(command)}\n\n"
            f"stderr:\n{result.stderr.strip()}"
        )

    duration_seconds, verification_tool = verify_working_wav(working_wav_path)
    metadata = IngestResult(
        original_path=str(original_path),
        copied_path=str(copied_path),
        working_wav_path=str(working_wav_path),
        source_extension=original_path.suffix.lower(),
        conversion_tool_used=tool,
        conversion_command=command,
        file_size=working_wav_path.stat().st_size,
        created_timestamp=datetime.now(timezone.utc).isoformat(),
        duration_seconds=duration_seconds,
        verification_tool_used=verification_tool,
    )
    write_metadata(metadata, project_root)
    return metadata

