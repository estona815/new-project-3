from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.reference.reference_evaluation import final_reference_recommendation


def write_reference_match_report(
    *,
    output_dir: Path,
    manifest: dict[str, Any],
    current_analysis: dict[str, Any],
    reference_analyses: list[dict[str, Any]],
    comparison: dict[str, Any],
    plan: dict[str, Any],
    eval_metrics: dict[str, Any] | None,
    iteration_history: dict[str, Any],
) -> Path:
    path = output_dir / "eval_reports" / "reference_match_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = final_reference_recommendation(comparison, plan, eval_metrics)
    diffs = comparison.get("differences", {})
    summary = comparison.get("comparison_summary", {})
    tonal = current_analysis.get("tonal_profile", {})
    vocal = current_analysis.get("vocal_profile", {})
    melody = current_analysis.get("melody_profile", {})
    energy = current_analysis.get("energy_profile", {})
    stereo = current_analysis.get("stereo_profile", {})
    loud = current_analysis.get("loudness_profile", {})
    art = current_analysis.get("artifact_profile", {})
    lines = [
        "# Reference Matching / Genre Targeting Report",
        "",
        "## Summary",
        "",
        f"- Final recommendation: `{rec}`",
        f"- Target profile: `{manifest.get('target_profile')}`",
        f"- References used: `{len(reference_analyses)}`",
        f"- Draft created: `false`",
        "- Original mix untouched: `true`",
        "- Match strategy: `broad feature comparison with safety overrides`",
        "",
        "## Reference Safety Note",
        "",
        "References were used only for broad tonal, energy, loudness, and mix-balance comparison. The system did not copy melody, lyrics, arrangement, artist identity, or reference audio.",
        "",
        "## Current Mix vs Target Profile",
        "",
        f"- vocal_forwardness: `{vocal.get('vocal_forwardness')}`",
        f"- lead_melody_prominence: `{melody.get('lead_melody_prominence')}`",
        f"- drum_energy: `{energy.get('drum_energy')}`",
        f"- 808_energy: `{energy.get('808_energy')}`",
        f"- low_end_control: `{1.0 - diffs.get('low_end_too_muddy', 0.0)}`",
        f"- presence_clarity: `{tonal.get('presence_1k_4k')}`",
        f"- harshness: `{tonal.get('harshness_2k5_6k')}`",
        f"- sibilance: `{tonal.get('sibilance_5k_10k')}`",
        f"- stereo_width: `{stereo.get('stereo_width_score')}`",
        f"- mono_compatibility: `{1.0 - stereo.get('mono_compatibility_risk', 0.0)}`",
        f"- loudness: `{loud.get('integrated_lufs')}`",
        f"- AI artifact exposure: `{max(art.get('high_fizz_risk', 0.0), art.get('metallic_harshness_risk', 0.0), art.get('sibilance_splatter_risk', 0.0))}`",
        "",
        "## Current Mix vs References",
        "",
    ]
    if reference_analyses:
        for ref in reference_analyses:
            lines.extend(
                [
                    f"### {ref.get('reference_name')}",
                    f"- loudness difference: `{loud.get('integrated_lufs', 0.0) - ref.get('loudness_profile', {}).get('integrated_lufs', 0.0)}`",
                    f"- tonal difference: `{json.dumps(ref.get('tonal_profile', {}), sort_keys=True)}`",
                    f"- vocal balance difference: `{vocal.get('vocal_forwardness', 0.0) - ref.get('vocal_profile', {}).get('vocal_forwardness', 0.0)}`",
                    f"- low-end difference: `{energy.get('808_energy', 0.0) - ref.get('energy_profile', {}).get('808_energy', 0.0)}`",
                    f"- drum energy difference: `{energy.get('drum_energy', 0.0) - ref.get('energy_profile', {}).get('drum_energy', 0.0)}`",
                    f"- stereo difference: `{stereo.get('stereo_width_score', 0.0) - ref.get('stereo_profile', {}).get('stereo_width_score', 0.0)}`",
                    f"- artifact safety concerns: `{', '.join(ref.get('warnings', [])) or 'none'}`",
                    "",
                ]
            )
    else:
        lines.append("- target profile only; no reference audio analyzed")
    lines.extend(
        [
            "",
            "## Safe Adjustment Priorities",
            "",
        ]
    )
    lines.extend([f"- {item}" for item in comparison.get("safe_adjustment_priorities", [])] or ["- none"])
    lines.extend(["", "## Blocked Adjustments", ""])
    lines.extend([f"- {item.get('requested_adjustment')}: {item.get('blocked_reason')}" for item in plan.get("blocked_adjustments", [])] or ["- none"])
    lines.extend(
        [
            "",
            "## Draft Adjustment Plan",
            "",
            f"- target tracks: `{', '.join(sorted(set(item.get('target', '') for item in plan.get('adjustments', []))))}`",
            f"- plugin chain: `{json.dumps([item.get('adjustment_type') for item in plan.get('adjustments', [])])}`",
            "- semantic controls written: `none - draft metadata only`",
            "- semantic controls skipped: `unknown plugin parameters are not written`",
            "- routing changes: `none applied in Python workflow`",
            f"- warnings: `{', '.join(plan.get('warnings', [])) or 'none'}`",
            "",
            "## A/B Render Files",
            "",
            f"- current mix: `{(eval_metrics or {}).get('current_mix_path')}`",
            f"- reference-match draft: `{(eval_metrics or {}).get('reference_match_draft_path')}`",
            f"- loudness matched: `{(eval_metrics or {}).get('loudness_matched_path')}`",
            f"- difference: `{(eval_metrics or {}).get('difference_path')}`",
            "",
            "## Evaluation Metrics",
            "",
            f"- match improvement scores: `{json.dumps((eval_metrics or {}).get('match_improvement_scores', {}), sort_keys=True)}`",
            f"- damage scores: `{json.dumps((eval_metrics or {}).get('damage_scores', {}), sort_keys=True)}`",
            f"- evaluation passed: `{(eval_metrics or {}).get('evaluation_passed', False)}`",
            "",
            "## Iteration History",
            "",
        ]
    )
    for item in iteration_history.get("iterations", []) or [{"iteration": i, "decision": "not run"} for i in range(4)]:
        lines.append(f"- iteration {item.get('iteration')}: `{item.get('decision')}`")
    lines.extend(
        [
            "",
            "## Manual Listening Checklist",
            "",
            "- Does the mix move toward the target without copying the reference?",
            "- Is the vocal still emotionally clear?",
            "- Is the lead melody stronger without masking the vocal?",
            "- Do drums/808 feel stronger without muddying the low-end?",
            "- Did the high-end become fake, fizzy, or metallic?",
            "- Did the vocal become more AI-like?",
            "- Did the stereo image become unstable?",
            "- Is the result better at equal loudness?",
            "",
            "## Final Recommendation",
            "",
            f"`{rec}`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path

