from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sample_arranger import (  # noqa: E402
    add_call_response_motif,
    analyze_sample_candidates,
    arrange_samples_musically,
    build_section_sample_plan,
    pitch_variant,
    select_sample_roles,
)


class SampleArrangerTests(unittest.TestCase):
    def test_pitch_variant_preserves_length(self) -> None:
        chop = np.sin(np.linspace(0, 8 * np.pi, 2048)).astype(np.float32)[:, None] * 0.2
        self.assertEqual(pitch_variant(chop, 7).shape, chop.shape)

    def test_call_response_motif_writes_musical_roles(self) -> None:
        sr = 48000
        mix = np.zeros((sr * 8, 2), dtype=np.float32)
        chop = np.ones((1000, 1), dtype=np.float32) * 0.05
        notes = add_call_response_motif(mix, [chop], sr, bpm=120)
        roles = {note["phrase_role"] for note in notes}
        self.assertIn("call", roles)
        self.assertIn("response", roles)
        self.assertGreater(float(np.max(np.abs(mix))), 0.0)

    def test_selects_stable_motif_from_dummy_samples(self) -> None:
        sr = 48000
        t = np.arange(sr // 2) / sr
        stable = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)[:, None]
        clicky_noise = np.random.default_rng(2).standard_normal((sr // 2, 1)).astype(np.float32) * 0.2
        clicky_noise[0] = 1.0
        candidates = analyze_sample_candidates([clicky_noise, stable], sr)
        selection = select_sample_roles(candidates)
        self.assertEqual(selection["selected"]["main_motif"]["index"], 1)

    def test_avoids_too_many_random_chops(self) -> None:
        sr = 48000
        mix = np.zeros((sr * 64, 2), dtype=np.float32)
        chop = np.sin(np.linspace(0, 6 * np.pi, sr // 4)).astype(np.float32)[:, None] * 0.1
        placements, report, _selection, _plan = arrange_samples_musically(mix, [chop, chop], sr, bpm=120)
        self.assertLess(len(placements), 80)
        self.assertIn("fewer stronger motifs over many random chops", report["arrangement_rules"])

    def test_generates_section_plan(self) -> None:
        selection = {"blocked": False, "selected": {"main_motif": {"index": 0}, "response_motif": {"index": 1}, "texture_chop": {"index": 2}, "transition_chop": {"index": 3}}}
        plan = build_section_sample_plan(selection)
        sections = {item["section"] for item in plan}
        self.assertIn("intro", sections)
        self.assertIn("hook", sections)
        self.assertIn("final_hook", sections)

    def test_policy_blocks_unknown_ownership_direct_use(self) -> None:
        candidates = [{"index": 0, "motif_score": 1.0, "boundary_click_risk": 0.0, "tonal_stability_proxy": 1.0, "spectral_brightness_db": -10.0, "transient_density_per_sec": 1.0, "frequency_conflict": {"vocal": 0.0}, "ownership_safety_status": "unknown"}]
        selection = select_sample_roles(candidates, policy_blocks_unknown=True)
        self.assertTrue(selection["blocked"])
        self.assertEqual(selection["selected"], {})


if __name__ == "__main__":
    unittest.main()
