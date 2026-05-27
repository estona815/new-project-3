#!/usr/bin/env python3
"""Generate master policy from reference/current loudness and QC constraints."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02_ANALYSIS"))

from audio_utils import clamp, read_json, resolve_path, scalar_feature, write_json

SCALE = {"conservative": 0.6, "normal": 1.0, "aggressive": 1.35}


def item(value, reason):
    return {"value": value, "reason": reason}


def build_policy(mode: str = "normal") -> dict:
    scale = SCALE.get(mode, 1.0)
    current = read_json(resolve_path("02_ANALYSIS", "current_song_analysis.json"), {"stems": []})
    ref = read_json(resolve_path("00_REFERENCES", "reference_profiles", "estona_reference_profile.json"), {"feature_summary": {}})
    ref_lufs = scalar_feature(ref.get("feature_summary", {}), "integrated_lufs", -10.5)
    stems = [s for s in current.get("stems", []) if "error" not in s]
    avg_lufs = sum(s.get("integrated_lufs", -18) for s in stems) / max(1, len(stems))
    target = clamp(ref_lufs if ref.get("status") == "ok" else -10.5, -12.5, -8.0)
    drive = clamp((avg_lufs - target) * -0.08 * scale, 0.0, 2.5)
    policy = {
        "master_clip_drive": item(round(drive, 2), f"Average stem loudness proxy is {avg_lufs:.2f} LUFS versus target {target:.2f}; clip drive stays conservative."),
        "limiter_target_lufs": item(round(target, 2), "Target follows user-approved reference median when present, otherwise a safe digicore draft target."),
        "true_peak_ceiling": item(-1.0, "True peak ceiling leaves safety margin and avoids claiming final master without QC/listening approval."),
        "mp3_safety_ceiling": item(-1.2, "MP3 safety ceiling reduces codec overshoot risk."),
        "avoid_overcompressed_flat_master": item(True, "User preference rules reject overcompressed flat masters even for loud digicore/hyperpop energy."),
    }
    return {"engine": "ESTONA_AUTO_MIX_ENGINE", "policy_type": "master", "mode": mode, "policy": policy}


def generate_all() -> dict:
    policies = {}
    for mode in SCALE:
        policies[mode] = build_policy(mode)
        write_json(resolve_path("03_POLICY_ENGINE", f"master_policy_{mode}.json"), policies[mode])
    write_json(resolve_path("03_POLICY_ENGINE", "master_policy.json"), policies["normal"])
    return policies["normal"]


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode == "all":
        print(f"master policy status: {generate_all()['mode']}")
    else:
        write_json(resolve_path("03_POLICY_ENGINE", "master_policy.json"), build_policy(mode))
        print(f"master policy generated: {mode}")
