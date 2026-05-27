#!/usr/bin/env python3
"""Compare current analysis to approved estona reference profile."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02_ANALYSIS"))

from audio_utils import read_json, resolve_path, scalar_feature, write_json


KEYS = [
    "integrated_lufs",
    "peak_dbfs",
    "rms_db",
    "crest_factor",
    "low_band_energy_20_120hz",
    "low_mid_energy_120_350hz",
    "vocal_presence_energy_1k_4k",
    "harshness_energy_3k_6k",
    "sibilance_energy_6k_9k",
    "air_energy_10k_plus",
    "stereo_correlation",
    "mid_side_ratio",
    "harmonic_density_proxy",
    "dynamic_range_proxy",
]


def compare() -> dict:
    current = read_json(resolve_path("02_ANALYSIS", "current_song_analysis.json"), {"stems": []})
    ref = read_json(resolve_path("00_REFERENCES", "reference_profiles", "estona_reference_profile.json"), {"feature_summary": {}})
    summary = ref.get("feature_summary", {})
    stems = [s for s in current.get("stems", []) if "error" not in s]
    deltas = []
    for stem in stems:
        stem_delta = {"file": stem.get("file"), "stem_type": stem.get("stem_type"), "features": {}}
        for key in KEYS:
            if key in stem and key in summary:
                target = scalar_feature(summary, key)
                stem_delta["features"][key] = {
                    "current": stem[key],
                    "reference_median": target,
                    "delta": stem[key] - target,
                    "acceptable_low": summary[key].get("acceptable_low"),
                    "acceptable_high": summary[key].get("acceptable_high"),
                }
        deltas.append(stem_delta)
    result = {
        "status": "ok" if summary and stems else "insufficient_data",
        "reference_status": ref.get("status"),
        "deltas": deltas,
        "note": "Reference is a direction profile only, not a source for copying musical content.",
    }
    write_json(resolve_path("03_POLICY_ENGINE", "reference_current_delta.json"), result)
    write_reference_delta_report(result)
    return result


def write_reference_delta_report(result: dict) -> None:
    lines = [
        "# Reference Delta Report",
        "",
        "## A. 코드가 측정한 사실",
        f"- Status: {result.get('status')}",
        f"- Reference status: {result.get('reference_status')}",
    ]
    for stem in result.get("deltas", []):
        lines.append(f"- {Path(stem.get('file', '')).name} ({stem.get('stem_type')})")
        for key, value in list(stem.get("features", {}).items())[:8]:
            lines.append(f"  - {key}: current {value['current']:.3f}, ref median {value['reference_median']:.3f}, delta {value['delta']:.3f}")
    lines += [
        "",
        "## B. 정책 엔진이 추천한 수정",
        "- Generate policies with `generate_mix_policy.py` and `generate_master_policy.py`.",
        "",
        "## C. 사용자가 청감으로 확인해야 하는 항목",
        "- 레퍼런스와 감정적 방향이 맞는지",
        "- 분석 수치가 맞아도 보컬/비트 밸런스가 음악적으로 자연스러운지",
    ]
    resolve_path("07_REPORTS", "reference_delta_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    print(f"comparison status: {compare().get('status')}")
