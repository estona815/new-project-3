from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_automation_guide(arrangement_plan: dict[str, Any], midi_region_guide: dict[str, Any] | None = None) -> dict[str, Any]:
    sections = (arrangement_plan.get("section_progression_guide") or {}).get("sections", [])
    events = []
    for section in sections:
        start = section.get("start", 0.0)
        name = section.get("name", "section")
        if name in {"intro", "motif_seed"}:
            events.append(_event("filter_movement", start, "Sample/Synth", "open low-pass toward first hook", "medium"))
        if "hook" in name or "drop" in name:
            events.append(_event("volume_automation", start, "Drums/808", "small lift into hook, avoid clipping", "medium"))
            events.append(_event("stereo_width", start, "Upper Synths", "widen upper layers only; keep sub mono", "medium"))
        if name in {"contrast", "bridge", "pre"}:
            events.append(_event("drum_mute", start, "Drums", "mute hats or kick for contrast", "medium"))
            events.append(_event("808_pause", start, "808", "short pause before re-entry", "medium"))
        if name in {"verse", "final_hook"}:
            events.append(_event("vocal_delay_throw", start, "Vocal", "manual delay throw at phrase ends", "low"))
    if not events:
        events = [
            _event("filter_movement", 0.0, "Sample/Synth", "manual intro-to-hook filter move", "low"),
            _event("reverb_send", 8.0, "Vocal/Synth", "increase send at transition tails", "low"),
        ]
    return {
        "schema_version": "automation_guide.v1",
        "events": events,
        "categories": [
            "volume automation suggestions",
            "filter movement",
            "reverb send changes",
            "drum mutes",
            "808 pauses",
            "stereo width automation",
            "vocal delay throw points",
        ],
        "claim_guard": {
            "automation_written_to_logic": False,
            "plugins_inserted": False,
            "logic_project_modified": False,
            "automation_success_verified": False,
        },
        "limitations": [
            "Automation guide is manual instruction unless Logic automation is executed and verified.",
            "Plugin insertion is not claimed by automation suggestions.",
        ],
    }


def write_automation_guide(path: str | Path, guide: dict[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(guide, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output


def _event(kind: str, start_seconds: float, target: str, instruction: str, confidence: str) -> dict[str, Any]:
    return {
        "type": kind,
        "start_seconds": start_seconds,
        "target": target,
        "instruction": instruction,
        "manual_logic_required": True,
        "confidence": confidence,
    }
