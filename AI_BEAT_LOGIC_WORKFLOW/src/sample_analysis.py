from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from audio_analysis import clipping_count, flatten_channels, mono_mix, read_wav_float
from loudness_estimation import linear_to_db, rms_db
from onset_analysis import analyze_transients, frame_features
from paths import PROJECT_ROOT
from sample_loop_detector import detect_loop_candidates
from sample_motif_detector import detect_motif_candidates
from section_detection import detect_silence_regions
from tempo_key_estimation import estimate_bpm, estimate_key


SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".aiff", ".aif", ".flac", ".m4a"}
SAMPLE_ANALYSIS_JSON = PROJECT_ROOT / "01_ANALYSIS" / "sample_analysis.json"
SAMPLE_ANALYSIS_SUMMARY = PROJECT_ROOT / "01_ANALYSIS" / "sample_analysis_summary.md"


def _load_audio_for_analysis(path: str | Path, working_wav_path: str | Path | None = None) -> tuple[Path, dict[str, Any], list[list[float]], list[str]]:
    source_path = Path(path).expanduser()
    limitations: list[str] = []
    if source_path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        raise ValueError(f"Unsupported sample extension: {source_path.suffix}")
    analysis_path = source_path
    if source_path.suffix.lower() != ".wav":
        if not working_wav_path:
            raise ValueError("Non-WAV sample analysis requires a converted working WAV path.")
        analysis_path = Path(working_wav_path).expanduser()
        limitations.append("Input was non-WAV; analysis used the provided converted working WAV.")
    metadata, channels = read_wav_float(analysis_path)
    return source_path, metadata, channels, limitations


def _format_name(path: Path) -> str:
    return path.suffix.lower().lstrip(".") or "unknown"


def _level_analysis(channels: list[list[float]], mono: list[float], sample_rate: int) -> dict[str, Any]:
    all_samples = flatten_channels(channels)
    peak = max((abs(sample) for sample in all_samples), default=0.0)
    return {
        "peak_dbfs": round(linear_to_db(peak), 3),
        "rms_dbfs": round(rms_db(all_samples), 3),
        "clipping_count": clipping_count(all_samples),
        "silence_regions": detect_silence_regions(mono, sample_rate, threshold=0.001, min_seconds=0.15),
    }


def _sample_usage_safety(ownership_status: str | None) -> dict[str, Any]:
    normalized = (ownership_status or "unknown").strip().lower()
    direct_allowed = normalized in {"owned", "licensed", "cleared", "owned_or_licensed", "user_confirmed_owned"}
    return {
        "ownership_status": normalized,
        "direct_sample_use_allowed": direct_allowed,
        "direct_sample_layer_blocked": not direct_allowed,
        "no_web_audio_download": True,
        "policy_note": (
            "Direct sample/layer use is allowed only inside the confirmed local owned/licensed source."
            if direct_allowed
            else "Ownership is unknown or unconfirmed; direct sample/layer use is blocked and traits must be recreated from scratch."
        ),
        "not_claimed": [
            "exact protected song copying",
            "exact melody copying",
            "exact drum pattern copying",
            "web audio download",
        ],
    }


def analyze_sample_audio(
    path: str | Path,
    *,
    working_wav_path: str | Path | None = None,
    ownership_status: str | None = None,
) -> dict[str, Any]:
    source_path, metadata, channels, limitations = _load_audio_for_analysis(path, working_wav_path)
    sample_rate = int(metadata["sample_rate"])
    duration = float(metadata["duration_seconds"])
    mono = mono_mix(channels)
    frames = frame_features(mono, sample_rate)
    transients = analyze_transients(mono, sample_rate)
    timing = estimate_bpm([float(item) for item in transients["onset_times"]], duration)
    tonal = estimate_key(mono, sample_rate, duration)
    loops = detect_loop_candidates(mono, sample_rate, duration, timing)
    motifs = detect_motif_candidates(frames, duration)

    if duration < 2.0:
        limitations.append("Sample is under 2 seconds; BPM and key must remain low confidence.")
    limitations.extend(
        [
            "All BPM, key, loop, onset, and motif results are heuristic unless verified by listening.",
            "No exact sample, melody, drum pattern, bassline, lyric, or sound recording copying is performed.",
        ]
    )
    return {
        "schema_version": "sample_analysis.v1",
        "metadata": {
            "path": str(source_path),
            "analysis_path": str(Path(working_wav_path).expanduser()) if working_wav_path else str(source_path),
            "duration_seconds": duration,
            "sample_rate": sample_rate,
            "channels": int(metadata["channels"]),
            "format": _format_name(source_path),
            "file_size": source_path.stat().st_size,
            "bit_depth": metadata.get("bit_depth"),
        },
        "level": _level_analysis(channels, mono, sample_rate),
        "timing": timing,
        "tonal": tonal,
        "loop_detection": {
            "loopable_regions": loops,
            "method": "Bar-aligned stdlib heuristic from BPM candidates plus waveform boundary click estimate.",
        },
        "motif_hook_detection": motifs,
        "transient_onset": transients,
        "sample_usage_safety": _sample_usage_safety(ownership_status),
        "dependency_behavior": {
            "active_level": "stdlib",
            "stdlib_support": ["duration", "peak", "RMS", "clipping", "silence", "rough onsets", "rough BPM candidates", "rough loops"],
            "optional_dependency_note": "librosa/essentia may improve rhythm, tonal, and spectral descriptors when added later; missing optional dependencies do not crash analysis.",
        },
        "limitations": list(dict.fromkeys(limitations)),
    }


def render_sample_analysis_summary(analysis: dict[str, Any]) -> str:
    metadata = analysis["metadata"]
    timing = analysis["timing"]
    tonal = analysis["tonal"]
    loops = analysis["loop_detection"]["loopable_regions"]
    motifs = analysis["motif_hook_detection"]["hook_motif_candidates"]
    safety = analysis["sample_usage_safety"]
    return "\n".join(
        [
            "# Sample Analysis Summary",
            "",
            f"- path: {metadata['path']}",
            f"- duration: {metadata['duration_seconds']:.3f}s",
            f"- sample rate: {metadata['sample_rate']}",
            f"- channels: {metadata['channels']}",
            f"- peak: {analysis['level']['peak_dbfs']:.3f} dBFS",
            f"- RMS: {analysis['level']['rms_dbfs']:.3f} dBFS",
            f"- clipping count: {analysis['level']['clipping_count']}",
            f"- BPM: {timing.get('bpm')} ({timing.get('confidence')} confidence)",
            f"- BPM candidates: {', '.join(str(item) for item in timing.get('bpm_candidates', [])) or 'none'}",
            f"- key/pitch center: {tonal.get('estimated_key') or tonal.get('estimated_tonic_or_pitch_center') or 'unknown'} ({tonal.get('confidence')} confidence)",
            f"- loop candidates: {len(loops)}",
            f"- motif candidates: {len(motifs)}",
            f"- direct sample use allowed: {str(bool(safety['direct_sample_use_allowed'])).lower()}",
            f"- safety note: {safety['policy_note']}",
            "",
            "## Limitations",
            *[f"- {item}" for item in analysis.get("limitations", [])],
            "",
        ]
    )


def write_sample_analysis(
    path: str | Path,
    *,
    project_root: Path = PROJECT_ROOT,
    working_wav_path: str | Path | None = None,
    ownership_status: str | None = None,
) -> dict[str, Path]:
    analysis = analyze_sample_audio(path, working_wav_path=working_wav_path, ownership_status=ownership_status)
    json_path = project_root / "01_ANALYSIS" / "sample_analysis.json"
    summary_path = project_root / "01_ANALYSIS" / "sample_analysis_summary.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary_path.write_text(render_sample_analysis_summary(analysis), encoding="utf-8")
    return {"json": json_path, "summary": summary_path}
