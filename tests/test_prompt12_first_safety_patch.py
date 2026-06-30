from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYSTEM = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM"
JSFX = SYSTEM / "JSFX" / "vocal_ai_artifact_split_tamer.jsfx"
DOCS = SYSTEM / "docs"
FACTORY_PRESETS = SYSTEM / "presets" / "factory_presets_safe_defaults.json"


def read_jsfx() -> str:
    return JSFX.read_text(encoding="utf-8")


def jsfx_slider_defaults() -> dict[str, float]:
    defaults: dict[str, float] = {}
    pattern = re.compile(r"^slider(\d+):(-?\d+(?:\.\d+)?)<")
    for line in read_jsfx().splitlines():
        match = pattern.match(line)
        if match:
            defaults[f"slider{match.group(1)}"] = float(match.group(2))
    return defaults


def test_first_safety_patch_doc_exists_and_is_safety_only() -> None:
    text = (DOCS / "first_safety_patch.md").read_text(encoding="utf-8")

    assert "This patch is safety-only" in text
    assert "does not add denoise strength" in text
    assert "Snapshot Added" in text
    assert "Fallback Conditions" in text
    assert "DryWet = 0 now returns dry" in text
    assert "No active model runtime exists" in text
    assert "does not claim improved vocal clarity" in text


def test_defaults_remain_preservation_first_and_match_factory_preserve() -> None:
    policy = json.loads(FACTORY_PRESETS.read_text(encoding="utf-8"))
    preserve = next(p for p in policy["presets"] if p["name"] == policy["default_preset"])
    jsfx = jsfx_slider_defaults()

    assert policy["default_preset"] == "Preserve"
    assert preserve["strong_mode"] is False
    assert preserve["jsfx_sliders"]["slider8"] == 0
    assert preserve["jsfx_sliders"]["slider9"] == 30
    assert preserve["jsfx_sliders"]["slider10"] == 8
    assert preserve["jsfx_sliders"]["slider14"] == 0.35
    assert preserve["jsfx_sliders"]["slider22"] == 0

    for key, value in preserve["jsfx_sliders"].items():
        assert jsfx[key] == float(value), key


def test_snapshot_and_dry_fallback_are_before_filterbank_processing() -> None:
    text = read_jsfx()
    filterbank_index = text.index("mono = 0.5 * (in_l + in_r);")

    for token in (
        "snap_wet = max(0, min(wet, 1));",
        "snap_bypass = bypass >= 0.5;",
        "snap_processing_enabled = processing_enabled >= 0.5;",
        "snap_mapped_amount = max(0, min(mapped_amount, 1));",
        "snap_mask_strength = max(0, min(mask_strength, 1));",
        "snap_out_gain = out_gain;",
        "snap_bypass ? (",
        ") : (snap_wet <= eps) ? (",
        ") : (!snap_processing_enabled) ? (",
    ):
        assert token in text
        assert text.index(token) < filterbank_index


def test_suspicious_collapse_uses_dry_fallback_not_reduced_wet() -> None:
    text = read_jsfx()
    fallback_index = text.index(") : (suspicious_drop || full_band_collapse) ? (")
    mix_index = text.index("out_l = in_l + (proc_l - in_l) * wet_state;")
    fallback_block = text[fallback_index:mix_index]

    assert "target_wet *= 0.25;" not in text
    assert "spl0 = in_l;" in fallback_block
    assert "spl1 = in_r;" in fallback_block
    assert "wet_state = 0;" in fallback_block
    assert "status = 5;" in fallback_block


def test_risk_register_marks_first_safety_patch_reductions() -> None:
    text = (DOCS / "risk_register.md").read_text(encoding="utf-8")

    assert "Reduced in first safety patch" in text
    assert "last_safe_l/r" in text
    assert "now returns dry instead of 25% wet processing" in text
