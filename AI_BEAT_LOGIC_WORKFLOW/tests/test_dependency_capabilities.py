from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from audio_backend_registry import build_audio_backend_registry, can_export_final_wav  # noqa: E402
from dependency_capabilities import collect_dependency_capabilities, write_dependency_capabilities  # noqa: E402


def missing_which(_name: str) -> str | None:
    return None


def selective_which(name: str) -> str | None:
    return {
        "ffmpeg": "/usr/local/bin/ffmpeg",
        "ffprobe": "/usr/local/bin/ffprobe",
        "osascript": "/usr/bin/osascript",
    }.get(name)


class DependencyCapabilitiesTests(unittest.TestCase):
    def test_missing_optional_dependencies_degrade_without_crashing(self) -> None:
        with mock.patch("platform.system", return_value="Linux"), mock.patch(
            "importlib.util.find_spec", return_value=None
        ):
            capabilities = collect_dependency_capabilities(checked_at="2026-05-18T00:00:00+00:00", which=missing_which)

        self.assertEqual(capabilities["schema_version"], "dependency_capabilities.v1")
        self.assertEqual(capabilities["metadata"]["platform"], "linux")
        self.assertTrue(capabilities["tools"]["python_stdlib_wav"]["available"])
        self.assertFalse(capabilities["tools"]["ffmpeg"]["available"])
        self.assertFalse(capabilities["tools"]["librosa"]["available"])
        self.assertFalse(capabilities["tools"]["essentia"]["available"])
        self.assertEqual(capabilities["capabilities"]["metadata_probe"], "stdlib")
        self.assertEqual(capabilities["capabilities"]["wav_export"], "unavailable")
        self.assertEqual(capabilities["capabilities"]["bpm_estimation"], "stdlib_heuristic")
        self.assertEqual(capabilities["capabilities"]["key_estimation"], "low_confidence_heuristic")
        self.assertIn("final WAV export must be blocked", " ".join(capabilities["limitations"]))

    def test_render_backend_is_selected_when_ffmpeg_exists(self) -> None:
        with mock.patch("platform.system", return_value="Darwin"), mock.patch(
            "importlib.util.find_spec", return_value=None
        ), mock.patch("dependency_capabilities._run_version", return_value="ffmpeg test version"):
            capabilities = collect_dependency_capabilities(
                checked_at="2026-05-18T00:00:00+00:00",
                which=selective_which,
                logic_app_path=Path("/tmp/does-not-exist-logic.app"),
            )
        registry = build_audio_backend_registry(capabilities)

        self.assertTrue(capabilities["tools"]["ffmpeg"]["available"])
        self.assertEqual(capabilities["tools"]["ffmpeg"]["path"], "/usr/local/bin/ffmpeg")
        self.assertEqual(capabilities["capabilities"]["metadata_probe"], "ffprobe")
        self.assertEqual(capabilities["capabilities"]["wav_export"], "ffmpeg")
        self.assertTrue(can_export_final_wav(registry))
        self.assertFalse(registry["final_export_blocked"])

    def test_logic_and_plugin_detection_are_claim_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            logic_app = Path(tmp) / "Logic Pro.app"
            logic_app.mkdir()
            with mock.patch("platform.system", return_value="Darwin"), mock.patch(
                "importlib.util.find_spec", return_value=None
            ), mock.patch("dependency_capabilities._scan_au_components", return_value=[str(Path(tmp) / "Decapitator.component")]):
                capabilities = collect_dependency_capabilities(
                    checked_at="2026-05-18T00:00:00+00:00",
                    which=selective_which,
                    logic_app_path=logic_app,
                )

        self.assertTrue(capabilities["tools"]["logic_pro"]["available"])
        self.assertTrue(capabilities["tools"]["osascript"]["available"])
        self.assertEqual(capabilities["capabilities"]["logic_project_creation"], "available")
        self.assertEqual(capabilities["capabilities"]["plugin_automation"], "manual_required")
        self.assertEqual(capabilities["plugins"]["autotune_like"]["status"], "manual_required")
        self.assertEqual(capabilities["plugins"]["soundtoys_decapitator"]["status"], "detected_manual_required")
        self.assertIn("requires manual or verified Logic automation", capabilities["plugins"]["soundtoys_decapitator"]["note"])

    def test_write_dependency_capabilities_uses_project_root(self) -> None:
        payload = collect_dependency_capabilities(checked_at="2026-05-18T00:00:00+00:00", which=missing_which)
        with tempfile.TemporaryDirectory() as tmp:
            output = write_dependency_capabilities(Path(tmp), capabilities=payload)
            parsed = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(output.name, "dependency_capabilities.json")
        self.assertEqual(parsed["schema_version"], "dependency_capabilities.v1")
        self.assertIn("capabilities", parsed)


if __name__ == "__main__":
    unittest.main()
