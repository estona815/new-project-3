from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINEERING_RULE_DIR = ROOT / "presets" / "engineering_rules"
DEFAULT_PROFILE_PATH = ENGINEERING_RULE_DIR / "default_engineering_rules.json"

DEFAULT_THRESHOLDS: dict[str, Any] = {
    "brightness_loss_warn_db": 1.0,
    "brightness_loss_fail_db": 2.5,
    "transient_loss_warn_ratio": 0.95,
    "transient_loss_fail_ratio": 0.90,
    "side_mid_change_warn_db": 1.5,
    "side_mid_change_fail_db": 3.0,
    "punch_loss_warn_db": 0.75,
    "punch_loss_fail_db": 1.5,
    "harshness_improvement_target_db": [0.5, 2.0],
    "sibilance_improvement_target_db": [0.5, 2.0],
    "true_peak_target_dbfs": -1.0,
    "clipping_peak_dbfs": -0.05,
    "duration_tolerance_sec": 0.5,
    "duration_tolerance_ratio": 0.01,
    "fullmix_deesser_max_reduction_db": 2.0,
    "master_bus_max_gain_reduction_db": 2.0,
    "master_dynamic_eq_max_reduction_db": 2.5,
    "resonance_min_q": 2.0,
}

FREQUENCY_MAP: dict[str, tuple[int, int]] = {
    "sub_rumble_hz": (0, 25),
    "deep_bass_hz": (25, 45),
    "bass_punch_hz": (45, 140),
    "low_mid_warmth_mud_hz": (140, 350),
    "box_nasal_congestion_hz": (350, 900),
    "presence_hz": (900, 3000),
    "harshness_hz": (3000, 8000),
    "sibilance_hz": (5000, 10000),
    "air_fizz_hz": (10000, 16000),
    "extreme_air_noise_hz": (16000, 22000),
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key == "inherits":
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _profile_path(profile: str | Path | None) -> Path:
    if profile is None:
        return DEFAULT_PROFILE_PATH
    path = Path(profile)
    if path.exists():
        return path
    name = str(profile)
    aliases = {
        "mp3": "mp3_source_rescue_rules.json",
        "mp3_source": "mp3_source_rescue_rules.json",
        "mp3_source_rescue": "mp3_source_rescue_rules.json",
        "fullmix": "fullmix_rescue_engineering_rules.json",
        "fullmix_rescue": "fullmix_rescue_engineering_rules.json",
        "vocal_rescue": "vocal_rescue_engineering_rules.json",
    }
    if name in aliases:
        alias_path = ENGINEERING_RULE_DIR / aliases[name]
        if alias_path.exists():
            return alias_path
    candidates = [
        ENGINEERING_RULE_DIR / name,
        ENGINEERING_RULE_DIR / f"{name}.json",
        ENGINEERING_RULE_DIR / f"{name}_engineering_rules.json",
        ENGINEERING_RULE_DIR / f"{name}_source_rescue_rules.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return path


def load_json_profile(profile: str | Path | None = None) -> dict[str, Any]:
    path = _profile_path(profile)
    if not path.exists():
        raise FileNotFoundError(f"Engineering rule profile not found: {profile}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_profile(profile: str | Path | None = None) -> dict[str, Any]:
    default = {
        "schema_version": 1,
        "profile_name": "default",
        "thresholds": copy.deepcopy(DEFAULT_THRESHOLDS),
        "frequency_map": {key: list(value) for key, value in FREQUENCY_MAP.items()},
        "allowed_ms_reasons": [
            "side wash reduction",
            "stereo harshness control",
            "low-end mono compatibility",
            "vocal center protection",
            "reverb/cymbal/synth side cleanup",
            "master bus width stabilization",
        ],
        "forbidden_language": {},
    }
    if DEFAULT_PROFILE_PATH.exists():
        default = _deep_merge(default, load_json_profile(DEFAULT_PROFILE_PATH))

    if profile is None:
        loaded = default
    else:
        path = _profile_path(profile)
        if path.resolve() == DEFAULT_PROFILE_PATH.resolve():
            loaded = default
        else:
            loaded = _deep_merge(default, load_json_profile(path))

    thresholds = _deep_merge(DEFAULT_THRESHOLDS, loaded.get("thresholds", {}))
    loaded["thresholds"] = thresholds
    return loaded


def thresholds_for(profile: dict[str, Any] | str | Path | None = None) -> dict[str, Any]:
    if isinstance(profile, dict):
        return _deep_merge(DEFAULT_THRESHOLDS, profile.get("thresholds", {}))
    return load_profile(profile).get("thresholds", copy.deepcopy(DEFAULT_THRESHOLDS))


def threshold(profile: dict[str, Any] | str | Path | None, key: str, default: Any = None) -> Any:
    thresholds = thresholds_for(profile)
    if default is None:
        default = DEFAULT_THRESHOLDS.get(key)
    return thresholds.get(key, default)


def audio_qc_profile(profile: dict[str, Any] | str | Path | None = None) -> dict[str, Any]:
    thresholds = thresholds_for(profile)
    return {
        "true_peak_target_dbfs": thresholds["true_peak_target_dbfs"],
        "max_acceptable_brightness_loss_db": thresholds["brightness_loss_warn_db"],
        "max_acceptable_transient_loss_ratio": 1.0 - thresholds["transient_loss_warn_ratio"],
        "max_acceptable_side_mid_change_db": thresholds["side_mid_change_warn_db"],
        "max_duration_delta_sec": thresholds["duration_tolerance_sec"],
        "max_duration_delta_ratio": thresholds["duration_tolerance_ratio"],
    }
