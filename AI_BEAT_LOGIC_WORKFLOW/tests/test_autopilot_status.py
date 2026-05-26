from __future__ import annotations

import sys
import unittest
from unittest import mock
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from audio_backend_registry import build_audio_backend_registry, choose_wav_export_backend  # noqa: E402
from autopilot_status import build_autopilot_status, final_export_blocked, plugin_claim_allowed  # noqa: E402
import main as workflow_main  # noqa: E402


def capabilities_fixture(*, wav_export: str = "unavailable", logic: str = "unavailable") -> dict:
    return {
        "schema_version": "dependency_capabilities.v1",
        "metadata": {"platform": "macOS", "checked_at": "2026-05-18T00:00:00+00:00"},
        "tools": {
            "python_stdlib_wav": {"available": True},
            "ffmpeg": {"available": wav_export == "ffmpeg", "path": "/usr/bin/ffmpeg" if wav_export == "ffmpeg" else None},
            "ffprobe": {"available": True, "path": "/usr/bin/ffprobe"},
            "afinfo": {"available": False},
            "afconvert": {"available": wav_export == "afconvert", "path": "/usr/bin/afconvert" if wav_export == "afconvert" else None},
            "logic_pro": {"available": logic != "unavailable", "path": "/Applications/Logic Pro.app" if logic != "unavailable" else None},
            "osascript": {"available": logic == "available", "path": "/usr/bin/osascript" if logic == "available" else None},
        },
        "plugins": {
            "autotune_like": {"status": "manual_required"},
            "soundtoys_decapitator": {"status": "not_detected"},
        },
        "capabilities": {
            "metadata_probe": "ffprobe",
            "wav_export": wav_export,
            "peak_rms_analysis": True,
            "rough_onset_analysis": True,
            "bpm_estimation": "stdlib_heuristic",
            "key_estimation": "low_confidence_heuristic",
            "vocal_pitch_tracking": "heuristic",
            "logic_project_creation": logic,
            "plugin_automation": "manual_required" if logic != "unavailable" else "unavailable",
        },
        "limitations": [],
    }


class AutopilotStatusTests(unittest.TestCase):
    def test_no_export_backend_forces_plan_only_status(self) -> None:
        status = build_autopilot_status(capabilities_fixture())

        self.assertEqual(status["mode"], "plan_only")
        self.assertTrue(status["plan_only"])
        self.assertTrue(final_export_blocked(status))
        self.assertFalse(status["completion_possible"])
        self.assertIn("final WAV export backend unavailable", status["plan_only_reasons"])
        self.assertIn("completion_gate.py", status["completion_rule"])

    def test_export_backend_makes_render_capable_but_not_complete(self) -> None:
        status = build_autopilot_status(capabilities_fixture(wav_export="ffmpeg", logic="available"))

        self.assertEqual(status["mode"], "render_capable")
        self.assertFalse(status["plan_only"])
        self.assertFalse(final_export_blocked(status))
        self.assertFalse(status["completion_possible"])
        self.assertEqual(status["capability_summary"]["wav_export"], "ffmpeg")
        self.assertIn("plugin automation is not verified", status["plan_only_reasons"])

    def test_plugin_claim_is_never_allowed_from_status_alone(self) -> None:
        status = build_autopilot_status(capabilities_fixture(wav_export="ffmpeg", logic="available"))

        self.assertFalse(plugin_claim_allowed(status))
        self.assertIn("no plugin-applied claim", status["plugin_status"]["claim_rule"])

    def test_audio_backend_registry_blocks_export_when_unavailable(self) -> None:
        registry = build_audio_backend_registry(capabilities_fixture())

        self.assertEqual(choose_wav_export_backend(registry), "unavailable")
        self.assertTrue(registry["final_export_blocked"])
        self.assertIn("No verified WAV export backend", " ".join(registry["blocking_reasons"]))

    def test_main_writes_dependency_capabilities_before_planning_exit(self) -> None:
        with mock.patch.object(sys, "argv", ["main.py"]), mock.patch.object(
            workflow_main, "write_dependency_capabilities", return_value=Path("01_ANALYSIS/dependency_capabilities.json")
        ) as writer:
            result = workflow_main.main()

        self.assertEqual(result, 0)
        writer.assert_called_once()


if __name__ == "__main__":
    unittest.main()
