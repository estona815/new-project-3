from __future__ import annotations

from user_options import UserOptions


def print_configuration_summary(options: UserOptions) -> None:
    print("\nAI_BEAT_LOGIC_WORKFLOW configuration summary")
    print("------------------------------------------------")
    print(f"Input file: {options.input_path or 'not provided'}")
    print(f"Input exists: {'yes' if options.input_exists else 'no'}")
    print(f"Length mode: {options.length_mode}")
    print(f"Vocal mode: {options.vocal_mode}")
    print(f"Melody focus: {options.melody_focus}")
    print(f"Drum/808: {options.drum_808}")
    print(f"Export format: {options.export_format}")
    print(f"Save Logic project: {'true' if options.save_logic_project else 'false'}")
    print(f"Mode: {options.mode}")
    print(f"Vocal style: {options.vocal_style}")
    print(f"Mix intensity: {options.mix_intensity}")
    print(f"Master loudness: {options.master_loudness}")
    print(f"Autotune: {options.autotune}")
    print(f"De-ess: {options.deess}")
    print(f"Reverb space: {options.reverb_space}")
    print(f"Delay style: {options.delay_style}")
    print("Audio processing: mode-aware ingest, planning, fallback processing, export, and QC")
    if options.validation_warnings:
        print("\nValidation warnings")
        for warning in options.validation_warnings:
            print(f"- {warning}")
    print("------------------------------------------------\n")
