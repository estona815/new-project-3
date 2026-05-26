from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from render_orchestrator import build_plan_only_manifest  # noqa: E402


class PlanOnlyNoCompleteTests(unittest.TestCase):
    def test_arrangement_plan_manifest_never_complete(self) -> None:
        manifest = build_plan_only_manifest(PROJECT_ROOT, "ARRANGEMENT_PLAN_READY")

        self.assertEqual(manifest["schema_version"], "audio_render_manifest.v1")
        self.assertEqual(manifest["status"], "ARRANGEMENT_PLAN_READY")
        self.assertFalse(manifest["completion_gate"]["complete"])
        self.assertFalse(manifest["final_wav"]["exists"])

    def test_midi_guide_manifest_never_complete(self) -> None:
        manifest = build_plan_only_manifest(PROJECT_ROOT, "MIDI_GUIDE_READY")

        self.assertEqual(manifest["status"], "MIDI_GUIDE_READY")
        self.assertFalse(manifest["completion_gate"]["complete"])
        self.assertIn("not a verified final WAV state", manifest["completion_gate"]["blocking_reasons"][0])


if __name__ == "__main__":
    unittest.main()
