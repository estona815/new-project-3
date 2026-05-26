from __future__ import annotations

from pathlib import Path
from typing import Any


SUPPORTED_SAMPLE_EXTENSIONS = {".wav", ".aif", ".aiff", ".mp3", ".flac", ".m4a"}
ROLE_ORDER = ("main_motif", "response_motif", "texture_layer", "transition_element")
CONFIDENCE_WEIGHT = {"low": 0.28, "medium": 0.64, "high": 1.0}


def _confidence(value: Any) -> str:
    text = str(value or "low").lower()
    return text if text in CONFIDENCE_WEIGHT else "low"


def _score_confidence(value: Any) -> float:
    return CONFIDENCE_WEIGHT[_confidence(value)]


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _sample_id(index: int, path: str | Path | None = None) -> str:
    if path:
        stem = Path(path).stem.strip().replace(" ", "_")
        if stem:
            return stem
    return f"sample_{index + 1:02d}"


def _folder_files(sample_folder: str | Path | None) -> list[Path]:
    if not sample_folder:
        return []
    folder = Path(sample_folder).expanduser()
    if not folder.exists() or not folder.is_dir():
        return []
    return [
        path
        for path in sorted(folder.iterdir())
        if path.is_file() and path.suffix.lower() in SUPPORTED_SAMPLE_EXTENSIONS
    ]


def _analysis_entries(sample_analysis: dict[str, Any] | list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not sample_analysis:
        return []
    if isinstance(sample_analysis, list):
        return [item for item in sample_analysis if isinstance(item, dict)]
    if isinstance(sample_analysis.get("samples"), list):
        return [item for item in sample_analysis["samples"] if isinstance(item, dict)]
    if isinstance(sample_analysis.get("analyses"), list):
        return [item for item in sample_analysis["analyses"] if isinstance(item, dict)]
    return [sample_analysis]


def _candidate_score(candidate: dict[str, Any]) -> float:
    duration = max(0.01, _safe_float(candidate.get("end"), 1.0) - _safe_float(candidate.get("start"), 0.0))
    duration_score = 1.0 if 0.45 <= duration <= 2.5 else 0.58 if duration <= 4.0 else 0.32
    loopable = 0.18 if candidate.get("loopable") else 0.0
    tonal = 0.18 if candidate.get("tonal") else 0.0
    transition = 0.08 if "transition" in str(candidate.get("role_hint", "")).lower() else 0.0
    return round(_score_confidence(candidate.get("confidence")) * 0.56 + duration_score * 0.18 + loopable + tonal + transition, 4)


def _candidate_from_motif(entry: dict[str, Any], motif: dict[str, Any], index: int, motif_index: int) -> dict[str, Any]:
    metadata = entry.get("metadata") or {}
    path = metadata.get("path") or entry.get("path")
    start = _safe_float(motif.get("start"), 0.0)
    end = _safe_float(motif.get("end"), min(start + 1.8, _safe_float(metadata.get("duration_seconds"), start + 1.8)))
    reason = str(motif.get("reason") or "tonal, recognizable, loopable")
    candidate = {
        "sample_id": f"{_sample_id(index, path)}_{motif_index + 1:02d}" if motif_index else _sample_id(index, path),
        "source_path": str(path) if path else "",
        "start": round(start, 3),
        "end": round(max(end, start + 0.1), 3),
        "confidence": _confidence(motif.get("confidence")),
        "reason": reason,
        "role_hint": motif.get("role_hint") or "hook_candidate",
        "tonal": bool((entry.get("tonal") or {}).get("estimated_key") or (entry.get("tonal") or {}).get("estimated_tonic_or_pitch_center")),
        "loopable": "loop" in reason.lower() or bool(((entry.get("loop_detection") or {}).get("loopable_regions") or [])),
        "source": "sample_analysis.motif_hook_detection",
    }
    candidate["motif_score"] = _candidate_score(candidate)
    return candidate


def _candidate_from_analysis_fallback(entry: dict[str, Any], index: int) -> dict[str, Any]:
    metadata = entry.get("metadata") or {}
    path = metadata.get("path") or entry.get("path")
    duration = _safe_float(metadata.get("duration_seconds"), 1.8)
    candidate = {
        "sample_id": _sample_id(index, path),
        "source_path": str(path) if path else "",
        "start": 0.0,
        "end": round(max(0.1, min(duration, 1.8)), 3),
        "confidence": "low",
        "reason": "fallback first usable region; trim by ear",
        "role_hint": "fallback_sample_region",
        "tonal": bool((entry.get("tonal") or {}).get("estimated_key") or (entry.get("tonal") or {}).get("estimated_tonic_or_pitch_center")),
        "loopable": bool(((entry.get("loop_detection") or {}).get("loopable_regions") or [])),
        "source": "sample_analysis.fallback",
    }
    candidate["motif_score"] = _candidate_score(candidate)
    return candidate


def build_sample_candidates(
    *,
    sample_folder: str | Path | None = None,
    sample_analysis: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    entries = _analysis_entries(sample_analysis)
    for index, entry in enumerate(entries):
        motifs = ((entry.get("motif_hook_detection") or {}).get("hook_motif_candidates") or [])
        if motifs:
            for motif_index, motif in enumerate(motifs[:4]):
                candidates.append(_candidate_from_motif(entry, motif, index, motif_index))
        else:
            candidates.append(_candidate_from_analysis_fallback(entry, index))

    if not candidates:
        for index, path in enumerate(_folder_files(sample_folder)):
            candidate = {
                "sample_id": _sample_id(index, path),
                "source_path": str(path),
                "start": 0.0,
                "end": 1.8,
                "confidence": "low",
                "reason": "local sample file available; analyze and trim by ear",
                "role_hint": "local_file_candidate",
                "tonal": False,
                "loopable": False,
                "source": "sample_folder",
            }
            candidate["motif_score"] = _candidate_score(candidate)
            candidates.append(candidate)

    return sorted(candidates, key=lambda item: (item["motif_score"], item["confidence"], -item["start"]), reverse=True)


def _role_reason(candidate: dict[str, Any], role: str) -> str:
    if role == "main_motif":
        return "tonal, recognizable, loopable" if candidate.get("tonal") or candidate.get("loopable") else "most recognizable motif candidate"
    if role == "response_motif":
        return "contrasts main motif while staying repeatable"
    if role == "texture_layer":
        return "usable atmosphere at low density"
    return "short intentional transition element, not random glitch"


def assign_sample_roles(
    *,
    sample_folder: str | Path | None = None,
    sample_analysis: dict[str, Any] | list[dict[str, Any]] | None = None,
    song_key_bpm: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidates = build_sample_candidates(sample_folder=sample_folder, sample_analysis=sample_analysis)
    selected: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    for role_index, role in enumerate(ROLE_ORDER):
        candidate = next((item for item in candidates if item["sample_id"] not in used_ids), candidates[0] if candidates else None)
        if candidate is None:
            break
        if role in {"texture_layer", "transition_element"} and len(candidates) == 1:
            candidate = candidates[0]
        used_ids.add(candidate["sample_id"])
        selected.append(
            {
                "sample_id": candidate["sample_id"],
                "role": role,
                "start": candidate["start"],
                "end": candidate["end"],
                "source_path": candidate.get("source_path", ""),
                "reason": _role_reason(candidate, role),
                "confidence": candidate.get("confidence", "low"),
                "motif_score": candidate.get("motif_score", 0.0),
            }
        )

    bpm = (song_key_bpm or {}).get("bpm") or (song_key_bpm or {}).get("tempo_bpm")
    key = (song_key_bpm or {}).get("key") or (song_key_bpm or {}).get("estimated_key")
    return {
        "schema_version": "sample_role_assignment.v1",
        "selected_samples": selected,
        "candidate_count": len(candidates),
        "candidates": candidates[:12],
        "song_context": {
            "bpm": bpm,
            "key": key,
            "key_confidence": (song_key_bpm or {}).get("key_confidence") or (song_key_bpm or {}).get("confidence"),
        },
        "rules": [
            "Use fewer stronger samples.",
            "Main motif must repeat with variation.",
            "Avoid random glitch chop.",
            "Do not over-chop to compensate for missing melody.",
        ],
    }
