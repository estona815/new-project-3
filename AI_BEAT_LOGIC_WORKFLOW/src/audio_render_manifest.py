from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from export_status import derive_render_status


def _gate_dict(completion_gate: Any) -> dict[str, Any]:
    if completion_gate is None:
        return {"complete": False, "blocking_reasons": ["completion gate was not run"]}
    if isinstance(completion_gate, dict):
        return {
            "complete": bool(completion_gate.get("complete")),
            "blocking_reasons": list(completion_gate.get("blocking_reasons", [])),
        }
    if is_dataclass(completion_gate):
        payload = asdict(completion_gate)
        return {"complete": bool(payload.get("complete")), "blocking_reasons": list(payload.get("blocking_reasons", []))}
    return {"complete": False, "blocking_reasons": ["completion gate status could not be parsed"]}


def build_audio_render_manifest(
    *,
    status: str | None = None,
    source_files: list[str] | None = None,
    rendered_files: list[str] | None = None,
    final_verify_result: dict[str, Any] | None = None,
    qc_report_path: str | Path | None = None,
    master_qc_report_path: str | Path | None = None,
    completion_gate: Any = None,
) -> dict[str, Any]:
    verification = final_verify_result or {}
    gate = _gate_dict(completion_gate)
    final_path = Path(str(verification.get("path"))) if verification.get("path") else None
    final_exists = bool(verification.get("exists") if "exists" in verification else final_path and final_path.exists())
    final_verified = bool(verification.get("ok") or verification.get("passed") or verification.get("format_verified") and not verification.get("errors"))
    resolved_status = status or derive_render_status(
        final_wav_exists=final_exists,
        final_wav_verified=final_verified,
        completion_complete=bool(gate.get("complete")),
    )
    return {
        "schema_version": "audio_render_manifest.v1",
        "status": resolved_status,
        "source_files": source_files or [],
        "rendered_files": rendered_files or [],
        "final_wav": {
            "path": str(final_path) if final_path else None,
            "exists": final_exists,
            "verified": final_verified,
            "sample_rate": verification.get("sample_rate"),
            "bit_depth": verification.get("bit_depth"),
            "codec": verification.get("codec_name"),
            "peak_dbfs": verification.get("peak_dbfs"),
            "rms_dbfs": verification.get("rms_dbfs"),
            "clipping_count": verification.get("clipping_count"),
        },
        "qc_reports": {
            "qc_report": str(qc_report_path) if qc_report_path else None,
            "master_qc_report": str(master_qc_report_path) if master_qc_report_path else None,
        },
        "completion_gate": gate,
    }


def write_audio_render_manifest(path: str | Path, manifest: dict[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output
