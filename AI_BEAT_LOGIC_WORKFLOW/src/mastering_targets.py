from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_MASTER_LOUDNESS = {"streaming_safe", "loud_demo", "master_ready_headroom", "release_master"}


@dataclass(frozen=True)
class MasteringTarget:
    name: str
    peak_target_dbfs: float
    limiter_ceiling_dbfs: float
    compression_ratio: float
    compression_threshold_dbfs: float
    saturation_drive: float
    warning: str


TARGETS = {
    "master_ready_headroom": MasteringTarget(
        name="master_ready_headroom",
        peak_target_dbfs=-2.5,
        limiter_ceiling_dbfs=-1.5,
        compression_ratio=1.15,
        compression_threshold_dbfs=-10.0,
        saturation_drive=1.0,
        warning="Conservative headroom target for later mastering; no aggressive limiting.",
    ),
    "streaming_safe": MasteringTarget(
        name="streaming_safe",
        peak_target_dbfs=-1.0,
        limiter_ceiling_dbfs=-1.0,
        compression_ratio=1.25,
        compression_threshold_dbfs=-12.0,
        saturation_drive=1.01,
        warning="Streaming-safe approximation; preserve dynamics and avoid crushed loudness.",
    ),
    "loud_demo": MasteringTarget(
        name="loud_demo",
        peak_target_dbfs=-0.8,
        limiter_ceiling_dbfs=-0.8,
        compression_ratio=1.45,
        compression_threshold_dbfs=-14.0,
        saturation_drive=1.03,
        warning="Louder preview with reduced headroom; less master-ready than conservative targets.",
    ),
    "release_master": MasteringTarget(
        name="release_master",
        peak_target_dbfs=-1.0,
        limiter_ceiling_dbfs=-1.0,
        compression_ratio=1.25,
        compression_threshold_dbfs=-12.0,
        saturation_drive=1.01,
        warning="Release master target requires final_verify, QC report, and release checklist before release package readiness.",
    ),
}


def get_mastering_target(name: str | None) -> MasteringTarget:
    resolved = name or "master_ready_headroom"
    if resolved not in TARGETS:
        raise ValueError(f"Unsupported master loudness target: {resolved}")
    return TARGETS[resolved]
