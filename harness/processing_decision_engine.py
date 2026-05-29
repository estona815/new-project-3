from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .qc_thresholds import load_profile, thresholds_for
except ImportError:  # pragma: no cover - direct script execution.
    from qc_thresholds import load_profile, thresholds_for


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True)


def _metric(payload: dict[str, Any], key: str, default: float = 0.0) -> float:
    metrics = payload.get("metrics", payload)
    if isinstance(metrics, dict):
        if key in metrics:
            return _number(metrics[key], default)
        delta = metrics.get("delta")
        if isinstance(delta, dict) and key in delta:
            return _number(delta[key], default)
        after = metrics.get("after")
        if isinstance(after, dict) and key in after:
            return _number(after[key], default)
    return default


def _has_stems(payload: dict[str, Any]) -> bool:
    stems = _as_list(payload.get("available_stems"))
    roles = _as_list(payload.get("stem_roles"))
    return bool(stems or roles)


def _source_is_lossy(payload: dict[str, Any]) -> bool:
    fmt = _text(payload.get("source_format") or payload.get("format")).lower()
    return bool(payload.get("source_is_lossy")) or fmt in {"mp3", "aac", "m4a", "ogg", "opus", "lossy"}


def recommend_processing_plan(input_payload: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = profile or load_profile(input_payload.get("profile"))
    thresholds = thresholds_for(profile)
    warnings: list[str] = []
    forbidden_claims: list[str] = []
    eq_moves: list[dict[str, Any]] = []
    ms_moves: list[dict[str, Any]] = []
    dynamic_eq_bands: list[dict[str, Any]] = []
    compression: list[dict[str, Any]] = []
    deesser: list[dict[str, Any]] = []
    deai_intensity = "mild"

    mode = _text(input_payload.get("mode")).lower()
    source_format = _text(input_payload.get("source_format") or input_payload.get("format")).lower()
    harshness = _metric(input_payload, "harshness_band_db")
    sibilance = _metric(input_payload, "sibilance_band_db")
    air_fizz = _metric(input_payload, "air_fizz_band_db")
    side_mid = _metric(input_payload, "side_mid_ratio_db")
    punch = _metric(input_payload, "low_band_energy_db")
    transient = _metric(input_payload, "transient_proxy")
    has_stems = _has_stems(input_payload)

    if not has_stems:
        forbidden_claims.extend(["stem mix", "stem-assisted rebuild", "true rebeat", "beat fully re-created"])
        warnings.append("No stems were reported; use fullmix rescue language unless a later RPP audit proves stems or reconstruction items.")
    if _source_is_lossy(input_payload):
        forbidden_claims.extend(["lossless restoration", "true original-resolution master"])
        warnings.append("Source is lossy; decoded WAV may be used for processing but final language must say lossy-source processed print.")

    if mode == "true_rebeat" and not has_stems:
        warnings.append("Requested true_rebeat is not supported without stems or placed MIDI/audio reconstruction evidence.")

    high_side_air = side_mid > -8.0 and air_fizz > -30.0
    high_harshness = harshness > -28.0
    high_sibilance = sibilance > -31.0
    low_punch = punch < -32.0

    if high_side_air and high_harshness:
        ms_moves.append(
            {
                "band": "8-16 kHz",
                "target": "Side",
                "static_or_dynamic": "dynamic",
                "amount_db": "0.5-1.5 dB max",
                "reason": "side wash reduction and stereo harshness control",
                "risk": "collapsed air or cymbal width if overdone",
                "guard": "side_mid_change_warn_db",
            }
        )
        dynamic_eq_bands.append(
            {
                "frequency_range_hz": [8000, 16000],
                "q_or_bandwidth": "wide side-aware dynamic shelf/notch hybrid",
                "threshold_behavior": "only triggers on unstable side fizz peaks",
                "max_reduction_db": 1.5,
                "attack_release_concept": "fast enough for splatter, slow enough to avoid pumping",
                "reason": "reduce side fizz without dulling the whole stereo signal",
                "risk": "air loss and width collapse",
            }
        )
        deai_intensity = "medium"

    if high_sibilance and not high_side_air:
        deesser.append(
            {
                "target": "vocal if isolated, otherwise fullmix-derived vocal band",
                "detection_band_hz": [5000, 10000],
                "processing_band_hz": [5000, 10000],
                "max_reduction_db": min(2.0, thresholds["fullmix_deesser_max_reduction_db"]),
                "stereo_or_ms": "narrow stereo or M/S where justified",
                "brightness_loss_guard": "brightness_loss_warn_db",
                "reason": "sibilance elevated while air/fizz is not the main problem",
            }
        )
        warnings.append("Do not use a broad high-shelf cut for isolated sibilance.")

    if low_punch and high_harshness:
        eq_moves.append(
            {
                "band": "45-140 Hz",
                "type": "preserve/protect",
                "reason": "punch is already low; do not sacrifice kick/bass while reducing harshness",
                "max_gain_change_db": 0.0,
                "risk": "limiter or broad EQ can make the track louder but weaker",
            }
        )
        dynamic_eq_bands.append(
            {
                "frequency_range_hz": [3000, 8000],
                "q_or_bandwidth": "semi-narrow dynamic",
                "threshold_behavior": "trigger only on harsh peaks",
                "max_reduction_db": 2.0,
                "attack_release_concept": "medium-fast attack, tempo-aware release",
                "reason": "reduce harshness dynamically while protecting bass punch",
                "risk": "vocal/snare presence loss",
            }
        )
        compression.append(
            {
                "target": "mix/master bus",
                "purpose": "control peaks without reducing punch",
                "ratio": "1.2:1-1.6:1",
                "attack_ms": "20-40",
                "release_ms": "tempo-aware 80-180",
                "knee_db": "soft",
                "gain_reduction_target_db": "0.5-1.5",
                "makeup_gain_db": "level-match only",
                "expected_sonic_effect": "stable but still punchy",
                "failure_mode": "transient proxy or 45-140 Hz punch drops",
            }
        )

    if _source_is_lossy(input_payload) and air_fizz > -34.0:
        dynamic_eq_bands.append(
            {
                "frequency_range_hz": [10000, 16000],
                "q_or_bandwidth": "gentle dynamic air/fizz control",
                "threshold_behavior": "trigger only on codec hash/fake air bursts",
                "max_reduction_db": 1.0,
                "attack_release_concept": "smooth release to avoid flutter",
                "reason": "MP3 high-frequency fizz control without fake reconstruction",
                "risk": "dull lossy-source processed print",
            }
        )
        if deai_intensity == "medium":
            deai_intensity = "mild-to-medium"
        warnings.append("Avoid extreme air boost or lossless-restoration language for MP3-derived processing.")

    if transient and transient < 0.001:
        warnings.append("Transient proxy is low; avoid heavy master compression and limiter-driven loudness.")

    if not eq_moves and not ms_moves and not dynamic_eq_bands and not deesser:
        eq_moves.append(
            {
                "band": "broad tonal balance only if measured problem exists",
                "type": "conservative static EQ",
                "reason": "no elevated engineering problem was supplied to the decision engine",
                "max_gain_change_db": 1.0,
                "risk": "unnecessary processing",
            }
        )

    return {
        "profile": profile.get("profile_name", "default"),
        "mode": mode or "auto",
        "source_format": source_format or "unknown",
        "recommended_eq_moves": eq_moves,
        "recommended_ms_moves": ms_moves,
        "recommended_dynamic_eq_bands": dynamic_eq_bands,
        "recommended_compression_strategy": compression,
        "recommended_deesser_strategy": deesser,
        "recommended_deai_intensity": deai_intensity,
        "warnings": warnings,
        "forbidden_claims": sorted(set(forbidden_claims)),
        "allowed_language": profile.get("allowed_language", []),
        "notes": [
            "This decision engine does not render audio.",
            "Every recommended move still needs REAPER project evidence, render artifacts, and QC before final claims.",
        ],
    }


def _markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Processing Decision Plan",
        "",
        f"- Profile: `{plan['profile']}`",
        f"- Mode: `{plan['mode']}`",
        f"- Recommended DeAI intensity: `{plan['recommended_deai_intensity']}`",
        "",
        "## Warnings",
        "",
    ]
    warnings = plan.get("warnings") or ["No decision warnings."]
    lines.extend(f"- {warning}" for warning in warnings)
    lines.extend(["", "## Forbidden Claims", ""])
    forbidden = plan.get("forbidden_claims") or ["None from supplied evidence."]
    lines.extend(f"- {claim}" for claim in forbidden)
    lines.extend(["", "## Plan JSON", "", "```json", json.dumps(plan, indent=2, sort_keys=True), "```", ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recommend safe processing moves from metrics and available evidence.")
    parser.add_argument("--input-json", required=True, help="JSON containing metrics, mode, source format, stems, and plugin availability.")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--out-json")
    parser.add_argument("--out-md")
    args = parser.parse_args(argv)

    with Path(args.input_json).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    profile = load_profile(args.profile or payload.get("profile"))
    plan = recommend_processing_plan(payload, profile)

    if args.out_json:
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")
    if args.out_md:
        Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_md).write_text(_markdown(plan), encoding="utf-8")
    if not args.out_json and not args.out_md:
        print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
