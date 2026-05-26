from __future__ import annotations

from pathlib import Path
from typing import Any


SECTION_TITLES = [
    "Session setup",
    "Import sample/vocal/stems",
    "Tempo/key confirmation",
    "Sample chop/loop placement",
    "Drum programming",
    "808 MIDI",
    "Synth width",
    "Vocal chain",
    "Automation",
    "Mix bus",
    "Master/export",
    "QC checklist",
]


def render_logic_arrangement_plan(
    arrangement_plan: dict[str, Any],
    midi_region_guide: dict[str, Any],
    automation_guide: dict[str, Any],
    logic_status: dict[str, Any],
) -> str:
    lines = [
        "# Logic Arrangement Manual Plan",
        "",
        f"- arrangement status: {arrangement_plan.get('status', 'ARRANGEMENT_PLAN_READY')}",
        f"- Logic autopilot status: {logic_status.get('status')}",
        f"- success allowed: {str(bool(logic_status.get('success_allowed'))).lower()}",
        f"- reason: {logic_status.get('reason')}",
        "- claim guard: no Logic automation success, plugin insertion, MIDI import, or bounce is claimed without verified artifacts.",
        "",
    ]
    body = {
        "Session setup": [
            "Create a new Logic session manually unless a verified .logicx artifact already exists.",
            f"Set tempo to {midi_region_guide.get('tempo_bpm') or 'tap tempo by ear'} BPM and time signature {midi_region_guide.get('time_signature', '4/4')}.",
        ],
        "Import sample/vocal/stems": [
            "Import local user-provided files only.",
            "If stems are unavailable, keep all processing stereo-only and do not claim stem-level control.",
        ],
        "Tempo/key confirmation": [
            f"Check key guide: {midi_region_guide.get('key') or 'unknown'} ({midi_region_guide.get('key_confidence', 'low')} confidence).",
            "Confirm BPM/key by ear before grid-locked chops or 808 notes.",
        ],
        "Sample chop/loop placement": [
            "Place Sample regions from midi_region_guide.json.",
            "Use direct sample chops only when ownership policy allows it.",
        ],
        "Drum programming": [
            "Program kick, clap/snare, hats, and fills from drum_midi_guide.json.",
            "Use controlled fills at section transitions; avoid generic trap unless requested.",
        ],
        "808 MIDI": [
            "Program 808 notes from bass_808_midi_guide.json after root confirmation.",
            "Keep sub mono; use glide/saturation as manual settings.",
        ],
        "Synth width": [
            "Widen upper synths only; keep bass and kick centered.",
            "Automate width at hook/drop sections from automation_guide.json.",
        ],
        "Vocal chain": [
            "Use vocal_pitch_guide.json as a recommendation only.",
            "Do not claim AutoTune, Melodyne, Flex Pitch, or plugin insertion unless verified.",
        ],
        "Automation": [
            f"Apply {len(automation_guide.get('events', []))} manual automation suggestions from automation_guide.json.",
            "Write volume, filter, reverb send, mutes, 808 pauses, width, and vocal delay throws by hand.",
        ],
        "Mix bus": [
            "Control low-end before loudness.",
            "Avoid cheap clipping and leave enough headroom for final verification.",
            "Use mix_prep_checklist.md before exporting a pre-master.",
        ],
        "Master/export": [
            "Bounce/export only after manual review.",
            "Do not claim bounce/export until the final WAV exists and verification passes.",
        ],
        "QC checklist": [
            "Verify .logicx/project artifact before any Logic success claim.",
            "Verify final WAV before bounce/export success.",
            "Confirm no exact protected melody, drum pattern, bassline, lyric, sample, or recording was copied.",
        ],
    }
    for title in SECTION_TITLES:
        lines.extend([f"## {title}", ""])
        lines.extend(f"- {item}" for item in body[title])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_logic_arrangement_plan(path: str | Path, markdown: str) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    return output
