from __future__ import annotations

from pathlib import Path
from typing import Any


def write_recovery_review_form(
    *,
    project_name: str,
    drafts: list[dict[str, Any]],
    ab_status: dict[str, Any],
    output_dir: Path,
) -> Path:
    ab_by_draft = {item.get("draft_track_name"): item for item in ab_status.get("tracks", [])}
    lines = [
        "# Recovery Draft Review Form",
        "",
        "## Instructions",
        "",
        "Listen to the original and recovery draft at matched loudness before accepting.",
        "",
        "Do not accept a draft only because it is quieter, darker, or less bright.",
        "",
        "Reject if the draft sounds:",
        "",
        "- dull",
        "- thin",
        "- smeared",
        "- phasey",
        "- lispy",
        "- over-denoised",
        "- less emotional",
        "- more metallic",
        "- more AI-like",
        "- unstable in stereo",
        "- worse on consonants",
        "- worse on reverb tails",
        "",
        "## Draft Review Table",
        "",
    ]
    if not drafts:
        lines.append("No recovery drafts are available for review.")
        lines.append("")
    for draft in drafts:
        draft_name = draft.get("draft_track_name", "")
        ab = ab_by_draft.get(draft_name, {})
        lines.extend(
            [
                f"### Track: {draft.get('original_track_name', draft.get('track_name', ''))}",
                "",
                f"- Original: `{draft.get('original_track_name', '')}`",
                f"- Recovery Draft: `{draft_name}`",
                f"- Loudness-Matched A/B: `{ab.get('ab_complete', False)}`",
                f"- Difference: `{ 'difference_render_missing' not in ab.get('warnings', []) }`",
                f"- Evaluation status: `{'passed' if ab.get('evaluation_passed') else 'not_passed_or_missing'}`",
                f"- Warnings: `{', '.join(ab.get('warnings', [])) or 'none'}`",
                "",
                "Decision:",
                "[ ] accepted",
                "[ ] accepted_light",
                "[ ] rejected",
                "[ ] needs_revision",
                "[ ] stem_required",
                "[ ] manual_cleanup_required",
                "",
                "Notes:",
                "",
                "Warnings acknowledged:",
                "[ ] yes",
                "[ ] no",
                "",
            ]
        )
    lines.extend(
        [
            "## Global Review Decision",
            "",
            "[ ] Accept selected recovery drafts for next-stage placement analysis.",
            "[ ] Do not proceed; revise recovery drafts.",
            "[ ] Do not proceed; provide better stems.",
            "[ ] Do not proceed; manual cleanup required.",
            "",
            f"Project: `{project_name}`",
            "",
        ]
    )
    path = output_dir / "review" / "recovery_review_form.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path

