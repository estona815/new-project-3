from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SUPPORTED_INPUT_EXTENSIONS = {".mp3", ".wav", ".aiff", ".aif", ".flac", ".m4a"}


@dataclass(frozen=True)
class UserOptions:
    input_path: str | None
    length_mode: str
    vocal_mode: str
    melody_focus: str
    drum_808: str
    export_format: str
    save_logic_project: bool
    input_exists: bool = False
    validation_warnings: tuple[str, ...] = field(default_factory=tuple)


def parse_bool(value: str | bool | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "save"}:
        return True
    if normalized in {"0", "false", "no", "n", "skip"}:
        return False
    raise ValueError(f"Expected a boolean value, got: {value}")


def ask_text(prompt: str, default: Any) -> str:
    answer = input(f"{prompt} [{default}]: ").strip()
    return answer or str(default)


def ask_bool(prompt: str, default: bool) -> bool:
    default_text = "true" if default else "false"
    answer = input(f"{prompt} [{default_text}]: ").strip()
    return parse_bool(answer or default_text, default)


def validate_input_path(input_path: str | None) -> tuple[bool, tuple[str, ...]]:
    if not input_path:
        return False, ("No input file path provided. Audio ingest will be handled in a later branch.",)

    path = Path(input_path).expanduser()
    warnings: list[str] = []
    if path.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
        warnings.append("Input path should point to an MP3, WAV, AIFF, FLAC, or M4A file.")
    if not path.exists():
        warnings.append("Input path does not exist; conversion will fail until a real file is provided.")

    return path.exists(), tuple(warnings)


def options_from_args(args: Any, defaults: dict[str, Any]) -> UserOptions:
    save_logic_project = parse_bool(args.save_logic_project, bool(defaults["save_logic_project"]))
    input_exists, warnings = validate_input_path(args.input)
    return UserOptions(
        input_path=args.input,
        length_mode=args.length_mode or defaults["length_mode"],
        vocal_mode=args.vocal_mode or defaults["vocal_mode"],
        melody_focus=args.melody_focus or defaults["melody_focus"],
        drum_808=args.drum_808 or defaults["drum_808"],
        export_format=args.export_format or defaults["export_format"],
        save_logic_project=save_logic_project,
        input_exists=input_exists,
        validation_warnings=warnings,
    )


def options_from_questionnaire(defaults: dict[str, Any]) -> UserOptions:
    input_path = input("Input file path: ").strip() or None
    length_mode = ask_text("Final length mode", defaults["length_mode"])
    vocal_mode = ask_text("Vocal removal/suppression preference", defaults["vocal_mode"])
    melody_focus = ask_text("Melody focus level", defaults["melody_focus"])
    drum_808 = ask_text("Drum/808 intensity", defaults["drum_808"])
    export_format = ask_text("Export format", defaults["export_format"])
    save_logic_project = ask_bool("Save Logic project?", bool(defaults["save_logic_project"]))
    input_exists, warnings = validate_input_path(input_path)

    return UserOptions(
        input_path=input_path,
        length_mode=length_mode,
        vocal_mode=vocal_mode,
        melody_focus=melody_focus,
        drum_808=drum_808,
        export_format=export_format,
        save_logic_project=save_logic_project,
        input_exists=input_exists,
        validation_warnings=warnings,
    )
