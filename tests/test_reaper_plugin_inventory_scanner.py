from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "automix/scan_reaper_plugin_inventory.lua"
ALIASES = ROOT / "automix/plugin_aliases.lua"
CATALOG = ROOT / "automix/plugin_capability_catalog.json"
DOC = ROOT / "docs/reaper_plugin_inventory.md"


REQUIRED_CAPABILITIES = {
    "pitch_correction",
    "static_eq",
    "dynamic_eq",
    "resonance_suppressor",
    "compressor",
    "limiter",
    "saturator",
    "multiband_compressor",
    "deesser",
    "reverb",
    "delay",
    "stereo_width",
    "noise_reduction",
    "analyzer",
    "utility",
}


TARGET_NAMES = [
    "MAutoPitch",
    "ReaPitch",
    "Auto-Tune",
    "Melodyne",
    "ReaEQ",
    "TDR Nova",
    "MEqualizer",
    "MAutoDynamicEQ",
    "MDynamicEQ",
    "Soothe",
    "DSEQ",
    "Decapitator",
    "Saturn",
    "ReaComp",
    "ReaXcomp",
    "LA-2A",
    "1176",
    "OTT",
    "ValhallaSupermassive",
    "ReaVerbate",
    "ReaDelay",
    "Kolin",
    "Koliv",
    "Kiive",
    "MSEQ",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_inventory_assets_exist() -> None:
    assert SCRIPT.exists()
    assert ALIASES.exists()
    assert CATALOG.exists()
    assert DOC.exists()


def test_capability_catalog_is_valid_and_complete() -> None:
    data = json.loads(read(CATALOG))
    assert data["schema"] == "automix-plugin-capability-catalog-v1"
    assert set(data["required_capabilities"]) == REQUIRED_CAPABILITIES
    assert data["safety"]["inventory_only"] is True
    assert data["safety"]["does_not_apply_fx"] is True
    assert data["safety"]["does_not_assume_parameter_indexes"] is True

    catalog_text = read(CATALOG)
    for name in TARGET_NAMES:
        assert name in catalog_text


def test_script_declares_outputs_schema_and_capabilities() -> None:
    text = read(SCRIPT)
    assert "automix-reaper-plugin-inventory-v1" in text
    assert "plugin_inventory.json" in text
    assert "plugin_inventory_report.md" in text
    assert "temporary_probe_track_deleted" in text
    assert "parameter_indexes_assumed = false" in text
    for capability in REQUIRED_CAPABILITIES:
        assert f'"{capability}"' in text


def test_script_uses_temp_probe_track_and_cleans_up() -> None:
    text = read(SCRIPT)
    assert "__AUTOMIX_PLUGIN_INVENTORY_TEMP_DO_NOT_USE__" in text
    assert "InsertTrackAtIndex" in text
    assert "B_MUTE" in text
    assert "B_SHOWINTCP" in text
    assert "B_SHOWINMIXER" in text
    assert "TrackFX_AddByName" in text
    assert "TrackFX_Delete" in text
    assert "delete_temp_probe_track(temp)" in text
    assert "restore_track_selection(selected_tracks)" in text
    assert "Undo_BeginBlock" in text
    assert "Undo_EndBlock" in text
    assert "PreventUIRefresh" in text


def test_script_does_not_use_destructive_or_parameter_setting_apis() -> None:
    text = read(SCRIPT)
    forbidden = [
        "TrackFX_SetParam",
        "TrackFX_SetNamedConfigParm",
        "TrackFX_SetPreset",
        "TrackFX_SetEnabled",
        "SetTrackSendInfo_Value",
        "Main_SaveProject",
        "Main_SaveProjectEx",
        "GetSetProjectInfo(0, \"RENDER",
        "GetSetProjectInfo_String(0, \"RENDER",
        "Main_OnCommand(40004",
        "RenderFileSection",
    ]
    for token in forbidden:
        assert token not in text


def test_script_has_fuzzy_matching_and_ambiguity_reporting() -> None:
    text = read(SCRIPT)
    assert "normalize_name" in text
    assert "compact_name" in text
    assert "score_alias" in text
    assert "confidence" in text
    assert "ambiguous" in text
    assert "manual_only" in text
    for name in TARGET_NAMES:
        assert name in text or name in read(ALIASES)


def test_alias_file_contains_user_extension_points() -> None:
    text = read(ALIASES)
    assert "return {" in text
    assert "user_defined_eq" in text
    assert "user_defined_dynamic_eq" in text
    assert "user_defined_opto_compressor" in text
    assert "MSEQ" in text
    assert "MAutoDynamicEQ" in text
    assert "MDynamicEQ" in text
    assert "Kolin" in text
    assert "Koliv" in text
    assert "Kiive" in text
    assert "Do not put license" in text


def test_documentation_states_inventory_only_limits() -> None:
    text = read(DOC)
    required_phrases = [
        "It does not mix, tune, render, save, or change user audio.",
        "It does not insert FX into original tracks.",
        "It does not assume any plugin parameter indexes.",
        "temporary muted hidden test track",
        "Fuzzy matches are not treated as proof of product identity.",
        "This scan is not an audio-quality claim",
    ]
    for phrase in required_phrases:
        assert phrase in text
