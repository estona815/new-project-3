from __future__ import annotations

from typing import Any


RELEASE_MASTER_TARGETS: dict[str, dict[str, Any]] = {
    "master_ready_headroom": {
        "mode": "master_ready_headroom",
        "default_for_release": False,
        "peak_target_dbfs": -2.5,
        "limiter_ceiling_dbfs": -1.5,
        "character": "conservative",
        "warning": "Useful for later mastering; do not overlimit.",
        "rules": ["preserve dynamics", "leave headroom", "do not overlimit"],
    },
    "streaming_safe": {
        "mode": "streaming_safe",
        "default_for_release": True,
        "peak_target_dbfs": -1.0,
        "limiter_ceiling_dbfs": -1.0,
        "character": "safe peak target",
        "warning": "No clipping; preserve clarity.",
        "rules": ["safe peak target", "no clipping", "preserve clarity"],
    },
    "loud_demo": {
        "mode": "loud_demo",
        "default_for_release": False,
        "peak_target_dbfs": -0.8,
        "limiter_ceiling_dbfs": -0.8,
        "character": "louder preview",
        "warning": "Reduced headroom; not default release master unless user requests it.",
        "rules": ["preview loudness only", "warn reduced headroom", "no clipping"],
    },
    "release_master": {
        "mode": "release_master",
        "default_for_release": False,
        "peak_target_dbfs": -1.0,
        "limiter_ceiling_dbfs": -1.0,
        "character": "verified final release WAV",
        "warning": "Requires verified final WAV, correct format, no clipping, QC report, and release checklist.",
        "rules": ["verified final WAV", "correct format", "no clipping", "QC report exists", "release checklist exists"],
    },
}


def normalize_release_master_target(mode: str | None, *, release_ready: bool = False) -> str:
    if mode in RELEASE_MASTER_TARGETS:
        return str(mode)
    return "streaming_safe" if release_ready else "master_ready_headroom"


def build_release_master_target(mode: str | None = None, *, release_ready: bool = False) -> dict[str, Any]:
    selected = normalize_release_master_target(mode, release_ready=release_ready)
    target = RELEASE_MASTER_TARGETS[selected]
    return {
        **target,
        "completion_requirements": [
            "final WAV exists and size is greater than zero",
            "final WAV duration is readable",
            "requested sample rate and 24-bit PCM/requested format are verified",
            "peak/RMS/clipping metrics are verified",
            "QC report exists",
            "release checklist exists when release package readiness is requested",
        ],
    }


def release_master_verified(
    *,
    final_verify_result: dict[str, Any] | None,
    qc_report_exists: bool = False,
    release_checklist_exists: bool = False,
    require_release_checklist: bool = False,
) -> dict[str, Any]:
    verification = final_verify_result or {}
    blocking: list[str] = []
    if not bool(verification.get("ok") or verification.get("passed")):
        blocking.append("final_verify did not pass")
    if not verification.get("format_verified"):
        blocking.append("final WAV format is not verified")
    if int(verification.get("clipping_count") or 0) > 0:
        blocking.append("clipping detected")
    if not qc_report_exists:
        blocking.append("QC report missing")
    if require_release_checklist and not release_checklist_exists:
        blocking.append("release checklist missing")
    return {
        "verified": not blocking,
        "blocking_reasons": list(dict.fromkeys(blocking)),
        "verification_source": "final_verify",
    }
