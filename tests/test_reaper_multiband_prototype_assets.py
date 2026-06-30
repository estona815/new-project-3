from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM/docs/reaper_ai_artifact_multiband_prototype.md"
SCRIPT = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM/scripts/create_reaper_ai_artifact_multiband_prototype.lua"
PRESETS = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM/presets/reaper_multiband_prototype_presets.json"
EVAL = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM/reports/reaper_multiband_prototype_evaluation_template.md"


REQUIRED_TRACKS = [
    "Original Dry",
    "Processed Full",
    "Processed Matched",
    "Residual Monitor",
    "Mid Process Bus",
    "Side Process Bus",
    "Broad Multiband Bus",
    "Surgical Dynamic EQ Bus",
    "ReaFIR Micro Suppression Bus",
    "Gate/Expander Bus",
    "Print/Render A/B",
    "Notes/Markers",
    "24-64 Band Suppressor Candidate",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_required_assets_exist() -> None:
    assert DOC.exists()
    assert SCRIPT.exists()
    assert PRESETS.exists()
    assert EVAL.exists()


def test_document_covers_required_architecture() -> None:
    text = read(DOC)
    for track in REQUIRED_TRACKS:
        assert track in text
    assert "Residual: original minus processed" in text
    assert "Mid and Side buses" in text
    assert "24-64 Band Dynamic Suppressor Candidate" in text
    assert "Artifact Score Detector" in text
    assert "vocal, transient, and harmonic guards" in text
    assert "Do not port huge static notch banks" in text
    assert "No manual A/B was performed" in text


def test_script_creates_tracks_and_core_routing() -> None:
    text = read(SCRIPT)
    for track in REQUIRED_TRACKS:
        assert track in text
    assert "CreateTrackSend" in text
    assert '"B_PHASE", 1' in text
    assert "TDR Nova" in text
    assert "ReaFIR" in text
    assert "ReaGate" in text
    assert "Mid/Side Encoder" in text
    assert "24-64 Band Dynamic Suppressor" in text
    assert "M/S independent artifact-score detector" in text
    assert "PROJECT_NOTES" in text


def test_presets_json_has_four_presets_and_band_log_schema() -> None:
    data = json.loads(read(PRESETS))
    assert data["schema"] == "reaper-ai-artifact-multiband-prototype-v1"
    assert [preset["name"] for preset in data["presets"]] == [
        "Vocal Preserve",
        "Balanced Artifact Reduction",
        "AI Metallic Surgical",
        "Strong Stress Test",
    ]
    assert len(data["band_templates"]) >= 8
    assert data["dynamic_suppressor_candidate"]["default_band_count"] == 24
    assert data["dynamic_suppressor_candidate"]["allowed_band_counts"] == [24, 48, 64]
    assert data["dynamic_suppressor_candidate"]["ms_processing"]["mode"] == "independent_mid_side_detectors_and_gain_smoothing"
    assert "transient_guard" in data["dynamic_suppressor_candidate"]["artifact_score_detector"]["guards"]
    assert "vocal_preservation_1_to_5" in data["evaluation_columns"]
    assert "residual_cleanliness_1_to_5" in data["evaluation_columns"]
    assert "artifact_score_usefulness_1_to_5" in data["evaluation_columns"]


def test_workflow_blocks_fake_clarity_and_strong_gate_defaults() -> None:
    combined = "\n".join(read(path).lower() for path in (DOC, SCRIPT, PRESETS, EVAL))
    assert "no exciter" in combined
    assert "high-shelf compensation" in combined
    assert "gaps only" in combined
    assert "source damage is not" in combined
    assert "24-band is the only preservation-first suppressor default" in combined
