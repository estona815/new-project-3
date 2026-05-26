from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_artifact_detector import detect_low_end_excess_proxy, detect_over_compressed_sections, detect_repeated_ai_loops
from audio_analysis import mono_mix, read_wav_float
from hook_detector import detect_hook_candidates, reels_hook_region
from melody_focus_detection import detect_low_end_excess_and_melody_burial
from paths import PROJECT_ROOT
from section_detector import detect_sections, frame_energy_features
from transition_detector import dead_outro_candidates, detect_abrupt_transitions, weak_intro_candidates
from vocal_texture_detection import detect_vocal_like_textures


VALID_MODES = {"full_song_stereo", "stems", "instrumental", "vocal_song"}


def _mode(value: str | None) -> str:
    if value in VALID_MODES:
        return str(value)
    if value == "instrumental_beat":
        return "instrumental"
    return "full_song_stereo"


def analyze_song_structure(path: str | Path, *, mode: str = "full_song_stereo") -> dict[str, Any]:
    song_path = Path(path).expanduser()
    analysis_mode = _mode(mode)
    try:
        metadata, channels = read_wav_float(song_path)
    except Exception as error:  # noqa: BLE001 - analysis must fail closed.
        return {
            "schema_version": "song_structure_analysis.v1",
            "input": {"path": str(song_path), "mode": analysis_mode},
            "duration_seconds": 0,
            "sections": [],
            "hook_candidates": [],
            "weak_intro_candidates": [],
            "dead_outro_candidates": [],
            "repeated_ai_loop_candidates": [],
            "abrupt_transition_candidates": [],
            "melody_buried_candidates": [],
            "vocal_like_texture_candidates": [],
            "over_compressed_sections": [],
            "low_end_excess_candidates": [],
            "reels_hook_region": None,
            "limitations": [f"Audio could not be read: {error}", "Section detection is heuristic."],
        }
    mono = mono_mix(channels)
    sample_rate = int(metadata["sample_rate"])
    duration = float(metadata["duration_seconds"])
    features = frame_energy_features(mono, sample_rate)
    sections = detect_sections(features, duration)
    hooks = detect_hook_candidates(features, duration)
    low_end, melody_buried = detect_low_end_excess_and_melody_burial(mono, sample_rate)
    low_end_proxy = detect_low_end_excess_proxy(mono, sample_rate)
    limitations = [
        "Section detection is heuristic.",
        "Section labels are not confirmed unless user markers, stems, or manual listening confirm them.",
    ]
    if analysis_mode != "stems":
        limitations.append("Only stereo/full-mix analysis is available; no full arrangement rewrite is claimed.")
    if duration < 8.0:
        limitations.append("Very short audio limits section, hook, and transition confidence.")

    return {
        "schema_version": "song_structure_analysis.v1",
        "input": {"path": str(song_path), "mode": analysis_mode},
        "duration_seconds": duration,
        "sections": sections,
        "hook_candidates": hooks,
        "weak_intro_candidates": weak_intro_candidates(features),
        "dead_outro_candidates": dead_outro_candidates(features, duration),
        "repeated_ai_loop_candidates": detect_repeated_ai_loops(features),
        "abrupt_transition_candidates": detect_abrupt_transitions(features),
        "melody_buried_candidates": melody_buried,
        "vocal_like_texture_candidates": detect_vocal_like_textures(channels, sample_rate),
        "over_compressed_sections": detect_over_compressed_sections(features),
        "low_end_excess_candidates": low_end or low_end_proxy,
        "reels_hook_region": reels_hook_region(hooks),
        "feature_summary": {
            "window_count": len(features),
            "method": "stdlib energy/novelty/onset contour analysis",
        },
        "limitations": limitations,
    }


def render_song_structure_summary(analysis: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Song Structure Analysis Summary",
            "",
            f"- path: {analysis['input']['path']}",
            f"- mode: {analysis['input']['mode']}",
            f"- duration: {analysis['duration_seconds']:.3f}s",
            f"- sections: {len(analysis['sections'])}",
            f"- hook candidates: {len(analysis['hook_candidates'])}",
            f"- weak intro candidates: {len(analysis['weak_intro_candidates'])}",
            f"- dead outro candidates: {len(analysis['dead_outro_candidates'])}",
            f"- repeated AI loop candidates: {len(analysis['repeated_ai_loop_candidates'])}",
            f"- abrupt transition candidates: {len(analysis['abrupt_transition_candidates'])}",
            f"- melody buried candidates: {len(analysis['melody_buried_candidates'])}",
            f"- vocal-like texture candidates: {len(analysis['vocal_like_texture_candidates'])}",
            f"- reels hook region: {analysis.get('reels_hook_region') or 'not detected'}",
            "",
            "## Limitations",
            *[f"- {item}" for item in analysis.get("limitations", [])],
            "",
        ]
    )


def write_song_structure_analysis(
    path: str | Path,
    *,
    project_root: Path = PROJECT_ROOT,
    mode: str = "full_song_stereo",
) -> dict[str, Path]:
    analysis = analyze_song_structure(path, mode=mode)
    analysis_dir = project_root / "01_ANALYSIS"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    json_path = analysis_dir / "song_structure_analysis.json"
    summary_path = analysis_dir / "song_structure_summary.md"
    json_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary_path.write_text(render_song_structure_summary(analysis), encoding="utf-8")
    return {"json": json_path, "summary": summary_path}
