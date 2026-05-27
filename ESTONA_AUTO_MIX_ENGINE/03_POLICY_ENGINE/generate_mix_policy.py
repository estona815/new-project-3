#!/usr/bin/env python3
"""Generate conservative/normal/aggressive mix policies with reasons."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02_ANALYSIS"))

from audio_utils import clamp, read_json, resolve_path, write_json


SCALE = {"conservative": 0.6, "normal": 1.0, "aggressive": 1.45}


def item(value, reason):
    return {"value": value, "reason": reason}


def load_rules() -> dict:
    path = resolve_path("03_POLICY_ENGINE", "user_preference_rules.yaml")
    rules = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line or line.strip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        rules[key.strip()] = value.strip().lower() in {"true", "yes", "1"}
    return rules


def build_policy(mode: str = "normal") -> dict:
    scale = SCALE.get(mode, 1.0)
    current = read_json(resolve_path("02_ANALYSIS", "current_song_analysis.json"), {"relationship_analysis": {}, "stems": []})
    masking = read_json(resolve_path("02_ANALYSIS", "vocal_beat_masking_analysis.json"), {})
    sat = read_json(resolve_path("02_ANALYSIS", "saturation_analysis.json"), {})
    pitch = read_json(resolve_path("02_ANALYSIS", "vocal_pitch_analysis.json"), {"tracks": []})
    rules = load_rules()
    rel = current.get("relationship_analysis", {})
    vbr = float(masking.get("vocal_to_beat_ratio", rel.get("vocal_to_beat_loudness_ratio", 1.5)))
    intrusion = float(rel.get("backing_intrusion_score", 0.0))
    harsh = float(masking.get("vocal_harsh_3k_6k", -24))
    sib = float(masking.get("vocal_sibilance_6k_9k", -28))
    thin = float(masking.get("vocal_thin_ai_score", 0.0))
    buried = float(masking.get("vocal_buried_score", 0.0))
    glue = float(masking.get("vocal_beat_glue_score", 0.7))
    beat_body = float(sat.get("beat_harmonic_body", 2.0))
    ref_body = float(sat.get("reference_harmonic_density_median", 2.0))
    upper_808 = float(sat.get("808_harmonic_visibility", 0.0))
    snap = max([float(t.get("pitch_snap_artifact_score", 0.0)) for t in pitch.get("tracks", [])] or [0.0])

    lead_gain = clamp(-(vbr - 1.5) * 0.45 * scale + buried * 1.0 * scale, -3.0, 2.0)
    backing_gain = clamp(-intrusion * 2.0 * scale if rules.get("female_backing_only", True) else -intrusion, -6.0, 0.0)
    harsh_cut = clamp(max(0.0, harsh + 20.0) * 0.35 * scale + snap * 1.2, 0.0, 4.5)
    deess = clamp(max(0.0, sib + 24.0) * 0.4 * scale, 0.0, 5.0)
    body = clamp(thin * 2.0 * scale, 0.0, 3.0)
    beat_sat = clamp(max(0.0, ref_body - beat_body) * 0.35 * scale, 0.0, 5.0)
    policy = {
        "lead_vocal_gain_db": item(round(lead_gain, 2), f"Current vocal-to-beat ratio is {vbr:.2f} dB; target is a conservative user-approved balance around 1.5 dB."),
        "backing_vocal_gain_db": item(round(backing_gain, 2), f"Backing intrusion score is {intrusion:.2f}; female backing must not take over the male lead."),
        "adlib_gate_strength": item(round(clamp(intrusion * 0.7 * scale, 0.0, 1.0), 2), "Gate strength follows backing overlap so adlibs stay in phrase gaps where possible."),
        "backing_center_reduction": item(round(clamp(intrusion * 0.8 * scale, 0.0, 1.0), 2), "Center reduction protects lead-vocal dominance when backing presence overlaps 1k-4k."),
        "backing_width_increase": item(round(clamp(0.2 + intrusion * 0.4 * scale, 0.0, 0.8), 2), "Wider backing keeps doubles/adlibs supportive instead of lead-like."),
        "vocal_body_boost_db": item(round(body, 2), f"Vocal thin/AI score is {thin:.2f}; add body while avoiding harsh top boost."),
        "vocal_harsh_dynamic_cut_db": item(round(harsh_cut, 2), f"Harshness band proxy is {harsh:.2f} dB and pitch snap score is {snap:.2f}."),
        "deess_amount": item(round(deess, 2), f"Sibilance band proxy is {sib:.2f} dB relative to safety threshold."),
        "vocal_parallel_saturation_amount": item(round(clamp(thin * 0.65 * scale, 0.0, 1.0), 2), "Parallel saturation restores body without making the vocal a new melodic source."),
        "beat_bus_saturation_amount": item(round(beat_sat, 2), f"Beat harmonic body {beat_body:.2f} is compared to reference median {ref_body:.2f}."),
        "drum_clip_drive": item(round(clamp(beat_sat * 0.5, 0.0, 2.5), 2), "Soft clip drive supports digicore energy while avoiding a flat overcompressed master."),
        "808_upper_harmonic_amount": item(round(clamp(max(0.0, -upper_808 - 5.0) * 0.12 * scale, 0.0, 1.0), 2), f"808 phone translation proxy is {upper_808:.2f}; upper harmonics help small-speaker audibility."),
        "808_mud_reduction_db": item(round(clamp(max(0.0, upper_808 + 4.0) * 0.25 * scale, 0.0, 3.0), 2), "Mud reduction is applied only when 100-250 Hz energy appears excessive."),
        "mono_sub_crossover_hz": item(120, "Sub below 120 Hz defaults to mono-compatible protection."),
        "mono_sub_amount": item(round(clamp(0.75 * scale, 0.4, 1.0), 2), "Mono sub guard prevents side low-end from weakening translation."),
        "vocal_beat_glue_amount": item(round(clamp((1.0 - glue) * scale, 0.0, 1.0), 2), f"Vocal/beat glue score is {glue:.2f}; apply gentle bus glue only as needed."),
    }
    result = {"engine": "ESTONA_AUTO_MIX_ENGINE", "policy_type": "mix", "mode": mode, "policy": policy}
    return result


def generate_all() -> dict:
    policies = {}
    for mode in SCALE:
        policies[mode] = build_policy(mode)
        write_json(resolve_path("03_POLICY_ENGINE", f"mix_policy_{mode}.json"), policies[mode])
    write_json(resolve_path("03_POLICY_ENGINE", "mix_policy.json"), policies["normal"])
    write_report(policies["normal"])
    return policies["normal"]


def write_report(policy: dict) -> None:
    lines = ["# Mix Policy Report", "", "## A. 코드가 측정한 사실", "- See current, masking, pitch, and saturation JSON analysis files.", "", "## B. 정책 엔진이 추천한 수정"]
    for key, value in policy["policy"].items():
        lines.append(f"- {key}: {value['value']} — {value['reason']}")
    lines += ["", "## C. 사용자가 청감으로 확인해야 하는 항목", "- 보컬이 너무 앞으로 튀는지", "- 여자 더블이 리드처럼 들리는지", "- 808이 폰에서도 들리는지", "- 고역이 피곤한지"]
    resolve_path("07_REPORTS", "mix_policy_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode == "all":
        print(f"mix policy status: {generate_all()['mode']}")
    else:
        write_json(resolve_path("03_POLICY_ENGINE", "mix_policy.json"), build_policy(mode))
        print(f"mix policy generated: {mode}")
