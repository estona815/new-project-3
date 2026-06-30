from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Any


def validate_render_file(path: Path | str | None) -> dict[str, Any]:
    if not path:
        return {
            "render_available": False,
            "evaluation_passed": False,
            "reason": "render_path_missing",
            "duration_seconds": 0.0,
            "file_size": 0,
        }
    render = Path(path)
    if not render.exists():
        return {
            "render_available": False,
            "evaluation_passed": False,
            "reason": "render_file_missing",
            "path": str(render),
            "duration_seconds": 0.0,
            "file_size": 0,
        }
    size = render.stat().st_size
    if size <= 0:
        return {
            "render_available": True,
            "evaluation_passed": False,
            "reason": "render_zero_byte",
            "path": str(render),
            "duration_seconds": 0.0,
            "file_size": size,
        }
    try:
        with wave.open(str(render), "rb") as wf:
            duration = wf.getnframes() / max(1, wf.getframerate())
    except wave.Error:
        return {
            "render_available": True,
            "evaluation_passed": False,
            "reason": "render_not_valid_wav",
            "path": str(render),
            "duration_seconds": 0.0,
            "file_size": size,
        }
    return {
        "render_available": True,
        "evaluation_passed": duration > 0.0,
        "reason": "ok" if duration > 0.0 else "render_duration_zero",
        "path": str(render),
        "duration_seconds": duration,
        "file_size": size,
    }


def build_mock_render_manifest(output_dir: Path, *, missing_render: bool = True) -> dict[str, Any]:
    manifest = {
        "schema": "prompt41-mock-render-manifest-v1",
        "mode": "mock_render",
        "renders": [],
        "evaluation_passed": False,
        "warnings": [],
    }
    if missing_render:
        manifest["renders"].append(validate_render_file(output_dir / "missing_render.wav"))
        manifest["warnings"].append("mock render unavailable; evaluation must not pass")
    path = output_dir / "eval_reports" / "prompt41_mock_render_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest
