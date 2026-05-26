from __future__ import annotations

from typing import Any

from arrangement_templates import normalize_length_mode


def design_energy_curve(length_mode: str = "under_2min") -> dict[str, Any]:
    """Return rescue-first section energy targets.

    Energy is an intentional arrangement score from 1-5, not a measured loudness
    target. The curve is designed to avoid long AI intros and static generated
    continuation.
    """
    length = normalize_length_mode(length_mode)
    curves: dict[str, list[dict[str, float | int | str]]] = {
        "reels_15sec": [
            {"name": "main_hook", "start_time": 0.0, "duration": 8.0, "energy": 5, "purpose": "instant hook identity"},
            {"name": "micro_variation", "start_time": 8.0, "duration": 5.0, "energy": 4, "purpose": "controlled switch-up"},
            {"name": "loopable_tag", "start_time": 13.0, "duration": 2.0, "energy": 3, "purpose": "clean cut or loop point"},
        ],
        "short_30sec": [
            {"name": "intro_hook_hint", "start_time": 0.0, "duration": 4.0, "energy": 3, "purpose": "lead pickup"},
            {"name": "main_hook", "start_time": 4.0, "duration": 12.0, "energy": 5, "purpose": "full identity"},
            {"name": "variation_answer", "start_time": 16.0, "duration": 8.0, "energy": 4, "purpose": "call-response development"},
            {"name": "final_hook_tag", "start_time": 24.0, "duration": 6.0, "energy": 5, "purpose": "payoff and clean ending"},
        ],
        "under_2min": [
            {"name": "intro_hook_hint", "start_time": 0.0, "duration": 4.0, "energy": 3, "purpose": "hook hint / lead pickup"},
            {"name": "main_hook", "start_time": 4.0, "duration": 16.0, "energy": 5, "purpose": "main hook"},
            {"name": "verse_groove", "start_time": 20.0, "duration": 16.0, "energy": 3, "purpose": "verse groove / reduced lead"},
            {"name": "hook_return", "start_time": 36.0, "duration": 16.0, "energy": 5, "purpose": "hook return"},
            {"name": "breakdown_filtered_lead", "start_time": 52.0, "duration": 16.0, "energy": 2, "purpose": "breakdown / filtered lead"},
            {"name": "final_hook", "start_time": 68.0, "duration": 20.0, "energy": 5, "purpose": "final hook lift"},
            {"name": "clean_outro_or_loop", "start_time": 88.0, "duration": 12.0, "energy": 2, "purpose": "clean outro or loopable ending"},
        ],
        "full_song": [
            {"name": "intro_hook_hint", "start_time": 0.0, "duration": 8.0, "energy": 3, "purpose": "short identity setup"},
            {"name": "main_hook", "start_time": 8.0, "duration": 20.0, "energy": 5, "purpose": "early hook statement"},
            {"name": "verse", "start_time": 28.0, "duration": 28.0, "energy": 3, "purpose": "controlled body"},
            {"name": "pre_hook", "start_time": 56.0, "duration": 12.0, "energy": 4, "purpose": "lift"},
            {"name": "hook_return", "start_time": 68.0, "duration": 24.0, "energy": 5, "purpose": "hook return"},
            {"name": "bridge", "start_time": 92.0, "duration": 20.0, "energy": 2, "purpose": "contrast"},
            {"name": "final_hook", "start_time": 112.0, "duration": 28.0, "energy": 5, "purpose": "final payoff"},
            {"name": "clean_outro", "start_time": 140.0, "duration": 12.0, "energy": 2, "purpose": "controlled finish"},
        ],
    }
    curve = curves[length]
    return {
        "schema_version": "energy_curve_design.v1",
        "length_mode": length,
        "hook_within_first_15_seconds": any("hook" in str(section["name"]) and float(section["start_time"]) < 15.0 for section in curve),
        "target_duration_seconds": round(max(float(section["start_time"]) + float(section["duration"]) for section in curve), 3),
        "curve": curve,
        "rules": [
            "Do not keep a 3-minute weak AI structure by default.",
            "Hook identity must arrive early.",
            "Use contrast and variation every 4-8 bars.",
            "Keep breakdowns intentional and short.",
        ],
    }
