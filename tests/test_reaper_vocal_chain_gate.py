from __future__ import annotations

import json
from pathlib import Path

from tools.validate_reaper_vocal_chain_gate import check_trace


def test_vocal_chain_gate_ignores_main_vocal_media_rows_before_fx(tmp_path: Path) -> None:
    trace = tmp_path / "actual_reaper_plugin_trace.json"
    trace.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "track": "08 MALE_NONHOOK_CENTER",
                        "stage": "track config",
                        "status": "loaded",
                        "plugin": "gain_db=4.500 pan=0.000 muted=false master_send=false",
                        "fx_index": -1,
                    },
                    {
                        "track": "08 MALE_NONHOOK_CENTER",
                        "stage": "insert media slice",
                        "status": "loaded",
                        "plugin": "/tmp/7 Vocals.wav",
                        "fx_index": -1,
                    },
                    {
                        "track": "08 MALE_NONHOOK_CENTER",
                        "stage": "Codex Vocal AI Artifact Split Tamer FIRST SLOT",
                        "status": "loaded",
                        "plugin": "JS: Codex Vocal AI Artifact Split Tamer",
                        "fx_index": 0,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    errors = check_trace(trace, {"08 male_nonhook_center"}, allow_tune=False)

    assert errors == []


def test_vocal_chain_gate_recognizes_required_main_track_without_explicit_alias(tmp_path: Path) -> None:
    trace = tmp_path / "actual_reaper_plugin_trace.json"
    trace.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "track": "08 MALE_NONHOOK_CENTER",
                        "stage": "Codex Vocal AI Artifact Split Tamer FIRST SLOT",
                        "status": "loaded",
                        "plugin": "JS: Codex Vocal AI Artifact Split Tamer",
                        "fx_index": 0,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    errors = check_trace(trace, set(), allow_tune=False)

    assert errors == []


def test_vocal_chain_gate_prefers_exact_main_track_over_alias_rows(tmp_path: Path) -> None:
    trace = tmp_path / "actual_reaper_plugin_trace.json"
    trace.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "track": "lead_vocal",
                        "stage": "incorrect alias first slot",
                        "status": "loaded",
                        "plugin": "VST: ReaEQ (Cockos)",
                        "fx_index": 0,
                    },
                    {
                        "track": "08 MALE_NONHOOK_CENTER",
                        "stage": "Codex Vocal AI Artifact Split Tamer FIRST SLOT",
                        "status": "loaded",
                        "plugin": "JS: Codex Vocal AI Artifact Split Tamer",
                        "fx_index": 0,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    errors = check_trace(trace, set(), allow_tune=False)

    assert errors == []
