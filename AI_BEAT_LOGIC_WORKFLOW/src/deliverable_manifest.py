from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


DELIVERABLE_FILENAMES = {
    "final_master": "final_master.wav",
    "mp3_preview": "final_preview.mp3",
    "reels_15sec": "reels_15sec.wav",
    "short_30sec": "short_30sec.wav",
    "instrumental": "instrumental.wav",
    "acapella": "acapella.wav",
    "premaster_headroom": "premaster_headroom.wav",
}


def _copy_if_available(source: str | Path | None, destination: Path) -> dict[str, Any] | None:
    if not source:
        return None
    src = Path(source)
    if not src.exists() or src.stat().st_size <= 0:
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, destination)
    return {"path": str(destination), "source_path": str(src), "file_size": destination.stat().st_size}


def build_deliverable_manifest(
    *,
    package_dir: str | Path,
    final_master_path: str | Path | None,
    optional_deliverables: dict[str, str | Path | None] | None = None,
) -> dict[str, Any]:
    root = Path(package_dir)
    deliverables_dir = root / "deliverables"
    deliverables_dir.mkdir(parents=True, exist_ok=True)
    optional = optional_deliverables or {}
    deliverables: list[dict[str, Any]] = []
    final_copy = _copy_if_available(final_master_path, deliverables_dir / DELIVERABLE_FILENAMES["final_master"])
    if final_copy:
        deliverables.append({"type": "final_master", "required": True, "available": True, **final_copy})
    else:
        deliverables.append({"type": "final_master", "required": True, "available": False, "path": str(deliverables_dir / DELIVERABLE_FILENAMES["final_master"])})
    for key in ("mp3_preview", "reels_15sec", "short_30sec", "instrumental", "acapella", "premaster_headroom"):
        copied = _copy_if_available(optional.get(key), deliverables_dir / DELIVERABLE_FILENAMES[key])
        deliverables.append(
            {
                "type": key,
                "required": False,
                "available": bool(copied),
                **(copied or {"path": str(deliverables_dir / DELIVERABLE_FILENAMES[key])}),
            }
        )
    return {
        "schema_version": "deliverable_manifest.v1",
        "deliverables_dir": str(deliverables_dir),
        "deliverables": deliverables,
        "notes": [
            "Optional deliverables are included only when source artifacts exist.",
            "Acapella and stems must not be faked; this manifest only copies available files.",
        ],
    }


def deliverable_by_type(manifest: dict[str, Any], deliverable_type: str) -> dict[str, Any] | None:
    for item in manifest.get("deliverables", []):
        if item.get("type") == deliverable_type:
            return item
    return None
