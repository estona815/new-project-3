from __future__ import annotations

from typing import Any


def generate_sample_chop_guide(sample_analysis: dict[str, Any] | None, ownership_policy: dict[str, Any] | None = None) -> dict[str, Any]:
    safety = (sample_analysis or {}).get("sample_usage_safety") or {}
    policy = ownership_policy or safety
    direct_allowed = bool(policy.get("direct_sample_use_allowed") or policy.get("exact_copy_allowed"))
    loops = ((sample_analysis or {}).get("loop_detection") or {}).get("loopable_regions", [])
    motifs = ((sample_analysis or {}).get("motif_hook_detection") or {}).get("hook_motif_candidates", [])
    chops = []
    for index, motif in enumerate(motifs[:8], start=1):
        chops.append(
            {
                "chop_id": f"chop_{index:02d}",
                "start": motif.get("start"),
                "end": motif.get("end"),
                "use": "motif accent or hook seed",
                "confidence": motif.get("confidence", "low"),
            }
        )
    return {
        "schema_version": "sample_chop_guide.v1",
        "ownership_status": policy.get("ownership_status") or policy.get("reason", "unknown"),
        "direct_sample_use_allowed": direct_allowed,
        "direct_sample_layer_blocked": not direct_allowed,
        "chop_candidates": chops,
        "loop_candidates": loops[:6],
        "motif_candidates": motifs[:6],
        "usage_rules": [
            "Direct sample use is allowed only when owned/licensed/cleared.",
            "If ownership is unknown, recreate the feel with new MIDI/synthesis instead of layering the sample.",
            "No web audio download or protected recording extraction.",
        ],
        "limitations": ["Chop timing is heuristic and should be trimmed by ear at zero crossings."],
    }
