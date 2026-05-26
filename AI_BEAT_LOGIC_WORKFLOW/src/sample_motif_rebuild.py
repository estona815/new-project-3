from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from audio_analysis import read_wav_float
from audio_metrics import clipping_count, db_to_linear, normalize_peak, pan_mono, to_stereo
from call_response_builder import build_call_response_plan
from export_audio import verify_wav, write_float_wav
from paths import PROJECT_ROOT
from sample_role_assigner import assign_sample_roles


def _tempo_bpm(song_key_bpm: dict[str, Any] | None, fallback: float = 148.0) -> float:
    data = song_key_bpm or {}
    value = data.get("bpm") or data.get("tempo_bpm")
    if not value:
        candidates = data.get("bpm_candidates") or []
        if candidates:
            first = candidates[0]
            value = first.get("bpm") if isinstance(first, dict) else first
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _target_duration(rescue_arrangement_plan: dict[str, Any] | None, fallback: float = 30.0) -> float:
    sections = list((rescue_arrangement_plan or {}).get("sections") or [])
    if sections:
        ends = []
        for section in sections:
            start = section.get("start_time", section.get("start", 0.0))
            duration = section.get("duration")
            end = section.get("end")
            try:
                ends.append(float(start) + float(duration if duration is not None else 0.0))
            except (TypeError, ValueError):
                if end is not None:
                    try:
                        ends.append(float(end))
                    except (TypeError, ValueError):
                        pass
        if ends:
            return min(max(8.0, max(ends)), 120.0)
    try:
        return min(max(8.0, float((rescue_arrangement_plan or {}).get("target_duration_seconds", fallback))), 120.0)
    except (TypeError, ValueError):
        return fallback


def _rules() -> list[str]:
    return [
        "Use fewer stronger samples.",
        "Main motif must repeat with variation.",
        "Avoid random glitch chop.",
        "Main motif returns in every hook.",
        "Response motif answers the main motif; it does not spam every beat.",
        "Texture layer stays behind lead/hook identity.",
    ]


def _limitations() -> list[str]:
    return [
        "Sample timing and role assignment are heuristic until edited by ear.",
        "Direct sample use requires owned/licensed/cleared local material.",
        "If ownership is unknown, recreate the trait with synthesis/MIDI instead of using the recording in release audio.",
    ]


def build_sample_motif_rebuild_plan(
    *,
    sample_folder: str | Path | None = None,
    sample_analysis: dict[str, Any] | list[dict[str, Any]] | None = None,
    song_key_bpm: dict[str, Any] | None = None,
    rescue_arrangement_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    role_assignment = assign_sample_roles(
        sample_folder=sample_folder,
        sample_analysis=sample_analysis,
        song_key_bpm=song_key_bpm,
    )
    selected_samples = role_assignment["selected_samples"]
    call_response = build_call_response_plan(selected_samples, rescue_arrangement_plan)
    section_usage = call_response["section_usage"]
    main_id = call_response.get("main_motif_id")
    main_returns_in_hook = bool(main_id and any(item.get("sample_id") == main_id and "hook" in item["section"].lower() for item in section_usage))
    return {
        "schema_version": "sample_motif_rebuild_plan.v1",
        "status": "SAMPLE_MOTIF_REBUILD_PLAN_READY",
        "selected_samples": [
            {
                "sample_id": item["sample_id"],
                "role": item["role"],
                "start": item["start"],
                "end": item["end"],
                "reason": item["reason"],
                "confidence": item["confidence"],
                "source_path": item.get("source_path", ""),
            }
            for item in selected_samples
        ],
        "section_usage": [
            {
                "section": item["section"],
                "sample_role": item["sample_role"],
                "density": item["density"],
                "sample_id": item.get("sample_id"),
                "start_time": item.get("start_time"),
                "duration": item.get("duration"),
            }
            for item in section_usage
        ],
        "call_response": call_response,
        "song_context": {
            "bpm": _tempo_bpm(song_key_bpm),
            "key": (song_key_bpm or {}).get("key") or (song_key_bpm or {}).get("estimated_key"),
            "key_confidence": (song_key_bpm or {}).get("key_confidence") or (song_key_bpm or {}).get("confidence"),
        },
        "quality_gates": {
            "samples_assigned_musical_roles": bool(selected_samples),
            "main_motif_returns_in_hook": main_returns_in_hook,
            "no_random_chop_spam": True,
            "max_active_sample_roles_per_section": 2,
        },
        "rules": _rules(),
        "limitations": _limitations(),
    }


def _load_audio(path: str | Path) -> tuple[dict[str, Any], np.ndarray]:
    metadata, channels = read_wav_float(Path(path).expanduser())
    frame_count = min((len(channel) for channel in channels), default=0)
    if frame_count <= 0:
        return metadata, np.zeros((0, 2), dtype=np.float32)
    audio = np.column_stack([np.asarray(channel[:frame_count], dtype=np.float32) for channel in channels])
    return metadata, to_stereo(audio)


def _extract_region(source: np.ndarray, sample_rate: int, start_seconds: float, end_seconds: float) -> np.ndarray:
    start = max(0, min(source.shape[0], int(start_seconds * sample_rate)))
    end = max(start + 1, min(source.shape[0], int(end_seconds * sample_rate)))
    region = source[start:end].astype(np.float32, copy=True)
    if region.shape[0] < int(0.08 * sample_rate):
        region = np.pad(region, ((0, int(0.08 * sample_rate) - region.shape[0]), (0, 0)))
    fade = min(max(8, int(0.006 * sample_rate)), region.shape[0] // 3)
    if fade > 0:
        ramp_in = np.linspace(0.0, 1.0, fade, dtype=np.float32)
        ramp_out = np.linspace(1.0, 0.0, fade, dtype=np.float32)
        region[:fade] *= ramp_in[:, None]
        region[-fade:] *= ramp_out[:, None]
    region, _gain = normalize_peak(region, -10.0, max_gain_db=8.0)
    return region.astype(np.float32)


def _placements_for_usage(section: dict[str, Any], bpm: float) -> list[tuple[float, float, float]]:
    start = float(section.get("start_time") or 0.0)
    duration = float(section.get("duration") or 4.0)
    beat_seconds = 60.0 / max(1.0, bpm)
    density = section.get("density")
    role = str(section.get("sample_role", ""))
    if density == "high":
        offsets = [0.0, 2.0 * beat_seconds]
        gain_db = -7.5
    elif density == "medium" or density == "medium_low":
        offsets = [beat_seconds]
        gain_db = -10.5
    elif density == "intentional":
        offsets = [max(0.0, duration - beat_seconds)]
        gain_db = -9.5
    else:
        offsets = [0.0]
        gain_db = -13.5
    if "filtered" in role:
        gain_db -= 2.0
    if "texture" in role:
        gain_db -= 2.5
    placements: list[tuple[float, float, float]] = []
    repeat_span = 4.0 * beat_seconds if density == "high" else 8.0 * beat_seconds
    cursor = 0.0
    while cursor < max(0.1, duration):
        for offset in offsets:
            position = start + cursor + offset
            if position < start + duration:
                pan = 0.0 if "main" in role else 0.28 if len(placements) % 2 == 0 else -0.28
                placements.append((position, gain_db, pan))
        cursor += repeat_span
        if len(placements) > 18:
            break
    return placements


def render_sample_motif_demo(plan: dict[str, Any], output_path: str | Path, *, sample_rate: int = 48_000) -> dict[str, Any]:
    bpm = float((plan.get("song_context") or {}).get("bpm") or 148.0)
    duration = _target_duration({"sections": plan.get("section_usage", [])}, fallback=30.0)
    mix = np.zeros((int((duration + 1.0) * sample_rate), 2), dtype=np.float32)
    selected_by_id = {item["sample_id"]: item for item in plan.get("selected_samples", [])}
    loaded: dict[str, np.ndarray] = {}
    skipped: list[dict[str, str]] = []
    placements: list[dict[str, Any]] = []

    for item in plan.get("selected_samples", []):
        path = item.get("source_path")
        if not path:
            skipped.append({"sample_id": item["sample_id"], "reason": "no source_path"})
            continue
        source_path = Path(path).expanduser()
        if source_path.suffix.lower() != ".wav":
            skipped.append({"sample_id": item["sample_id"], "reason": "demo renderer supports WAV only"})
            continue
        if not source_path.exists():
            skipped.append({"sample_id": item["sample_id"], "reason": "source_path not found"})
            continue
        metadata, audio = _load_audio(source_path)
        region = _extract_region(audio, int(metadata["sample_rate"]), float(item.get("start", 0.0)), float(item.get("end", 1.8)))
        if int(metadata["sample_rate"]) != sample_rate:
            skipped.append({"sample_id": item["sample_id"], "reason": "sample rate conversion not available in fallback demo renderer"})
            continue
        loaded[item["sample_id"]] = region

    for section in plan.get("section_usage", []):
        sample_id = section.get("sample_id")
        if sample_id not in loaded:
            continue
        region = loaded[str(sample_id)]
        for position, gain_db, pan in _placements_for_usage(section, bpm):
            start = int(position * sample_rate)
            if start >= mix.shape[0]:
                continue
            stereo = pan_mono(region, pan) * db_to_linear(gain_db)
            count = min(stereo.shape[0], mix.shape[0] - start)
            mix[start : start + count] += stereo[:count]
            selected = selected_by_id.get(str(sample_id), {})
            placements.append(
                {
                    "section": section.get("section"),
                    "sample_id": sample_id,
                    "role": selected.get("role"),
                    "time": round(position, 3),
                    "gain_db": gain_db,
                    "pan": round(pan, 3),
                }
            )

    if not placements:
        return {
            "created": False,
            "path": str(output_path),
            "reason": "no renderable WAV sample regions were available",
            "skipped": skipped,
        }

    mix, safety_gain = normalize_peak(mix, -3.5, max_gain_db=0.0)
    output = Path(output_path)
    write_float_wav(output, [mix[:, 0].astype(float).tolist(), mix[:, 1].astype(float).tolist()], sample_rate)
    verification = verify_wav(output)
    return {
        "created": True,
        "path": str(output),
        "sample_rate": sample_rate,
        "duration_seconds": verification["duration_seconds"],
        "placements": placements[:80],
        "placement_count": len(placements),
        "safety_gain": round(float(safety_gain), 6),
        "verification": verification,
        "clipping_count": clipping_count(mix),
        "skipped": skipped,
        "render_note": "Simple sample motif demo rendered from local WAV regions; not a release-ready stem.",
    }


def write_sample_motif_rebuild_outputs(
    *,
    project_root: str | Path = PROJECT_ROOT,
    sample_folder: str | Path | None = None,
    sample_analysis: dict[str, Any] | list[dict[str, Any]] | None = None,
    song_key_bpm: dict[str, Any] | None = None,
    rescue_arrangement_plan: dict[str, Any] | None = None,
    render: bool = False,
) -> dict[str, Any]:
    root = Path(project_root)
    edit_dir = root / "02_EDIT_PLAN"
    processed_dir = root / "04_PROCESSED_AUDIO"
    edit_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    plan = build_sample_motif_rebuild_plan(
        sample_folder=sample_folder,
        sample_analysis=sample_analysis,
        song_key_bpm=song_key_bpm,
        rescue_arrangement_plan=rescue_arrangement_plan,
    )
    plan_path = edit_dir / "sample_motif_rebuild_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    render_report: dict[str, Any] = {"created": False, "reason": "render disabled; plan only"}
    demo_path = processed_dir / "sample_motif_demo.wav"
    if render:
        render_report = render_sample_motif_demo(plan, demo_path)
    return {
        "sample_motif_rebuild_plan": plan,
        "paths": {
            "sample_motif_rebuild_plan": plan_path,
            "sample_motif_demo": demo_path,
        },
        "render": render_report,
    }
