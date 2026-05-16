from __future__ import annotations

import argparse

from audio_analysis import analyze_working_wav
from config import load_defaults
from ingest_convert import ConversionError, ingest_and_convert, write_conversion_error
from logging_utils import print_configuration_summary
from paths import ensure_folder_structure
from user_options import options_from_args, options_from_questionnaire


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scaffold CLI for the AI_BEAT_LOGIC_WORKFLOW Suno-to-Logic beat workflow."
    )
    parser.add_argument("--input", help="Path to the source Suno MP3/WAV file.")
    parser.add_argument("--length-mode", help="Final length mode, e.g. under_2min.")
    parser.add_argument("--vocal-mode", help="Vocal handling mode, e.g. suppress.")
    parser.add_argument("--melody-focus", help="Melody focus level, e.g. front.")
    parser.add_argument("--drum-808", help="Drum/808 intensity, e.g. strong_controlled.")
    parser.add_argument("--export-format", help="Export format, e.g. wav24_48k.")
    parser.add_argument("--save-logic-project", help="Whether to save a Logic project: true or false.")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Ask the seven setup questions interactively.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    ensure_folder_structure()
    defaults = load_defaults()

    if args.interactive:
        options = options_from_questionnaire(defaults)
    else:
        options = options_from_args(args, defaults)

    print_configuration_summary(options)
    if not options.input_path:
        print("Planned settings loaded. No input was provided, so conversion was not attempted.")
        return 0

    try:
        metadata = ingest_and_convert(options.input_path, options.export_format)
    except (ConversionError, FileNotFoundError, ValueError) as error:
        write_conversion_error(str(error))
        print(f"Conversion failed: {error}")
        print("No converted working WAV is being claimed.")
        return 2

    print("Input ingestion and working WAV conversion complete.")
    print(f"Copied input: {metadata.copied_path}")
    print(f"Working WAV: {metadata.working_wav_path}")
    print(f"Conversion tool: {metadata.conversion_tool_used}")
    analysis = analyze_working_wav()
    print(f"Analysis written: 01_ANALYSIS/analysis.json")
    print(f"Analysis summary written: 01_ANALYSIS/analysis_summary.md")
    print(f"Analyzed duration: {analysis['metadata']['duration_seconds']:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
