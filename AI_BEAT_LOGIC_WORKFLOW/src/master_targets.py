from __future__ import annotations

from typing import Any


MASTER_TARGETS: dict[str, dict[str, Any]] = {
    "master_ready_headroom": {
        "peak_target_range_dbfs": [-3.0, -1.5],
        "limiting": "minimal",
        "dynamics": "preserve",
        "warning": "No aggressive limiting; leave headroom for later mastering.",
    },
    "streaming_safe": {
        "peak_target_range_dbfs": [-1.2, -0.8],
        "limiting": "controlled",
        "dynamics": "preserve",
        "warning": "Streaming-safe approximation; preserve dynamics and avoid clipping.",
    },
    "loud_demo": {
        "peak_target_range_dbfs": [-1.0, -0.6],
        "limiting": "louder_preview",
        "dynamics": "reduced_headroom",
        "warning": "Louder preview with reduced headroom; no severe clipping is allowed.",
    },
    "release_master": {
        "peak_target_range_dbfs": [-1.2, -0.8],
        "limiting": "controlled_release",
        "dynamics": "preserve_clarity",
        "warning": "Release master requires final verification, QC report, and release checklist.",
    },
}


def normalize_master_target(mode: str | None) -> str:
    return mode if mode in MASTER_TARGETS else "master_ready_headroom"


def build_master_chain(mode: str | None = None) -> dict[str, Any]:
    selected = normalize_master_target(mode)
    target = MASTER_TARGETS[selected]
    return {
        "target_mode": selected,
        **target,
        "chain": [
            "pre-master gain trim",
            "sub-rumble high-pass only when needed",
            "broad tonal EQ",
            "gentle glue compression",
            "optional controlled saturation",
            "final limiter only at the end",
            "export verification before any completion claim",
        ],
        "rules": [
            "No clipping.",
            "No overcompressed loudness-war result.",
            "Release package readiness requires verified final audio and release checklist.",
            "Commercial readiness means technical readiness and QC discipline, not commercial success.",
        ],
    }
