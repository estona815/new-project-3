#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.workflow import (  # noqa: E402
    SessionOptions,
    copy_input_file,
    ensure_project_directories,
    write_session_files,
)


def ask(prompt: str, default: str) -> str:
    answer = input(f"{prompt} [{default}]: ").strip()
    return answer or default


def ask_bool(prompt: str, default: bool) -> bool:
    default_text = "yes" if default else "no"
    answer = input(f"{prompt} [{default_text}]: ").strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes", "true", "1", "save"}


def collect_options(args: argparse.Namespace) -> SessionOptions:
    if args.non_interactive:
        return SessionOptions(input_file=args.input)

    input_file = args.input or input("Input Suno MP3/WAV path: ").strip() or None
    return SessionOptions(
        input_file=input_file,
        final_length=ask("Final length", "under 2 minutes"),
        vocal_handling=ask("Vocal removal or vocal texture suppression", "suppress vocal chops / no vocal texture"),
        melody_forwardness=ask("How forward should the main melody be?", "main melody forward"),
        drum_808_intensity=ask("Drum/808 intensity", "strong but not covering melody"),
        export_format=ask("Final export format", "WAV 24-bit 48kHz"),
        save_logic_project=ask_bool("Save a Logic Pro project file if possible?", True),
    )


def init_command(_args: argparse.Namespace) -> int:
    directories = ensure_project_directories(PROJECT_DIR)
    write_session_files(SessionOptions(), PROJECT_DIR)
    print(f"Initialized {len(directories)} workflow directories in {PROJECT_DIR}")
    print("Final WAV status: not exported; completion is intentionally not claimed.")
    return 0


def prepare_command(args: argparse.Namespace) -> int:
    ensure_project_directories(PROJECT_DIR)
    options = collect_options(args)

    copied_path: Path | None = None
    if options.input_file:
        copied_path = copy_input_file(Path(options.input_file).expanduser(), PROJECT_DIR)
        options = SessionOptions(
            input_file=str(copied_path),
            final_length=options.final_length,
            vocal_handling=options.vocal_handling,
            melody_forwardness=options.melody_forwardness,
            drum_808_intensity=options.drum_808_intensity,
            export_format=options.export_format,
            save_logic_project=options.save_logic_project,
        )

    write_session_files(options, PROJECT_DIR)
    print(f"Prepared workflow session in {PROJECT_DIR}")
    if copied_path:
        print(f"Copied input without overwriting original: {copied_path}")
    print("Final WAV status: not exported; completion is intentionally not claimed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare a Suno-to-Logic beat post-production workflow session."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create folders and starter artifacts.")
    init_parser.set_defaults(func=init_command)

    prepare_parser = subparsers.add_parser("prepare", help="Collect settings and copy an input MP3/WAV.")
    prepare_parser.add_argument("--input", help="Path to the source Suno MP3/WAV.")
    prepare_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Use defaults for unanswered production choices.",
    )
    prepare_parser.set_defaults(func=prepare_command)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

