from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_analysis_json(analysis: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")


def fmt_region(region: dict[str, Any] | None) -> str:
    if not region:
        return "Not detected"
    return f"{region.get('start', 0):.2f}s - {region.get('end', 0):.2f}s"


def build_summary(analysis: dict[str, Any]) -> str:
    arrangement = analysis.get("arrangement_candidates", {})
    hook = arrangement.get("first_hook_or_main_motif_entrance")
    intro = analysis.get("silence_detection", {}).get("intro_silence") or arrangement.get("intro")
    vocal_candidates = analysis.get("vocal_like_texture_candidates", [])
    melody_buried = analysis.get("melody_buried_candidates", [])
    low_end = analysis.get("low_end_excess_candidates", [])
    glitches = arrangement.get("ai_random_transition_or_glitch_candidates", [])
    over = analysis.get("over_compression_detection", {})

    duration = analysis.get("metadata", {}).get("duration_seconds", 0.0)
    suggested_length = "under 2 minutes" if duration > 120 else "keep original unless arrangement cleanup suggests a tighter reel edit"
    diagnosis_bits = []
    if over.get("possible_over_compression"):
        diagnosis_bits.append("possible over-compression")
    if low_end:
        diagnosis_bits.append("low-end dominance candidates")
    if vocal_candidates:
        diagnosis_bits.append("heuristic vocal-like texture candidates")
    if glitches:
        diagnosis_bits.append("abrupt transition/glitch candidates")
    if not diagnosis_bits:
        diagnosis_bits.append("no severe heuristic warnings in this pass")

    lines = [
        "# Analysis Summary",
        "",
        "## Overall Diagnosis",
        "",
        "This is a heuristic analysis for production planning, not a final musical judgment or ML stem/vocal detection result.",
        f"Overall flags: {', '.join(diagnosis_bits)}.",
        "",
        "## Best Hook Candidate",
        "",
        f"- {fmt_region(hook)}",
        "- Reason: strongest motif/hook candidate is estimated from loudness, energy, onset density, and novelty heuristics.",
        "",
        "## Suggested Final Length",
        "",
        f"- {suggested_length}",
        "",
        "## Suggested Intro Cut",
        "",
        f"- Consider cutting or tightening around: {fmt_region(intro)}",
        "",
        "## Melody-Forward Recommendations",
        "",
    ]
    if melody_buried:
        lines.append("- Melody-buried candidates were detected. Reduce drum/808 pressure or automate melody lift in these sections:")
        lines.extend(f"  - {fmt_region(item)}: {item.get('reason')}" for item in melody_buried[:6])
    else:
        lines.append("- No strong melody-buried candidates were detected by the current heuristic.")

    lines.extend(["", "## Drum/808 Balance Warnings", ""])
    if low_end:
        lines.append("- Low-end excess candidates were detected. Keep 808 strong but carve it around the main melody:")
        lines.extend(f"  - {fmt_region(item)}: {item.get('reason')}" for item in low_end[:6])
    else:
        lines.append("- No strong low-end dominance warning was detected by the current heuristic.")

    lines.extend(["", "## Vocal Chop Suppression Notes", ""])
    if vocal_candidates:
        lines.append("- Heuristic vocal-like texture candidates. Do not treat these as confirmed vocals; audition and suppress if they feel like fake voice/chops:")
        lines.extend(f"  - {fmt_region(item)}: {item.get('confidence')} confidence, {item.get('reason')}" for item in vocal_candidates[:6])
    else:
        lines.append("- No strong heuristic vocal-like texture candidates were detected.")

    lines.extend(["", "## AI-Randomness Cleanup Notes", ""])
    if glitches:
        lines.append("- Abrupt spectral/loudness novelty candidates may indicate random AI transitions or glitchy jumps:")
        lines.extend(f"  - {fmt_region(item)}: {item.get('reason')}" for item in glitches[:6])
    else:
        lines.append("- No major abrupt transition candidates were detected.")

    lines.extend(["", "## Human Arrangement Cleanup", ""])
    lines.append("- Audition hook, drop, and repeated loop candidates manually before committing to edits.")
    lines.append("- Preserve the strongest melody section and reduce anything that makes the beat feel like a generic AI loop.")
    return "\n".join(lines) + "\n"


def write_analysis_summary(analysis: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_summary(analysis), encoding="utf-8")

