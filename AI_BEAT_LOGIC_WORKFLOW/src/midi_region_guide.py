from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_midi_region_guide(
    arrangement_plan: dict[str, Any],
    *,
    drum_midi_guide: dict[str, Any] | None = None,
    bass_808_midi_guide: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sample_analysis = arrangement_plan.get("sample_chop_guide") or {}
    chord = arrangement_plan.get("chord_progression_guide") or {}
    sample_regions = _sample_regions(sample_analysis)
    drum_regions = _drum_regions(drum_midi_guide or {})
    bass_regions = _bass_regions(bass_808_midi_guide or {})
    return {
        "schema_version": "midi_region_guide.v1",
        "tempo_bpm": _tempo(arrangement_plan),
        "tempo_confidence": _tempo_confidence(arrangement_plan),
        "time_signature": "4/4",
        "key": chord.get("estimated_key"),
        "key_confidence": chord.get("key_confidence", "low"),
        "regions": sample_regions + drum_regions + bass_regions,
        "claim_guard": {
            "midi_imported_into_logic": False,
            "logic_project_modified": False,
            "import_requires_manual_or_verified_logic_execution": True,
        },
        "limitations": [
            "MIDI regions are production guide data only.",
            "Do not claim MIDI was imported into Logic unless a verified Logic artifact exists.",
        ],
    }


def write_midi_region_guide(path: str | Path, guide: dict[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(guide, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output


def _tempo(arrangement_plan: dict[str, Any]) -> int | None:
    context = arrangement_plan.get("analysis_context") or {}
    timing_context = context.get("sample_timing") or {}
    bpm_context = timing_context.get("bpm")
    if bpm_context:
        return int(round(float(bpm_context)))
    section = arrangement_plan.get("section_progression_guide") or {}
    source = section.get("source_summary") or {}
    sample = arrangement_plan.get("sample_analysis") or {}
    timing = sample.get("timing") or {}
    bpm = timing.get("bpm")
    return int(round(float(bpm))) if bpm else 148 if source else None


def _tempo_confidence(arrangement_plan: dict[str, Any]) -> str:
    context = arrangement_plan.get("analysis_context") or {}
    timing_context = context.get("sample_timing") or {}
    if timing_context.get("confidence"):
        return timing_context["confidence"]
    sample = arrangement_plan.get("sample_analysis") or {}
    timing = sample.get("timing") or {}
    return timing.get("confidence", "medium" if _tempo(arrangement_plan) else "low")


def _sample_regions(sample_chop_guide: dict[str, Any]) -> list[dict[str, Any]]:
    regions = []
    for index, loop in enumerate(sample_chop_guide.get("loop_candidates", [])[:3], start=1):
        regions.append(
            {
                "track": "Sample",
                "region_name": "main_loop" if index == 1 else f"loop_{index:02d}",
                "start_bar": 1 + ((index - 1) * 4),
                "length_bars": max(1, int(round(float(loop.get("estimated_bars", 4) or 4)))),
                "source_start_seconds": loop.get("start", 0.0),
                "source_end_seconds": loop.get("end", 0.0),
                "operation": "loop",
                "confidence": loop.get("confidence", "low"),
            }
        )
    for index, chop in enumerate(sample_chop_guide.get("chop_candidates", [])[:4], start=1):
        regions.append(
            {
                "track": "Sample",
                "region_name": chop.get("chop_id", f"chop_{index:02d}"),
                "start_bar": 1 + index,
                "length_bars": 1,
                "source_start_seconds": chop.get("start"),
                "source_end_seconds": chop.get("end"),
                "operation": "chop",
                "confidence": chop.get("confidence", "low"),
            }
        )
    return regions


def _drum_regions(drum_guide: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "track": "Drums",
            "region_name": pattern.get("region_name", "drum_pattern"),
            "start_bar": pattern.get("start_bar", 1),
            "length_bars": pattern.get("length_bars", 4),
            "operation": "program_midi",
            "manual_logic_required": True,
            "confidence": "medium",
        }
        for pattern in drum_guide.get("patterns", [])[:8]
    ]


def _bass_regions(bass_guide: dict[str, Any]) -> list[dict[str, Any]]:
    notes = bass_guide.get("notes", [])
    if not notes:
        return []
    return [
        {
            "track": "808",
            "region_name": "808_hook_pattern",
            "start_bar": min(int(note.get("bar", 1)) for note in notes),
            "length_bars": 8,
            "notes": notes,
            "manual_logic_required": True,
        }
    ]
