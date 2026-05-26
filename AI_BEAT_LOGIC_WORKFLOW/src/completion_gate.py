from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from final_verify import verify_final_wav


EXPECTED_SAMPLE_RATES = {
    "wav24_48k": 48000,
    "wav24_44k": 44100,
}


@dataclass
class CompletionStatus:
    complete: bool
    final_wav_path: str | None
    qc_report_path: str | None
    requested_format: str
    blocking_reasons: list[str] = field(default_factory=list)
    verified_final_wav: bool = False
    verified_qc_report: bool = False
    verified_format: bool = False
    verified_audio_metrics: bool = False
    verified_release_package: bool = False
    verification_summary: dict[str, Any] = field(default_factory=dict)


def _path_or_none(path: str | Path | None) -> Path | None:
    return Path(path).expanduser() if path else None


def _has_required_metrics(verification: dict[str, Any]) -> bool:
    required = ("duration_seconds", "peak_dbfs", "rms_dbfs", "clipping_count")
    return all(key in verification and verification[key] is not None for key in required)


def check_completion_status(
    *,
    final_wav_path: str | Path | None,
    qc_report_path: str | Path | None,
    requested_format: str,
    final_verify_result: dict | None = None,
    require_master_qc: bool = False,
    master_qc_report_path: str | Path | None = None,
    require_release_package: bool = False,
    release_package_manifest_path: str | Path | None = None,
    release_qc_report_path: str | Path | None = None,
) -> CompletionStatus:
    blocking: list[str] = []
    final_path = _path_or_none(final_wav_path)
    report_path = _path_or_none(qc_report_path)
    master_report_path = _path_or_none(master_qc_report_path)
    release_manifest_path = _path_or_none(release_package_manifest_path)
    release_qc_path = _path_or_none(release_qc_report_path)
    verification_summary: dict[str, Any] = {}

    verified_final_wav = False
    verified_qc_report = False
    verified_format = False
    verified_audio_metrics = False
    verified_release_package = False

    if requested_format not in EXPECTED_SAMPLE_RATES:
        blocking.append(f"unsupported requested format: {requested_format}")

    if final_path is None:
        blocking.append("final WAV path was not provided")
    elif not final_path.exists():
        blocking.append(f"final WAV missing: {final_path}")
    elif final_path.stat().st_size <= 0:
        blocking.append(f"final WAV is empty: {final_path}")
    else:
        verified_final_wav = True
        if final_verify_result is None:
            try:
                final_verify_result = verify_final_wav(final_path, requested_format)
            except Exception as error:  # noqa: BLE001 - completion gate must fail closed.
                blocking.append(f"peak/RMS/clipping verification did not complete: {error}")

        if final_verify_result:
            verification_summary.update(final_verify_result)
            if _has_required_metrics(final_verify_result):
                verified_audio_metrics = True
            else:
                blocking.append("peak/RMS/clipping verification is incomplete")
            verified_format = bool(final_verify_result.get("format_verified"))
            if not final_verify_result.get("exists", True):
                blocking.append(f"final WAV missing: {final_path}")
            if not final_verify_result.get("format_verified"):
                blocking.append("final WAV requested format was not verified")
            if final_verify_result.get("ok") is False:
                blocking.append("final WAV verification did not pass")
            if final_verify_result.get("errors"):
                blocking.extend(str(error) for error in final_verify_result["errors"])
            if final_verify_result.get("warnings"):
                blocking.extend(str(warning) for warning in final_verify_result["warnings"])
            if final_verify_result.get("passed") is False:
                blocking.append("final WAV verification did not pass")
        else:
            blocking.append("peak/RMS/clipping verification is missing")

    if report_path is None:
        blocking.append("QC report path was not provided")
    elif not report_path.exists():
        blocking.append(f"QC report missing: {report_path}")
    elif report_path.stat().st_size <= 0:
        blocking.append(f"QC report is empty: {report_path}")
    else:
        verified_qc_report = True

    if require_master_qc:
        if master_report_path is None:
            blocking.append("master QC report path was not provided")
        elif not master_report_path.exists():
            blocking.append(f"master QC report missing: {master_report_path}")
        elif master_report_path.stat().st_size <= 0:
            blocking.append(f"master QC report is empty: {master_report_path}")

    if require_release_package:
        if release_manifest_path is None:
            blocking.append("release package manifest path was not provided")
        elif not release_manifest_path.exists():
            blocking.append(f"release package manifest missing: {release_manifest_path}")
        elif release_manifest_path.stat().st_size <= 0:
            blocking.append(f"release package manifest is empty: {release_manifest_path}")
        else:
            try:
                release_payload = json.loads(release_manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as error:
                blocking.append(f"release package manifest could not be parsed: {error}")
            else:
                verified_release_package = bool(release_payload.get("release_ready"))
                if not verified_release_package:
                    reasons = (
                        release_payload.get("blocking_reasons")
                        or (release_payload.get("qc") or {}).get("blocking_issues")
                        or ["release package did not pass"]
                    )
                    blocking.extend(str(reason) for reason in reasons)
        if release_qc_path is None:
            blocking.append("release QC report path was not provided")
        elif not release_qc_path.exists():
            blocking.append(f"release QC report missing: {release_qc_path}")
        elif release_qc_path.stat().st_size <= 0:
            blocking.append(f"release QC report is empty: {release_qc_path}")

    blocking = list(dict.fromkeys(blocking))
    return CompletionStatus(
        complete=not blocking,
        final_wav_path=str(final_path) if final_path else None,
        qc_report_path=str(report_path) if report_path else None,
        requested_format=requested_format,
        blocking_reasons=blocking,
        verified_final_wav=verified_final_wav,
        verified_qc_report=verified_qc_report,
        verified_format=verified_format,
        verified_audio_metrics=verified_audio_metrics,
        verified_release_package=verified_release_package,
        verification_summary=verification_summary,
    )
