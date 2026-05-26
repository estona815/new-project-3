from __future__ import annotations

from typing import Any


TODO_ORDER = [
    ("import_files", "import files"),
    ("confirm_tempo_key", "confirm tempo/key"),
    ("build_section_arrangement", "build section arrangement"),
    ("program_drums", "program drums"),
    ("program_808", "program 808"),
    ("place_sample_melody", "place sample/melody"),
    ("place_vocal", "place vocal"),
    ("apply_vocal_chain", "apply vocal chain"),
    ("apply_drum_808_mix_controls", "apply drum/808 mix controls"),
    ("apply_synth_width", "apply synth width"),
    ("automate_transitions", "automate transitions"),
    ("export_pre_master", "export pre-master"),
    ("run_final_master", "run final master"),
    ("verify_final_wav", "verify final WAV"),
    ("build_release_package", "build release package"),
]


def _task(task_id: str, title: str, instruction: str, *, status: str = "manual_required", notes: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": task_id,
        "title": title,
        "status": status,
        "instruction": instruction,
        "notes": list(notes or []),
    }


def build_production_todo(package: dict[str, Any]) -> list[dict[str, Any]]:
    capabilities = package.get("capabilities") or {}
    stereo_only = bool(capabilities.get("stereo_only"))
    stems_available = bool(capabilities.get("stems_available"))
    sample_allowed = bool((package.get("sample_chop_guide") or {}).get("direct_sample_use_allowed"))
    plugin_notes = package.get("plugin_requirements") or []
    master_target = package.get("master_target") or "streaming_safe"
    manual_logic = package.get("manual_logic_requirements") or []
    status_stem = "manual_stems_required" if stereo_only and not stems_available else "direct_balancing_allowed"
    sample_status = "blocked_without_ownership" if not sample_allowed else "manual_allowed"
    plugin_status = "manual_insert_required" if plugin_notes else "manual_required"
    tasks_by_id = {
        "import_files": _task("import_files", "import files", "Import local user-provided song/sample/vocal/stem files into the Logic session."),
        "confirm_tempo_key": _task("confirm_tempo_key", "confirm tempo/key", "Tap/confirm BPM and key by ear before locking MIDI, chops, and 808 roots."),
        "build_section_arrangement": _task("build_section_arrangement", "build section arrangement", "Create markers and regions from the section plan; keep the hook early when requested."),
        "program_drums": _task("program_drums", "program drums", "Program drums from the drum guide; avoid exact reference pattern copying.", status=status_stem),
        "program_808": _task("program_808", "program 808", "Program 808/bass from the bass guide, keep sub mono, and confirm roots by ear.", status=status_stem),
        "place_sample_melody": _task(
            "place_sample_melody",
            "place sample/melody",
            "Place sample chops only if ownership is confirmed; otherwise recreate the motif as a new melody/texture.",
            status=sample_status,
        ),
        "place_vocal": _task("place_vocal", "place vocal", "Place lead/adlib/backing vocals according to the vocal/topline guide; do not claim exact transcription."),
        "apply_vocal_chain": _task(
            "apply_vocal_chain",
            "apply vocal chain",
            "Insert tuning/de-ess/compression/saturation/reverb/delay manually where available.",
            status=plugin_status,
            notes=plugin_notes,
        ),
        "apply_drum_808_mix_controls": _task("apply_drum_808_mix_controls", "apply drum/808 mix controls", "Balance kick/808 by ear; stereo-only mode requires manual layers or stems for true replacement.", status=status_stem),
        "apply_synth_width": _task("apply_synth_width", "apply synth width", "Widen high-passed upper layers only; keep sub/kick/808 centered and check mono."),
        "automate_transitions": _task("automate_transitions", "automate transitions", "Write filter, volume, width, mute, send, pause, and delay-throw automation manually."),
        "export_pre_master": _task("export_pre_master", "export pre-master", "Bounce a clean pre-master only after manual arrangement and mix review."),
        "run_final_master": _task("run_final_master", "run final master", f"Run final master toward {master_target}; avoid clipping and keep verification headroom."),
        "verify_final_wav": _task("verify_final_wav", "verify final WAV", "Verify final WAV exists, size, duration, sample rate, format, peak/RMS, and clipping."),
        "build_release_package": _task("build_release_package", "build release package", "Build release metadata, rights/safety checklist, release QC, and status only after verified audio."),
    }
    if manual_logic:
        tasks_by_id["build_section_arrangement"]["notes"].extend(manual_logic[:4])
    return [tasks_by_id[task_id] for task_id, _title in TODO_ORDER]


def render_production_todo(package: dict[str, Any]) -> str:
    tasks = package.get("production_todo") or build_production_todo(package)
    lines = [
        "# Production Todo",
        "",
        f"- package status: {package.get('status', 'PRODUCTION_PACKAGE_READY')}",
        f"- complete: {str(bool(package.get('complete'))).lower()}",
        "",
    ]
    for index, task in enumerate(tasks, start=1):
        lines.extend(
            [
                f"{index}. {task['title']}",
                f"   - status: {task['status']}",
                f"   - instruction: {task['instruction']}",
            ]
        )
        for note in task.get("notes", []):
            lines.append(f"   - note: {note}")
    lines.extend(
        [
            "",
            "## Safety",
            "- This todo is manual production guidance only.",
            "- No Logic automation, plugin insertion, MIDI import, bounce, or final WAV success is claimed without verified artifacts.",
            "- Stereo-only work cannot claim stem-level remixing, guaranteed vocal removal, true kick/bass replacement, true drum rewrite, or true stem separation.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"
