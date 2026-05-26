from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from deliverable_manifest import build_deliverable_manifest, deliverable_by_type
from final_verify import expected_bit_depth, expected_sample_rate, verify_final_wav
from release_metadata import build_release_metadata_payload, write_release_metadata_files
from release_qc import build_release_qc, render_release_qc_report
from rights_clearance_checklist import (
    build_rights_payload,
    render_cover_art_requirements,
    render_distribution_checklist,
    render_rights_clearance_checklist,
)


def _final_master_summary(final_master_path: str | Path | None, requested_format: str) -> dict[str, Any]:
    if not final_master_path:
        return {
            "path": "",
            "verified": False,
            "sample_rate": None,
            "bit_depth": None,
            "channels": None,
            "peak_dbfs": None,
            "rms_dbfs": None,
            "clipping_count": None,
            "duration_seconds": None,
            "codec_name": None,
            "format_verified": False,
            "expected_sample_rate": expected_sample_rate(requested_format),
            "expected_bit_depth": expected_bit_depth(requested_format),
            "exists": False,
            "blocking_reasons": ["final master WAV missing"],
        }
    verification = verify_final_wav(final_master_path, requested_format)
    return {
        "path": str(final_master_path),
        "verified": bool(verification.get("ok")),
        "exists": bool(verification.get("exists")),
        "duration_seconds": verification.get("duration_seconds"),
        "sample_rate": verification.get("sample_rate"),
        "expected_sample_rate": verification.get("expected_sample_rate"),
        "bit_depth": verification.get("bit_depth"),
        "expected_bit_depth": expected_bit_depth(requested_format),
        "channels": verification.get("channels"),
        "codec_name": verification.get("codec_name"),
        "format_verified": bool(verification.get("format_verified")),
        "peak_dbfs": verification.get("peak_dbfs"),
        "rms_dbfs": verification.get("rms_dbfs"),
        "clipping_count": verification.get("clipping_count"),
        "blocking_reasons": list(verification.get("errors", [])),
    }


def build_release_manifest(
    *,
    package_dir: str | Path,
    final_master_path: str | Path | None,
    requested_format: str = "wav24_48k",
    metadata: dict[str, Any] | None = None,
    rights: dict[str, Any] | None = None,
    optional_deliverables: dict[str, str | Path | None] | None = None,
    cover_art_path: str | Path | None = None,
    artwork_required: bool = False,
    mix_master: dict[str, Any] | None = None,
    arrangement: dict[str, Any] | None = None,
    reference_profile: dict[str, Any] | None = None,
    requested_deliverables: list[str] | None = None,
    completion_gate: dict[str, Any] | None = None,
    qc_report_path: str | Path | None = None,
    master_qc_report_path: str | Path | None = None,
    false_claim_risk: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata_payload = build_release_metadata_payload(metadata)
    rights_payload = build_rights_payload(**(rights or {}))
    deliverables = build_deliverable_manifest(
        package_dir=package_dir,
        final_master_path=final_master_path,
        optional_deliverables=optional_deliverables,
    )
    final_master = _final_master_summary(final_master_path, requested_format)
    final_deliverable = deliverable_by_type(deliverables, "final_master") or {}
    if final_deliverable.get("available"):
        final_master["path"] = final_deliverable.get("path", final_master["path"])
    cover_art_present = bool(cover_art_path and Path(cover_art_path).exists())
    qc = build_release_qc(
        final_master=final_master,
        metadata_payload=metadata_payload,
        rights_payload=rights_payload,
        deliverable_manifest=deliverables,
        cover_art_present=cover_art_present,
        artwork_required=artwork_required,
        mix_master=mix_master,
        arrangement=arrangement,
        reference_profile=reference_profile,
        requested_deliverables=requested_deliverables,
        completion_gate=completion_gate,
        qc_report_path=str(qc_report_path) if qc_report_path else None,
        master_qc_report_path=str(master_qc_report_path) if master_qc_report_path else None,
        release_qc_report_path=str(Path(package_dir) / "release_qc_report.md"),
        release_manifest_path=str(Path(package_dir) / "release_manifest.json"),
        rights_checklist_path=str(Path(package_dir) / "rights_clearance_checklist.md"),
        qc_report_exists=Path(qc_report_path).exists() if qc_report_path else True,
        master_qc_report_exists=Path(master_qc_report_path).exists() if master_qc_report_path else True,
        release_qc_report_exists=True,
        release_manifest_exists=True,
        rights_checklist_exists=True,
        false_claim_risk=false_claim_risk,
    )
    return {
        "schema_version": "release_manifest.v1",
        "release_ready": bool(qc["release_ready"]),
        "release_status": qc.get("status"),
        "average_score": qc.get("average_score"),
        "final_master": {
            "path": final_master.get("path", ""),
            "verified": bool(final_master.get("verified")),
            "duration_seconds": final_master.get("duration_seconds"),
            "sample_rate": final_master.get("sample_rate"),
            "bit_depth": final_master.get("bit_depth"),
            "channels": final_master.get("channels"),
            "codec_name": final_master.get("codec_name"),
            "format_verified": bool(final_master.get("format_verified")),
            "peak_dbfs": final_master.get("peak_dbfs"),
            "rms_dbfs": final_master.get("rms_dbfs"),
            "clipping_count": final_master.get("clipping_count"),
        },
        "deliverables": deliverables.get("deliverables", []),
        "metadata": metadata_payload["metadata"],
        "rights": rights_payload["rights"],
        "qc": {
            "release_qc_report": str(Path(package_dir) / "release_qc_report.md"),
            "blocking_issues": qc.get("blocking_issues", []),
            "status": qc.get("status"),
            "average_score": qc.get("average_score"),
            "categories": qc.get("categories", []),
        },
        "limitations": [
            *qc.get("limitations", []),
            "If metadata is missing, release package is draft and release_ready=false.",
            "Cover art requirements are documented when artwork is absent; local audio completion is blocked only when artwork is required.",
            "Do not invent ISRC or UPC.",
        ],
        "_internal": {
            "metadata_payload": metadata_payload,
            "rights_payload": rights_payload,
            "deliverable_manifest": deliverables,
            "release_qc": qc,
            "cover_art_present": cover_art_present,
            "artwork_required": artwork_required,
        },
    }


def write_release_package(
    project_root: str | Path,
    manifest: dict[str, Any],
) -> dict[str, Path]:
    root = Path(project_root)
    package_dir = root / "10_RELEASE_PACKAGE"
    package_dir.mkdir(parents=True, exist_ok=True)
    internal = manifest.get("_internal", {})
    metadata_payload = internal.get("metadata_payload") or build_release_metadata_payload(manifest.get("metadata"))
    rights_payload = internal.get("rights_payload") or {"rights": manifest.get("rights", {}), "release_ready": False, "blocking_issues": []}
    release_qc = internal.get("release_qc") or {"release_ready": False, "blocking_issues": manifest.get("qc", {}).get("blocking_issues", [])}
    metadata_paths = write_release_metadata_files(package_dir, metadata_payload)
    paths = {
        "manifest": package_dir / "release_manifest.json",
        "metadata_json": metadata_paths["json"],
        "metadata_md": metadata_paths["markdown"],
        "rights_checklist": package_dir / "rights_clearance_checklist.md",
        "distribution_checklist": package_dir / "distribution_checklist.md",
        "release_qc_report": package_dir / "release_qc_report.md",
    }
    public_manifest = {key: value for key, value in manifest.items() if key != "_internal"}
    paths["manifest"].write_text(json.dumps(public_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths["rights_checklist"].write_text(render_rights_clearance_checklist(rights_payload), encoding="utf-8")
    paths["distribution_checklist"].write_text(
        render_distribution_checklist(
            manifest.get("metadata", {}),
            cover_art_present=bool(internal.get("cover_art_present")),
            final_audio_verified=bool(manifest.get("final_master", {}).get("verified")),
        ),
        encoding="utf-8",
    )
    paths["release_qc_report"].write_text(render_release_qc_report(release_qc), encoding="utf-8")
    if not internal.get("cover_art_present"):
        cover_path = package_dir / "cover_art_requirements.md"
        cover_path.write_text(render_cover_art_requirements(), encoding="utf-8")
        paths["cover_art_requirements"] = cover_path
    return paths


def build_and_write_release_package(
    project_root: str | Path,
    *,
    final_master_path: str | Path | None,
    requested_format: str = "wav24_48k",
    metadata: dict[str, Any] | None = None,
    rights: dict[str, Any] | None = None,
    optional_deliverables: dict[str, str | Path | None] | None = None,
    cover_art_path: str | Path | None = None,
    artwork_required: bool = False,
    mix_master: dict[str, Any] | None = None,
    arrangement: dict[str, Any] | None = None,
    reference_profile: dict[str, Any] | None = None,
    requested_deliverables: list[str] | None = None,
    completion_gate: dict[str, Any] | None = None,
    qc_report_path: str | Path | None = None,
    master_qc_report_path: str | Path | None = None,
    false_claim_risk: dict[str, Any] | None = None,
) -> dict[str, Any]:
    package_dir = Path(project_root) / "10_RELEASE_PACKAGE"
    manifest = build_release_manifest(
        package_dir=package_dir,
        final_master_path=final_master_path,
        requested_format=requested_format,
        metadata=metadata,
        rights=rights,
        optional_deliverables=optional_deliverables,
        cover_art_path=cover_art_path,
        artwork_required=artwork_required,
        mix_master=mix_master,
        arrangement=arrangement,
        reference_profile=reference_profile,
        requested_deliverables=requested_deliverables,
        completion_gate=completion_gate,
        qc_report_path=qc_report_path,
        master_qc_report_path=master_qc_report_path,
        false_claim_risk=false_claim_risk,
    )
    paths = write_release_package(project_root, manifest)
    return {"manifest": {key: value for key, value in manifest.items() if key != "_internal"}, "paths": paths}
