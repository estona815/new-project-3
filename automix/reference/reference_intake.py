from __future__ import annotations

from pathlib import Path
from typing import Any

from automix.analyze_ai_pitch_source import safe_filename, write_json
from automix.export.audio_export_utils import wav_info
from automix.mastering.premaster_safety_analyzer import now_utc
from automix.reference.genre_target_profiles import DEFAULT_TARGET_PROFILE, get_target_profile


REFERENCE_ROLES = {
    "primary_reference",
    "vocal_balance_reference",
    "low_end_reference",
    "drum_energy_reference",
    "width_reference",
    "loudness_reference",
    "emotional_reference",
}


def normalize_reference_role(role: str | None) -> str:
    role = role or "primary_reference"
    return role if role in REFERENCE_ROLES else "primary_reference"


def reference_entry(path: Path, role: str | None = None, name: str | None = None) -> dict[str, Any]:
    path = Path(path)
    exists = path.exists()
    warnings: list[str] = []
    info = wav_info(path) if exists and path.suffix.lower() == ".wav" else {"exists": exists, "size_bytes": path.stat().st_size if exists else 0}
    if not exists:
        warnings.append("reference_file_missing")
    if exists and path.suffix.lower() != ".wav":
        warnings.append("only_wav_references_are_analyzed_by_local_engine")
    return {
        "name": name or safe_filename(path.stem),
        "path": str(path),
        "role": normalize_reference_role(role),
        "exists": exists,
        "duration_seconds": float(info.get("duration_seconds", 0.0)),
        "sample_rate": int(info.get("sample_rate", 0)),
        "channels": int(info.get("channels", 0)),
        "analysis_status": "pending" if exists and path.suffix.lower() == ".wav" else "blocked",
        "warnings": warnings,
    }


def build_reference_manifest(
    *,
    project_name: str,
    references: list[tuple[Path, str]] | None = None,
    target_profile: str | None = None,
    user_notes: str = "",
    output_dir: Path | None = None,
) -> dict[str, Any]:
    profile_name = target_profile or DEFAULT_TARGET_PROFILE
    get_target_profile(profile_name)
    refs = [reference_entry(path, role) for path, role in (references or [])]
    if not refs:
        refs = []
    manifest = {
        "schema": "automix-reference-manifest-v1",
        "created_at": now_utc(),
        "project_name": project_name,
        "references": refs,
        "target_profile": profile_name,
        "user_notes": user_notes,
        "copyright_safety_note": "Reference is used for broad mix/tonal/energy comparison only, not copying musical content.",
    }
    if output_dir:
        write_json(output_dir / "reference" / "reference_manifest.json", manifest)
    return manifest

