from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "mwolla_v11_constant_vocal_light_dyn_eq_master.py"


def load_v11_module():
    spec = importlib.util.spec_from_file_location("mwolla_v11_constant_vocal_light_dyn_eq_master", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mid_song_general_low_window_receives_final_lock_gain():
    v11 = load_v11_module()

    gain, reason = v11.post_final_lock_gain_for_window(
        start_s=120.0,
        end_s=121.5,
        rms_db=-15.30,
        target_db=-13.22,
    )

    assert gain >= 1.0
    assert reason == "post-final general low-window level lock"


def test_stable_window_does_not_get_unnecessary_level_lock_gain():
    v11 = load_v11_module()

    gain, reason = v11.post_final_lock_gain_for_window(
        start_s=51.0,
        end_s=52.5,
        rms_db=-13.95,
        target_db=-13.22,
    )

    assert gain == 0.0
    assert reason == ""


def test_forced_high_window_keeps_safety_cut():
    v11 = load_v11_module()

    gain, reason = v11.post_final_lock_gain_for_window(
        start_s=67.5,
        end_s=69.0,
        rms_db=-11.90,
        target_db=-13.22,
    )

    assert gain < 0.0
    assert reason == "post-final forced-high level lock"
